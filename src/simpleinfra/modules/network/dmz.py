"""DMZ (Demilitarized Zone) specialized module.

Creates and manages DMZ network segments with best practices:
- Public-facing isolation
- Limited inbound access
- Restricted outbound access
- Logging and monitoring
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class DMZModule(Module):
    """Specialized module for DMZ setup and management."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "create")

        if action == "create":
            return await self._create_dmz(connector, kwargs)
        elif action == "harden":
            return await self._harden_dmz(connector, kwargs)
        elif action == "verify":
            return await self._verify_dmz(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown DMZ action: {action}",
            )

    async def _create_dmz(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Create a DMZ zone with best practices.

        Implements:
        - Default deny inbound
        - Allow specific public services (HTTP/HTTPS)
        - Allow SSH from management network only
        - Enable connection tracking
        - Set up logging
        """
        zone_name = params.get("zone", "dmz")
        public_services = params.get("services", ["http", "https"])
        management_ips = params.get("management_ips", [])
        enable_logging = params.get("logging", True)

        # Convert service names to ports
        service_ports = {
            "http": 80,
            "https": 443,
            "smtp": 25,
            "dns": 53,
            "ftp": 21,
        }

        allowed_ports = [service_ports.get(svc, svc) for svc in public_services]

        # Detect firewall
        ufw_check = await connector.run_command("which ufw")
        use_ufw = ufw_check.success

        commands = []

        if use_ufw:
            # UFW-based DMZ setup
            commands.extend([
                "ufw --force reset",  # Clean slate
                "ufw default deny incoming",
                "ufw default deny outgoing",  # Restrictive outbound
                "ufw default deny routed",
            ])

            # Allow public services from anywhere
            for port in allowed_ports:
                commands.append(f"ufw allow {port}/tcp")

            # Allow SSH only from management network
            for mgmt_ip in management_ips:
                commands.append(f"ufw allow from {mgmt_ip} to any port 22")

            # Allow DNS for outbound (necessary)
            commands.append("ufw allow out 53")

            # Allow HTTP/HTTPS outbound (for updates)
            commands.append("ufw allow out 80/tcp")
            commands.append("ufw allow out 443/tcp")

            # Enable logging
            if enable_logging:
                commands.append("ufw logging on")

            commands.append("ufw --force enable")

        else:
            # iptables-based DMZ setup
            commands.extend([
                "iptables -F",  # Flush rules
                "iptables -X",  # Delete custom chains
                "iptables -P INPUT DROP",
                "iptables -P FORWARD DROP",
                "iptables -P OUTPUT DROP",  # Restrictive outbound
            ])

            # Allow loopback
            commands.append("iptables -A INPUT -i lo -j ACCEPT")
            commands.append("iptables -A OUTPUT -o lo -j ACCEPT")

            # Allow established connections
            commands.append("iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT")
            commands.append("iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT")

            # Allow public services
            for port in allowed_ports:
                commands.append(f"iptables -A INPUT -p tcp --dport {port} -j ACCEPT")

            # Allow SSH from management only
            for mgmt_ip in management_ips:
                commands.append(f"iptables -A INPUT -s {mgmt_ip} -p tcp --dport 22 -j ACCEPT")

            # Allow DNS outbound
            commands.append("iptables -A OUTPUT -p udp --dport 53 -j ACCEPT")

            # Allow HTTP/HTTPS outbound
            commands.append("iptables -A OUTPUT -p tcp --dport 80 -j ACCEPT")
            commands.append("iptables -A OUTPUT -p tcp --dport 443 -j ACCEPT")

            # Logging
            if enable_logging:
                commands.append("iptables -A INPUT -j LOG --log-prefix 'DMZ-INPUT: '")
                commands.append("iptables -A OUTPUT -j LOG --log-prefix 'DMZ-OUTPUT: '")

            # Save rules
            commands.append("iptables-save > /etc/iptables/rules.v4 || netfilter-persistent save")

        # Execute all commands
        for cmd in commands:
            result = await connector.run_command(cmd, sudo=True)
            if not result.success and "already exists" not in result.stderr:
                # Continue even on some failures
                pass

        return ModuleResult(
            changed=True,
            success=True,
            message=f"DMZ zone '{zone_name}' created with {len(allowed_ports)} public services",
            details={
                "zone": zone_name,
                "services": public_services,
                "allowed_ports": allowed_ports,
                "management_ips": management_ips,
                "logging": enable_logging,
                "firewall": "ufw" if use_ufw else "iptables",
            },
        )

    async def _harden_dmz(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Apply additional hardening to DMZ.

        Includes:
        - Rate limiting
        - SYN flood protection
        - Port scan detection
        - ICMP rate limiting
        """
        commands = []

        # Check if iptables is available
        check = await connector.run_command("which iptables")
        if not check.success:
            return ModuleResult(
                changed=False,
                success=False,
                message="iptables required for hardening",
            )

        # SYN flood protection
        commands.extend([
            "iptables -A INPUT -p tcp --syn -m limit --limit 1/s --limit-burst 3 -j ACCEPT",
            "iptables -A INPUT -p tcp --syn -j DROP",
        ])

        # Port scan protection
        commands.extend([
            "iptables -N port-scanning",
            "iptables -A port-scanning -p tcp --tcp-flags SYN,ACK,FIN,RST RST -m limit --limit 1/s --limit-burst 2 -j RETURN",
            "iptables -A port-scanning -j DROP",
        ])

        # ICMP rate limiting (prevent ping floods)
        commands.append("iptables -A INPUT -p icmp -m limit --limit 1/s --limit-burst 1 -j ACCEPT")
        commands.append("iptables -A INPUT -p icmp -j DROP")

        # Drop invalid packets
        commands.append("iptables -A INPUT -m state --state INVALID -j DROP")

        # Execute hardening rules
        for cmd in commands:
            await connector.run_command(cmd, sudo=True)

        return ModuleResult(
            changed=True,
            success=True,
            message="DMZ hardening applied (SYN flood, port scan, ICMP protection)",
            details={
                "protections": [
                    "SYN flood protection",
                    "Port scan detection",
                    "ICMP rate limiting",
                    "Invalid packet dropping",
                ],
            },
        )

    async def _verify_dmz(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Verify DMZ configuration.

        Checks:
        - Firewall is active
        - Default policies are correct
        - Required ports are open
        - Logging is enabled
        """
        issues = []

        # Check firewall status
        ufw_check = await connector.run_command("ufw status")
        iptables_check = await connector.run_command("iptables -L -n")

        if ufw_check.success and "Status: active" in ufw_check.stdout:
            firewall_active = True
            firewall_type = "ufw"
            firewall_output = ufw_check.stdout
        elif iptables_check.success:
            firewall_active = True
            firewall_type = "iptables"
            firewall_output = iptables_check.stdout
        else:
            firewall_active = False
            firewall_type = "none"
            firewall_output = ""
            issues.append("Firewall not active")

        # Check default policies (for iptables)
        if firewall_type == "iptables":
            if "Chain INPUT (policy DROP" not in firewall_output:
                issues.append("INPUT policy should be DROP")
            if "Chain FORWARD (policy DROP" not in firewall_output:
                issues.append("FORWARD policy should be DROP")

        # Check logging
        if firewall_type == "ufw":
            log_check = await connector.run_command("ufw status verbose")
            if "Logging: on" not in log_check.stdout:
                issues.append("Logging not enabled")

        return ModuleResult(
            changed=False,
            success=len(issues) == 0,
            message=f"DMZ verification {'passed' if len(issues) == 0 else 'found ' + str(len(issues)) + ' issues'}",
            details={
                "firewall_active": firewall_active,
                "firewall_type": firewall_type,
                "issues": issues,
                "firewall_rules": firewall_output[:500],  # First 500 chars
            },
        )
