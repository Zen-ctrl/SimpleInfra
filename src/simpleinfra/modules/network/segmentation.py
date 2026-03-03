"""Network segmentation module for SimpleInfra.

Provides network segmentation capabilities including:
- VLAN management
- Firewall-based network isolation
- Micro-segmentation
- Network discovery
- Traffic control

All operations are agentless by default, using SSH.
Can optionally deploy lightweight monitoring agents.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class NetworkSegmentationModule(Module):
    """Network segmentation and isolation capabilities."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "isolate")

        if action == "isolate":
            return await self._isolate_network(connector, kwargs)
        elif action == "vlan":
            return await self._manage_vlan(connector, kwargs)
        elif action == "discover":
            return await self._discover_network(connector, kwargs)
        elif action == "zone":
            return await self._create_zone(connector, kwargs)
        elif action == "microsegment":
            return await self._microsegment(connector, kwargs)
        elif action == "traffic_control":
            return await self._traffic_control(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown network segmentation action: {action}",
            )

    async def _isolate_network(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Isolate a network segment using firewall rules.

        Creates a DMZ-style isolated network zone.
        """
        zone_name = params.get("zone", "isolated")
        allowed_ips = params.get("allowed_ips", [])
        allowed_ports = params.get("allowed_ports", [])
        default_policy = params.get("default_policy", "deny")

        # Detect firewall system
        ufw_check = await connector.run_command("which ufw")
        iptables_check = await connector.run_command("which iptables")

        if ufw_check.success:
            return await self._isolate_with_ufw(connector, zone_name, allowed_ips, allowed_ports, default_policy)
        elif iptables_check.success:
            return await self._isolate_with_iptables(connector, zone_name, allowed_ips, allowed_ports, default_policy)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="No supported firewall found (ufw or iptables required)",
            )

    async def _isolate_with_ufw(
        self,
        connector: "Connector",
        zone_name: str,
        allowed_ips: list[str],
        allowed_ports: list[int],
        default_policy: str,
    ) -> ModuleResult:
        """Create isolated network zone using UFW."""
        commands = []

        # Set default policy
        if default_policy == "deny":
            commands.append("ufw default deny incoming")
            commands.append("ufw default allow outgoing")

        # Allow specific IPs
        for ip in allowed_ips:
            commands.append(f"ufw allow from {ip}")

        # Allow specific ports
        for port in allowed_ports:
            commands.append(f"ufw allow {port}")

        # Enable UFW if not already enabled
        commands.append("ufw --force enable")

        # Execute all commands
        for cmd in commands:
            result = await connector.run_command(cmd, sudo=True)
            if not result.success:
                return ModuleResult(
                    changed=True,
                    success=False,
                    message=f"Failed to execute: {cmd}",
                    details={"error": result.stderr},
                )

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Network zone '{zone_name}' isolated successfully",
            details={
                "zone": zone_name,
                "allowed_ips": allowed_ips,
                "allowed_ports": allowed_ports,
                "policy": default_policy,
            },
        )

    async def _isolate_with_iptables(
        self,
        connector: "Connector",
        zone_name: str,
        allowed_ips: list[str],
        allowed_ports: list[int],
        default_policy: str,
    ) -> ModuleResult:
        """Create isolated network zone using iptables."""
        commands = []

        # Create custom chain for this zone
        chain_name = f"ZONE_{zone_name.upper()}"
        commands.append(f"iptables -N {chain_name} 2>/dev/null || iptables -F {chain_name}")

        # Set default policy
        if default_policy == "deny":
            commands.append("iptables -P INPUT DROP")
            commands.append("iptables -P FORWARD DROP")

        # Allow established connections
        commands.append("iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT")

        # Allow loopback
        commands.append("iptables -A INPUT -i lo -j ACCEPT")

        # Allow specific IPs
        for ip in allowed_ips:
            commands.append(f"iptables -A INPUT -s {ip} -j ACCEPT")

        # Allow specific ports
        for port in allowed_ports:
            commands.append(f"iptables -A INPUT -p tcp --dport {port} -j ACCEPT")

        # Save rules
        commands.append("iptables-save > /etc/iptables/rules.v4 || netfilter-persistent save")

        for cmd in commands:
            result = await connector.run_command(cmd, sudo=True)
            # Continue even on some failures (like chain already exists)

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Network zone '{zone_name}' isolated with iptables",
            details={
                "zone": zone_name,
                "chain": chain_name,
                "allowed_ips": allowed_ips,
                "allowed_ports": allowed_ports,
            },
        )

    async def _manage_vlan(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Create and manage VLANs."""
        vlan_id = params.get("vlan_id")
        interface = params.get("interface", "eth0")
        ip_address = params.get("ip_address")
        netmask = params.get("netmask", "255.255.255.0")
        operation = params.get("operation", "create")

        if not vlan_id:
            return ModuleResult(
                changed=False,
                success=False,
                message="VLAN ID is required",
            )

        vlan_interface = f"{interface}.{vlan_id}"

        if operation == "create":
            # Install vlan package
            await connector.run_command("apt-get install -y vlan || yum install -y vconfig", sudo=True)

            # Load 8021q module
            await connector.run_command("modprobe 8021q", sudo=True)

            # Create VLAN interface
            result = await connector.run_command(
                f"ip link add link {interface} name {vlan_interface} type vlan id {vlan_id}",
                sudo=True,
            )

            if not result.success:
                return ModuleResult(
                    changed=False,
                    success=False,
                    message=f"Failed to create VLAN {vlan_id}",
                    details={"error": result.stderr},
                )

            # Bring up interface
            await connector.run_command(f"ip link set dev {vlan_interface} up", sudo=True)

            # Assign IP if provided
            if ip_address:
                await connector.run_command(
                    f"ip addr add {ip_address}/{netmask} dev {vlan_interface}",
                    sudo=True,
                )

            return ModuleResult(
                changed=True,
                success=True,
                message=f"VLAN {vlan_id} created on {interface}",
                details={
                    "vlan_id": vlan_id,
                    "interface": vlan_interface,
                    "ip": ip_address,
                },
            )

        elif operation == "delete":
            result = await connector.run_command(f"ip link delete {vlan_interface}", sudo=True)
            return ModuleResult(
                changed=True,
                success=result.success,
                message=f"VLAN {vlan_id} {'deleted' if result.success else 'deletion failed'}",
            )

        return ModuleResult(
            changed=False,
            success=False,
            message=f"Unknown VLAN operation: {operation}",
        )

    async def _discover_network(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Discover network topology and connected devices."""
        subnet = params.get("subnet", "192.168.1.0/24")
        scan_type = params.get("scan_type", "ping")

        # Install nmap for network discovery
        await connector.run_command("apt-get install -y nmap || yum install -y nmap", sudo=True)

        if scan_type == "ping":
            # Quick ping scan
            result = await connector.run_command(f"nmap -sn {subnet}")
        elif scan_type == "full":
            # Full network scan with OS detection
            result = await connector.run_command(f"nmap -A {subnet}", sudo=True)
        elif scan_type == "fast":
            # Fast scan
            result = await connector.run_command(f"nmap -F {subnet}")
        else:
            result = await connector.run_command(f"nmap {subnet}")

        # Parse nmap output for host count
        import re
        host_count = len(re.findall(r"Nmap scan report for", result.stdout))

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Network discovery complete: {host_count} hosts found",
            details={
                "subnet": subnet,
                "hosts_found": host_count,
                "scan_output": result.stdout,
            },
        )

    async def _create_zone(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Create a network security zone with firewalld."""
        zone_name = params.get("zone")
        interfaces = params.get("interfaces", [])
        sources = params.get("sources", [])
        services = params.get("services", [])
        ports = params.get("ports", [])

        if not zone_name:
            return ModuleResult(
                changed=False,
                success=False,
                message="Zone name is required",
            )

        # Check for firewalld
        check = await connector.run_command("which firewall-cmd")
        if not check.success:
            # Install firewalld
            await connector.run_command("apt-get install -y firewalld || yum install -y firewalld", sudo=True)
            await connector.run_command("systemctl start firewalld", sudo=True)
            await connector.run_command("systemctl enable firewalld", sudo=True)

        # Create zone
        result = await connector.run_command(
            f"firewall-cmd --permanent --new-zone={zone_name}",
            sudo=True,
        )

        # Add interfaces to zone
        for interface in interfaces:
            await connector.run_command(
                f"firewall-cmd --permanent --zone={zone_name} --add-interface={interface}",
                sudo=True,
            )

        # Add source networks to zone
        for source in sources:
            await connector.run_command(
                f"firewall-cmd --permanent --zone={zone_name} --add-source={source}",
                sudo=True,
            )

        # Add services to zone
        for service in services:
            await connector.run_command(
                f"firewall-cmd --permanent --zone={zone_name} --add-service={service}",
                sudo=True,
            )

        # Add ports to zone
        for port in ports:
            await connector.run_command(
                f"firewall-cmd --permanent --zone={zone_name} --add-port={port}",
                sudo=True,
            )

        # Reload firewalld
        await connector.run_command("firewall-cmd --reload", sudo=True)

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Network zone '{zone_name}' created",
            details={
                "zone": zone_name,
                "interfaces": interfaces,
                "sources": sources,
                "services": services,
                "ports": ports,
            },
        )

    async def _microsegment(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Create micro-segmentation rules between specific hosts/services."""
        from_hosts = params.get("from", [])
        to_hosts = params.get("to", [])
        allowed_ports = params.get("ports", [])
        protocol = params.get("protocol", "tcp")

        if not from_hosts or not to_hosts:
            return ModuleResult(
                changed=False,
                success=False,
                message="Both 'from' and 'to' host lists are required",
            )

        rules_created = []

        # Create specific allow rules between hosts
        for from_host in from_hosts:
            for to_host in to_hosts:
                for port in allowed_ports:
                    # Create iptables rule
                    rule = (
                        f"iptables -A FORWARD -s {from_host} -d {to_host} "
                        f"-p {protocol} --dport {port} -j ACCEPT"
                    )
                    result = await connector.run_command(rule, sudo=True)

                    if result.success:
                        rules_created.append(
                            f"{from_host} -> {to_host}:{port}/{protocol}"
                        )

        # Default deny between these hosts for other traffic
        for from_host in from_hosts:
            for to_host in to_hosts:
                deny_rule = f"iptables -A FORWARD -s {from_host} -d {to_host} -j DROP"
                await connector.run_command(deny_rule, sudo=True)

        # Save rules
        await connector.run_command(
            "iptables-save > /etc/iptables/rules.v4 || netfilter-persistent save",
            sudo=True,
        )

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Micro-segmentation complete: {len(rules_created)} rules created",
            details={"rules": rules_created},
        )

    async def _traffic_control(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Control network traffic with tc (traffic control)."""
        interface = params.get("interface", "eth0")
        action = params.get("tc_action", "limit")
        bandwidth = params.get("bandwidth", "1mbit")
        delay = params.get("delay", "100ms")
        packet_loss = params.get("packet_loss", "0.1%")

        # Install tc
        await connector.run_command("apt-get install -y iproute2 || yum install -y iproute", sudo=True)

        if action == "limit":
            # Limit bandwidth
            commands = [
                f"tc qdisc del dev {interface} root 2>/dev/null || true",
                f"tc qdisc add dev {interface} root tbf rate {bandwidth} burst 32kbit latency 400ms",
            ]

        elif action == "delay":
            # Add network delay
            commands = [
                f"tc qdisc del dev {interface} root 2>/dev/null || true",
                f"tc qdisc add dev {interface} root netem delay {delay}",
            ]

        elif action == "loss":
            # Simulate packet loss
            commands = [
                f"tc qdisc del dev {interface} root 2>/dev/null || true",
                f"tc qdisc add dev {interface} root netem loss {packet_loss}",
            ]

        elif action == "remove":
            # Remove all traffic control
            commands = [f"tc qdisc del dev {interface} root"]

        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown traffic control action: {action}",
            )

        for cmd in commands:
            await connector.run_command(cmd, sudo=True)

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Traffic control applied to {interface}",
            details={
                "interface": interface,
                "action": action,
                "bandwidth": bandwidth if action == "limit" else None,
                "delay": delay if action == "delay" else None,
                "packet_loss": packet_loss if action == "loss" else None,
            },
        )
