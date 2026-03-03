"""Load balancing and high availability module.

Provides:
- HAProxy configuration
- Keepalived (VRRP) setup
- Health checks
- Failover configuration
- Backend server management
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class LoadBalancerModule(Module):
    """Load balancing and high availability."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "configure")

        if action == "install_haproxy":
            return await self._install_haproxy(connector, kwargs)
        elif action == "configure":
            return await self._configure_lb(connector, kwargs)
        elif action == "add_backend":
            return await self._add_backend(connector, kwargs)
        elif action == "remove_backend":
            return await self._remove_backend(connector, kwargs)
        elif action == "setup_keepalived":
            return await self._setup_keepalived(connector, kwargs)
        elif action == "enable_stats":
            return await self._enable_stats(connector, kwargs)
        else:
            return ModuleResult(changed=False, success=False, message=f"Unknown loadbalancer action: {action}")

    async def _install_haproxy(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Install HAProxy."""
        result = await connector.run_command("apt-get update && apt-get install -y haproxy", sudo=True)

        if result.success:
            await connector.run_command("systemctl enable haproxy", sudo=True)
            return ModuleResult(changed=True, success=True, message="HAProxy installed")
        return ModuleResult(changed=False, success=False, message="Installation failed")

    async def _configure_lb(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Configure load balancer."""
        backend_servers = params.get("backend_servers", "")
        algorithm = params.get("algorithm", "roundrobin")
        frontend_port = params.get("frontend_port", "80")
        backend_port = params.get("backend_port", "8080")
        health_check = params.get("health_check", "true") == "true"

        if isinstance(backend_servers, str):
            backend_servers = [s.strip() for s in backend_servers.split(",")]

        # Build backend server list
        backend_lines = []
        for i, server in enumerate(backend_servers, 1):
            health = " check" if health_check else ""
            backend_lines.append(f"    server backend{i} {server}{health}")

        haproxy_config = f"""
global
    log /dev/log local0
    log /dev/log local1 notice
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon

defaults
    log global
    mode http
    option httplog
    option dontlognull
    timeout connect 5000
    timeout client  50000
    timeout server  50000

frontend http_front
    bind *:{frontend_port}
    default_backend http_back

backend http_back
    balance {algorithm}
{chr(10).join(backend_lines)}
"""

        await connector.run_command(f"cat > /etc/haproxy/haproxy.cfg << 'EOL'\n{haproxy_config}\nEOL", sudo=True)

        # Test configuration
        test_result = await connector.run_command("haproxy -c -f /etc/haproxy/haproxy.cfg", sudo=True)
        if not test_result.success:
            return ModuleResult(changed=False, success=False,
                message="HAProxy configuration test failed", details={"error": test_result.stderr})

        # Reload HAProxy
        await connector.run_command("systemctl reload haproxy", sudo=True)

        return ModuleResult(changed=True, success=True,
            message="Load balancer configured",
            details={"algorithm": algorithm, "backends": len(backend_servers)})

    async def _add_backend(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Add backend server to HAProxy."""
        server_name = params.get("server_name", "")
        server_address = params.get("server_address", "")

        backend_line = f"    server {server_name} {server_address} check"

        # Append to backend section
        await connector.run_command(
            f"sed -i '/^backend http_back/a {backend_line}' /etc/haproxy/haproxy.cfg",
            sudo=True,
        )

        await connector.run_command("systemctl reload haproxy", sudo=True)

        return ModuleResult(changed=True, success=True, message=f"Backend {server_name} added")

    async def _remove_backend(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Remove backend server."""
        server_name = params.get("server_name", "")

        await connector.run_command(
            f"sed -i '/server {server_name}/d' /etc/haproxy/haproxy.cfg",
            sudo=True,
        )

        await connector.run_command("systemctl reload haproxy", sudo=True)

        return ModuleResult(changed=True, success=True, message=f"Backend {server_name} removed")

    async def _setup_keepalived(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Setup Keepalived for VRRP."""
        vip = params.get("vip", "")
        interface = params.get("interface", "eth0")
        role = params.get("role", "MASTER")  # MASTER or BACKUP
        priority = params.get("priority", "100")
        router_id = params.get("router_id", "51")

        # Install keepalived
        await connector.run_command("apt-get install -y keepalived", sudo=True)

        keepalived_config = f"""
vrrp_instance VI_1 {{
    state {role}
    interface {interface}
    virtual_router_id {router_id}
    priority {priority}
    advert_int 1
    authentication {{
        auth_type PASS
        auth_pass simpleinfra
    }}
    virtual_ipaddress {{
        {vip}
    }}
}}
"""

        await connector.run_command(f"cat > /etc/keepalived/keepalived.conf << 'EOL'\n{keepalived_config}\nEOL", sudo=True)

        await connector.run_command("systemctl enable keepalived", sudo=True)
        await connector.run_command("systemctl restart keepalived", sudo=True)

        return ModuleResult(changed=True, success=True,
            message=f"Keepalived configured ({role})", details={"vip": vip, "role": role})

    async def _enable_stats(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Enable HAProxy stats page."""
        port = params.get("port", "8404")
        username = params.get("username", "admin")
        password = params.get("password", "admin")

        stats_config = f"""
listen stats
    bind *:{port}
    stats enable
    stats uri /stats
    stats refresh 30s
    stats auth {username}:{password}
"""

        await connector.run_command(f"cat >> /etc/haproxy/haproxy.cfg << 'EOL'\n{stats_config}\nEOL", sudo=True)
        await connector.run_command("systemctl reload haproxy", sudo=True)

        return ModuleResult(changed=True, success=True,
            message=f"Stats page enabled on port {port}",
            details={"port": port, "url": f"http://localhost:{port}/stats"})
