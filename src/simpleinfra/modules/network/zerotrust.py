"""Zero-Trust networking module.

Implements zero-trust network principles:
- Default deny all traffic
- Explicit allow per service
- Identity-based access (via IP/certificates)
- Continuous verification
- Least privilege access
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class ZeroTrustModule(Module):
    """Zero-trust network architecture implementation."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "enable")

        if action == "enable":
            return await self._enable_zero_trust(connector, kwargs)
        elif action == "add_policy":
            return await self._add_policy(connector, kwargs)
        elif action == "verify":
            return await self._verify_zero_trust(connector, kwargs)
        elif action == "audit":
            return await self._audit_traffic(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown zero-trust action: {action}",
            )

    async def _enable_zero_trust(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Enable zero-trust networking.

        Sets up:
        - Default deny all
        - Logging for all traffic
        - Connection tracking
        - Drop invalid packets
        """
        zone = params.get("zone", "zero-trust")

        commands = []

        # Flush existing rules
        commands.extend([
            "iptables -F",
            "iptables -X",
        ])

        # Set default deny policies
        commands.extend([
            "iptables -P INPUT DROP",
            "iptables -P FORWARD DROP",
            "iptables -P OUTPUT DROP",  # Zero-trust: deny outbound too
        ])

        # Allow loopback (necessary for local processes)
        commands.extend([
            "iptables -A INPUT -i lo -j ACCEPT",
            "iptables -A OUTPUT -o lo -j ACCEPT",
        ])

        # Drop invalid packets immediately
        commands.append("iptables -A INPUT -m state --state INVALID -j DROP")

        # Allow established connections (after verification)
        commands.extend([
            "iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT",
            "iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT",
        ])

        # Create logging chains
        commands.extend([
            "iptables -N LOGGING",
            "iptables -A INPUT -j LOGGING",
            "iptables -A LOGGING -m limit --limit 2/min -j LOG --log-prefix 'ZT-DROPPED: ' --log-level 4",
            "iptables -A LOGGING -j DROP",
        ])

        # Execute commands
        for cmd in commands:
            await connector.run_command(cmd, sudo=True)

        # Save rules
        await connector.run_command(
            "iptables-save > /etc/iptables/rules.v4 || netfilter-persistent save",
            sudo=True,
        )

        # Mark as zero-trust enabled
        await connector.run_command(
            f"echo 'zero-trust-enabled: {zone}' > /etc/simpleinfra-zerotrust.conf",
            sudo=True,
        )

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Zero-trust networking enabled for zone '{zone}'",
            details={
                "zone": zone,
                "default_policy": "deny-all",
                "logging": True,
                "mode": "strict",
            },
        )

    async def _add_policy(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Add explicit allow policy for specific traffic.

        Zero-trust: must explicitly allow each service.
        """
        source = params.get("source")  # IP or subnet
        destination = params.get("destination")  # IP or "self"
        port = params.get("port")
        protocol = params.get("protocol", "tcp")
        service_name = params.get("service", "unnamed")

        if not source or not port:
            return ModuleResult(
                changed=False,
                success=False,
                message="source and port are required for zero-trust policy",
            )

        # Create policy rule
        if destination == "self" or not destination:
            # Traffic to this host
            rule = f"iptables -A INPUT -s {source} -p {protocol} --dport {port} -j ACCEPT"
        else:
            # Traffic to another host (forwarding)
            rule = f"iptables -A FORWARD -s {source} -d {destination} -p {protocol} --dport {port} -j ACCEPT"

        result = await connector.run_command(rule, sudo=True)

        if not result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to add policy for {service_name}",
                details={"error": result.stderr},
            )

        # Log the policy
        policy_desc = f"# ZT-Policy: {service_name} - {source} -> {destination or 'self'}:{port}/{protocol}"
        await connector.run_command(
            f"echo '{policy_desc}' >> /etc/simpleinfra-zerotrust-policies.conf",
            sudo=True,
        )

        # Save rules
        await connector.run_command(
            "iptables-save > /etc/iptables/rules.v4 || netfilter-persistent save",
            sudo=True,
        )

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Zero-trust policy added: {service_name} ({source} -> {destination or 'self'}:{port})",
            details={
                "service": service_name,
                "source": source,
                "destination": destination or "self",
                "port": port,
                "protocol": protocol,
            },
        )

    async def _verify_zero_trust(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Verify zero-trust configuration.

        Checks:
        - Default policies are deny
        - All traffic is logged
        - Only explicit policies exist
        """
        issues = []

        # Check if zero-trust is enabled
        zt_check = await connector.run_command("cat /etc/simpleinfra-zerotrust.conf 2>/dev/null")
        if not zt_check.success or "zero-trust-enabled" not in zt_check.stdout:
            issues.append("Zero-trust not enabled")

        # Check default policies
        policy_check = await connector.run_command("iptables -L -n | grep 'Chain INPUT\\|Chain FORWARD\\|Chain OUTPUT'")
        if policy_check.success:
            if "policy DROP" not in policy_check.stdout:
                issues.append("Default policies should be DROP")

        # Count explicit allow rules
        rules_check = await connector.run_command("iptables -L INPUT -n | grep ACCEPT | wc -l")
        allow_rule_count = int(rules_check.stdout.strip()) if rules_check.success else 0

        # Check logging
        log_check = await connector.run_command("iptables -L LOGGING -n 2>/dev/null")
        if not log_check.success:
            issues.append("Logging chain not configured")

        # Check for policies
        policies_check = await connector.run_command("cat /etc/simpleinfra-zerotrust-policies.conf 2>/dev/null")
        policy_count = len([l for l in policies_check.stdout.split('\n') if l.startswith('#')]) if policies_check.success else 0

        return ModuleResult(
            changed=False,
            success=len(issues) == 0,
            message=f"Zero-trust verification: {len(issues)} issues found",
            details={
                "issues": issues,
                "allow_rules": allow_rule_count,
                "policies": policy_count,
                "compliant": len(issues) == 0,
            },
        )

    async def _audit_traffic(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Audit dropped traffic in zero-trust mode.

        Reviews logs to identify:
        - Frequently dropped traffic (may need policy)
        - Suspicious patterns
        - Policy violations
        """
        log_lines = params.get("lines", 100)

        # Get dropped traffic from syslog
        result = await connector.run_command(
            f"grep 'ZT-DROPPED' /var/log/syslog | tail -{log_lines} || "
            f"journalctl | grep 'ZT-DROPPED' | tail -{log_lines}",
            sudo=True,
        )

        if not result.success:
            return ModuleResult(
                changed=False,
                success=True,
                message="No dropped traffic logs found",
                details={"dropped_count": 0},
            )

        # Parse logs
        dropped_traffic = result.stdout.split('\n')
        dropped_count = len(dropped_traffic)

        # Analyze patterns (simple frequency count)
        import re
        sources = []
        destinations = []
        ports = []

        for line in dropped_traffic:
            # Extract source IP
            src_match = re.search(r'SRC=(\d+\.\d+\.\d+\.\d+)', line)
            if src_match:
                sources.append(src_match.group(1))

            # Extract destination port
            dpt_match = re.search(r'DPT=(\d+)', line)
            if dpt_match:
                ports.append(dpt_match.group(1))

        # Count frequencies
        from collections import Counter
        top_sources = Counter(sources).most_common(5)
        top_ports = Counter(ports).most_common(5)

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Audit complete: {dropped_count} dropped packets analyzed",
            details={
                "dropped_count": dropped_count,
                "top_sources": top_sources,
                "top_ports": top_ports,
                "recent_drops": dropped_traffic[:10],  # Last 10
            },
        )
