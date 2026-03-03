"""Multi-tenant network isolation module.

Provides VLAN-based and firewall-based tenant isolation:
- Separate VLANs per tenant
- Inter-tenant traffic blocking
- Per-tenant bandwidth limits
- Tenant resource tracking
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class MultiTenantModule(Module):
    """Multi-tenant network isolation."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "create_tenant")

        if action == "create_tenant":
            return await self._create_tenant(connector, kwargs)
        elif action == "isolate_tenants":
            return await self._isolate_tenants(connector, kwargs)
        elif action == "set_bandwidth":
            return await self._set_bandwidth_limit(connector, kwargs)
        elif action == "list_tenants":
            return await self._list_tenants(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown multi-tenant action: {action}",
            )

    async def _create_tenant(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Create isolated tenant network.

        Creates:
        - Dedicated VLAN
        - Firewall rules for isolation
        - Optional bandwidth limit
        """
        tenant_id = params.get("tenant_id")
        vlan_id = params.get("vlan_id")
        subnet = params.get("subnet")
        interface = params.get("interface", "eth0")
        bandwidth_limit = params.get("bandwidth")  # e.g., "100mbit"

        if not tenant_id or not vlan_id:
            return ModuleResult(
                changed=False,
                success=False,
                message="tenant_id and vlan_id are required",
            )

        vlan_interface = f"{interface}.{vlan_id}"

        # Install VLAN support
        await connector.run_command("apt-get install -y vlan || yum install -y vconfig", sudo=True)
        await connector.run_command("modprobe 8021q", sudo=True)

        # Create VLAN
        result = await connector.run_command(
            f"ip link add link {interface} name {vlan_interface} type vlan id {vlan_id}",
            sudo=True,
        )

        if not result.success and "already exists" not in result.stderr:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to create VLAN {vlan_id}",
                details={"error": result.stderr},
            )

        # Bring up interface
        await connector.run_command(f"ip link set dev {vlan_interface} up", sudo=True)

        # Assign subnet if provided
        if subnet:
            await connector.run_command(
                f"ip addr add {subnet} dev {vlan_interface}",
                sudo=True,
            )

        # Create firewall rules for tenant isolation
        # Block traffic to other VLANs
        await connector.run_command(
            f"iptables -A FORWARD -i {vlan_interface} -o {interface}.+ ! -o {vlan_interface} -j DROP",
            sudo=True,
        )

        # Apply bandwidth limit if specified
        if bandwidth_limit:
            await connector.run_command(
                f"tc qdisc add dev {vlan_interface} root tbf rate {bandwidth_limit} burst 32kbit latency 400ms",
                sudo=True,
            )

        # Save configuration
        config_line = f"# Tenant {tenant_id}: VLAN {vlan_id}, Subnet {subnet or 'N/A'}, Bandwidth {bandwidth_limit or 'unlimited'}"
        await connector.run_command(
            f"echo '{config_line}' >> /etc/simpleinfra-tenants.conf",
            sudo=True,
        )

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Tenant {tenant_id} created with VLAN {vlan_id}",
            details={
                "tenant_id": tenant_id,
                "vlan_id": vlan_id,
                "vlan_interface": vlan_interface,
                "subnet": subnet,
                "bandwidth_limit": bandwidth_limit,
            },
        )

    async def _isolate_tenants(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Ensure all tenants are isolated from each other.

        Applies strict firewall rules to prevent inter-tenant traffic.
        """
        interface = params.get("interface", "eth0")

        # Get all VLAN interfaces
        result = await connector.run_command(f"ip link show | grep '{interface}\\.'")
        vlan_interfaces = []

        if result.success:
            import re
            for line in result.stdout.split('\n'):
                match = re.search(rf'{interface}\.\d+', line)
                if match:
                    vlan_interfaces.append(match.group(0))

        if not vlan_interfaces:
            return ModuleResult(
                changed=False,
                success=True,
                message="No tenant VLANs found",
                details={"vlan_count": 0},
            )

        # Create isolation rules
        rules_created = 0
        for vlan1 in vlan_interfaces:
            for vlan2 in vlan_interfaces:
                if vlan1 != vlan2:
                    # Block traffic from vlan1 to vlan2
                    await connector.run_command(
                        f"iptables -A FORWARD -i {vlan1} -o {vlan2} -j DROP",
                        sudo=True,
                    )
                    rules_created += 1

        # Save iptables rules
        await connector.run_command(
            "iptables-save > /etc/iptables/rules.v4 || netfilter-persistent save",
            sudo=True,
        )

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Tenant isolation applied: {len(vlan_interfaces)} tenants, {rules_created} rules",
            details={
                "tenant_count": len(vlan_interfaces),
                "vlan_interfaces": vlan_interfaces,
                "rules_created": rules_created,
            },
        )

    async def _set_bandwidth_limit(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Set or update bandwidth limit for a tenant."""
        tenant_id = params.get("tenant_id")
        vlan_id = params.get("vlan_id")
        bandwidth = params.get("bandwidth")
        interface = params.get("interface", "eth0")

        if not vlan_id or not bandwidth:
            return ModuleResult(
                changed=False,
                success=False,
                message="vlan_id and bandwidth are required",
            )

        vlan_interface = f"{interface}.{vlan_id}"

        # Remove existing qdisc
        await connector.run_command(
            f"tc qdisc del dev {vlan_interface} root 2>/dev/null || true",
            sudo=True,
        )

        # Add new bandwidth limit
        result = await connector.run_command(
            f"tc qdisc add dev {vlan_interface} root tbf rate {bandwidth} burst 32kbit latency 400ms",
            sudo=True,
        )

        return ModuleResult(
            changed=True,
            success=result.success,
            message=f"Bandwidth limit set to {bandwidth} for tenant {tenant_id or vlan_id}",
            details={
                "tenant_id": tenant_id,
                "vlan_interface": vlan_interface,
                "bandwidth": bandwidth,
            },
        )

    async def _list_tenants(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """List all configured tenants."""
        # Check for tenant configuration file
        result = await connector.run_command("cat /etc/simpleinfra-tenants.conf 2>/dev/null || echo ''")

        tenants = []
        if result.success and result.stdout:
            for line in result.stdout.split('\n'):
                if line.startswith('#') and 'Tenant' in line:
                    tenants.append(line.replace('# ', ''))

        # Also list VLAN interfaces
        vlan_result = await connector.run_command("ip link show | grep -E '\\.\\d+:'")
        vlan_count = len(vlan_result.stdout.split('\n')) if vlan_result.success else 0

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Found {len(tenants)} configured tenants, {vlan_count} VLAN interfaces",
            details={
                "tenants": tenants,
                "vlan_count": vlan_count,
            },
        )
