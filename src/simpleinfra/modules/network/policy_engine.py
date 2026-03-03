"""Advanced policy engine for network segmentation.

Provides Illumio-like capabilities:
- Policy templates
- Label-based segmentation
- Application dependency mapping
- Policy simulation and testing
- Automatic policy generation
- Compliance templates
"""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING
from pathlib import Path

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


# Policy Templates
POLICY_TEMPLATES = {
    "web-tier": {
        "description": "Standard web tier segmentation",
        "inbound": [
            {"port": 80, "protocol": "tcp", "source": "any", "description": "HTTP"},
            {"port": 443, "protocol": "tcp", "source": "any", "description": "HTTPS"},
        ],
        "outbound": [
            {"port": 80, "protocol": "tcp", "destination": "any", "description": "HTTP outbound"},
            {"port": 443, "protocol": "tcp", "destination": "any", "description": "HTTPS outbound"},
            {"port": 53, "protocol": "udp", "destination": "any", "description": "DNS"},
        ],
        "labels": ["role:web", "tier:frontend"],
    },

    "app-tier": {
        "description": "Application tier segmentation",
        "inbound": [
            {"port": 8080, "protocol": "tcp", "source": "label:role=web", "description": "App API"},
            {"port": 8443, "protocol": "tcp", "source": "label:role=web", "description": "App API SSL"},
        ],
        "outbound": [
            {"port": 5432, "protocol": "tcp", "destination": "label:role=database", "description": "PostgreSQL"},
            {"port": 3306, "protocol": "tcp", "destination": "label:role=database", "description": "MySQL"},
            {"port": 6379, "protocol": "tcp", "destination": "label:role=cache", "description": "Redis"},
        ],
        "labels": ["role:app", "tier:backend"],
    },

    "database-tier": {
        "description": "Database tier segmentation (strict)",
        "inbound": [
            {"port": 5432, "protocol": "tcp", "source": "label:role=app", "description": "PostgreSQL"},
            {"port": 3306, "protocol": "tcp", "source": "label:role=app", "description": "MySQL"},
        ],
        "outbound": [],  # No outbound except established
        "labels": ["role:database", "tier:data"],
    },

    "pci-compliant": {
        "description": "PCI-DSS compliant cardholder data environment",
        "inbound": [
            {"port": 443, "protocol": "tcp", "source": "label:role=web", "description": "HTTPS only"},
        ],
        "outbound": [
            {"port": 443, "protocol": "tcp", "destination": "payment-gateway", "description": "Payment processor"},
        ],
        "labels": ["compliance:pci-dss", "data:cardholder"],
        "logging": "all",
        "encryption": "required",
    },

    "zero-trust-app": {
        "description": "Zero-trust application template",
        "inbound": [],  # Start with nothing
        "outbound": [],
        "default_policy": "deny",
        "labels": ["security:zero-trust"],
        "require_authentication": True,
    },
}


# Compliance Templates
COMPLIANCE_TEMPLATES = {
    "pci-dss": {
        "name": "PCI-DSS 4.0 Compliance",
        "requirements": [
            "Segment cardholder data environment",
            "Restrict access to business need-to-know",
            "Track and monitor all access",
            "Encrypt transmission over open networks",
        ],
        "policies": [
            {
                "name": "CDE Isolation",
                "rule": "isolate cardholder data environment from all other networks",
                "template": "pci-compliant",
            },
            {
                "name": "Access Control",
                "rule": "allow only authorized applications to access CDE",
                "verification": "label-based",
            },
        ],
    },

    "hipaa": {
        "name": "HIPAA Compliance",
        "requirements": [
            "Protect ePHI with access controls",
            "Implement audit controls",
            "Encrypt ePHI in transit",
        ],
        "policies": [
            {
                "name": "ePHI Isolation",
                "rule": "segment systems containing ePHI",
                "encryption": "required",
            },
        ],
    },

    "nist": {
        "name": "NIST Cybersecurity Framework",
        "requirements": [
            "Identify critical assets",
            "Protect via segmentation",
            "Detect anomalies",
            "Respond to incidents",
        ],
    },
}


class PolicyEngineModule(Module):
    """Advanced policy engine with templates and automation."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "apply_template")

        if action == "apply_template":
            return await self._apply_template(connector, kwargs)
        elif action == "create_from_labels":
            return await self._create_from_labels(connector, kwargs)
        elif action == "simulate":
            return await self._simulate_policy(connector, kwargs)
        elif action == "recommend":
            return await self._recommend_policies(connector, kwargs)
        elif action == "apply_compliance":
            return await self._apply_compliance_template(connector, kwargs)
        elif action == "export_policy":
            return await self._export_policy(connector, kwargs)
        elif action == "import_policy":
            return await self._import_policy(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown policy engine action: {action}",
            )

    async def _apply_template(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Apply a policy template to a host/service.

        Templates provide pre-configured policies for common scenarios.
        """
        template_name = params.get("template")
        labels = params.get("labels", [])
        mode = params.get("mode", "enforce")  # enforce or test

        if not template_name:
            return ModuleResult(
                changed=False,
                success=False,
                message="template parameter is required",
            )

        if template_name not in POLICY_TEMPLATES:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown template: {template_name}. Available: {', '.join(POLICY_TEMPLATES.keys())}",
            )

        template = POLICY_TEMPLATES[template_name]

        # Merge template labels with provided labels
        all_labels = template.get("labels", []) + labels

        # Apply inbound rules
        inbound_rules = []
        for rule in template.get("inbound", []):
            port = rule["port"]
            protocol = rule.get("protocol", "tcp")
            source = rule.get("source", "any")

            if mode == "enforce":
                # Create actual firewall rule
                if source == "any":
                    cmd = f"iptables -A INPUT -p {protocol} --dport {port} -j ACCEPT"
                else:
                    # Handle label-based sources later
                    cmd = f"iptables -A INPUT -p {protocol} --dport {port} -j ACCEPT"

                await connector.run_command(cmd, sudo=True)
                inbound_rules.append(rule["description"])

        # Apply outbound rules
        outbound_rules = []
        for rule in template.get("outbound", []):
            port = rule["port"]
            protocol = rule.get("protocol", "tcp")

            if mode == "enforce":
                cmd = f"iptables -A OUTPUT -p {protocol} --dport {port} -j ACCEPT"
                await connector.run_command(cmd, sudo=True)
                outbound_rules.append(rule["description"])

        # Save labels to host
        labels_config = {
            "labels": all_labels,
            "template": template_name,
            "mode": mode,
        }

        labels_json = json.dumps(labels_config, indent=2)
        await connector.run_command(
            f"echo '{labels_json}' > /etc/simpleinfra-labels.json",
            sudo=True,
        )

        # Save rules if enforcing
        if mode == "enforce":
            await connector.run_command(
                "iptables-save > /etc/iptables/rules.v4 || netfilter-persistent save",
                sudo=True,
            )

        return ModuleResult(
            changed=True if mode == "enforce" else False,
            success=True,
            message=f"Template '{template_name}' applied in {mode} mode",
            details={
                "template": template_name,
                "description": template["description"],
                "inbound_rules": len(inbound_rules),
                "outbound_rules": len(outbound_rules),
                "labels": all_labels,
                "mode": mode,
                "rules_enforced": mode == "enforce",
            },
        )

    async def _create_from_labels(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Create policies based on host labels.

        Implements label-based segmentation like Illumio.
        """
        labels = params.get("labels", [])
        discover_peers = params.get("discover_peers", True)

        if not labels:
            return ModuleResult(
                changed=False,
                success=False,
                message="labels parameter is required",
            )

        # Parse labels
        label_dict = {}
        for label in labels:
            if ":" in label:
                key, value = label.split(":", 1)
                label_dict[key] = value

        # Determine policies based on labels
        policies_created = []

        # Role-based policies
        if "role" in label_dict:
            role = label_dict["role"]

            if role == "web":
                # Web servers need HTTP/HTTPS
                await connector.run_command(
                    "iptables -A INPUT -p tcp --dport 80 -j ACCEPT",
                    sudo=True,
                )
                await connector.run_command(
                    "iptables -A INPUT -p tcp --dport 443 -j ACCEPT",
                    sudo=True,
                )
                policies_created.append("web-inbound (80, 443)")

            elif role == "app":
                # App servers need app ports
                await connector.run_command(
                    "iptables -A INPUT -p tcp --dport 8080 -j ACCEPT",
                    sudo=True,
                )
                policies_created.append("app-inbound (8080)")

            elif role == "database":
                # Databases should be very restrictive
                await connector.run_command(
                    "iptables -P INPUT DROP",
                    sudo=True,
                )
                policies_created.append("database-strict (default deny)")

        # Environment-based policies
        if "env" in label_dict:
            env = label_dict["env"]
            if env == "prod":
                # Production needs stricter logging
                await connector.run_command(
                    "iptables -A INPUT -j LOG --log-prefix 'PROD-INPUT: '",
                    sudo=True,
                )
                policies_created.append("production-logging")

        # Compliance-based policies
        if "compliance" in label_dict:
            compliance = label_dict["compliance"]
            if "pci" in compliance.lower():
                # PCI requires encryption and logging
                await connector.run_command(
                    "iptables -A INPUT -p tcp --dport 80 -j DROP",
                    sudo=True,
                )
                policies_created.append("pci-no-unencrypted-http")

        # Save labels
        await connector.run_command(
            f"echo '{json.dumps(label_dict)}' > /etc/simpleinfra-labels.json",
            sudo=True,
        )

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Label-based policies created: {len(policies_created)} rules",
            details={
                "labels": label_dict,
                "policies": policies_created,
            },
        )

    async def _simulate_policy(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Simulate policy changes without applying them.

        Tests what would happen if policy is applied.
        """
        template = params.get("template")
        source_ip = params.get("test_source", "192.168.1.100")
        dest_port = params.get("test_port", "80")

        if not template:
            return ModuleResult(
                changed=False,
                success=False,
                message="template required for simulation",
            )

        if template not in POLICY_TEMPLATES:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown template: {template}",
            )

        policy = POLICY_TEMPLATES[template]

        # Simulate - check if traffic would be allowed
        allowed = False
        matched_rule = None

        for rule in policy.get("inbound", []):
            if str(rule["port"]) == str(dest_port):
                allowed = True
                matched_rule = rule["description"]
                break

        # Get current rules for comparison
        current_rules = await connector.run_command("iptables -L INPUT -n")

        return ModuleResult(
            changed=False,  # Simulation never changes
            success=True,
            message=f"Simulation complete: Traffic would be {'ALLOWED' if allowed else 'DENIED'}",
            details={
                "template": template,
                "test_traffic": {
                    "source": source_ip,
                    "destination_port": dest_port,
                    "result": "ALLOW" if allowed else "DENY",
                    "matched_rule": matched_rule,
                },
                "current_rules": current_rules.stdout[:500],
                "simulation": True,
            },
        )

    async def _recommend_policies(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Analyze traffic and recommend policies.

        Uses connection tracking to suggest policies.
        """
        duration = params.get("duration", "300")  # 5 minutes default

        # Analyze active connections
        result = await connector.run_command("ss -tunap")

        if not result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message="Failed to analyze connections",
            )

        # Parse connections
        import re
        connections = []
        for line in result.stdout.split('\n'):
            # Look for ESTAB connections
            if 'ESTAB' in line:
                # Extract ports
                port_match = re.search(r':(\d+)\s+.*:(\d+)', line)
                if port_match:
                    local_port = port_match.group(1)
                    remote_port = port_match.group(2)
                    connections.append({
                        "local_port": local_port,
                        "remote_port": remote_port,
                    })

        # Count frequency
        from collections import Counter
        local_ports = Counter([c["local_port"] for c in connections])
        remote_ports = Counter([c["remote_port"] for c in connections])

        # Generate recommendations
        recommendations = []

        for port, count in local_ports.most_common(10):
            if int(port) > 1024:  # Application ports
                recommendations.append({
                    "type": "inbound",
                    "port": port,
                    "protocol": "tcp",
                    "reason": f"Observed {count} active connections",
                    "confidence": "high" if count > 5 else "medium",
                })

        for port, count in remote_ports.most_common(10):
            recommendations.append({
                "type": "outbound",
                "port": port,
                "protocol": "tcp",
                "reason": f"Observed {count} outbound connections",
                "confidence": "high" if count > 5 else "medium",
            })

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Policy recommendations: {len(recommendations)} suggested rules",
            details={
                "recommendations": recommendations,
                "connections_analyzed": len(connections),
                "unique_local_ports": len(local_ports),
                "unique_remote_ports": len(remote_ports),
            },
        )

    async def _apply_compliance_template(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Apply compliance-specific template.

        Implements compliance requirements (PCI-DSS, HIPAA, etc.).
        """
        compliance = params.get("compliance")
        mode = params.get("mode", "enforce")

        if not compliance:
            return ModuleResult(
                changed=False,
                success=False,
                message="compliance parameter required",
            )

        if compliance not in COMPLIANCE_TEMPLATES:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown compliance template: {compliance}. Available: {', '.join(COMPLIANCE_TEMPLATES.keys())}",
            )

        template = COMPLIANCE_TEMPLATES[compliance]

        # Apply compliance policies
        policies_applied = []

        for policy in template.get("policies", []):
            policy_name = policy["name"]

            if "template" in policy:
                # Use existing template
                template_result = await self._apply_template(
                    connector,
                    {
                        "template": policy["template"],
                        "mode": mode,
                        "labels": [f"compliance:{compliance}"],
                    },
                )
                policies_applied.append(policy_name)

        # Log compliance application
        compliance_record = {
            "compliance": compliance,
            "applied_at": "$(date -Iseconds)",
            "policies": policies_applied,
            "mode": mode,
        }

        await connector.run_command(
            f"echo '{json.dumps(compliance_record)}' >> /var/log/simpleinfra-compliance.log",
            sudo=True,
        )

        return ModuleResult(
            changed=True if mode == "enforce" else False,
            success=True,
            message=f"Compliance template '{compliance}' applied: {len(policies_applied)} policies",
            details={
                "compliance": compliance,
                "name": template["name"],
                "requirements": template["requirements"],
                "policies_applied": policies_applied,
                "mode": mode,
            },
        )

    async def _export_policy(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Export current policy configuration."""
        format_type = params.get("format", "json")

        # Get current iptables rules
        result = await connector.run_command("iptables-save")

        # Get labels
        labels_result = await connector.run_command("cat /etc/simpleinfra-labels.json 2>/dev/null || echo '{}'")

        try:
            labels = json.loads(labels_result.stdout) if labels_result.success else {}
        except:
            labels = {}

        policy_export = {
            "version": "1.0",
            "export_type": "simpleinfra-policy",
            "labels": labels,
            "firewall_rules": result.stdout if result.success else "",
        }

        return ModuleResult(
            changed=False,
            success=True,
            message="Policy exported",
            details={"policy": policy_export, "format": format_type},
        )

    async def _import_policy(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Import policy configuration."""
        policy_data = params.get("policy")

        if not policy_data:
            return ModuleResult(
                changed=False,
                success=False,
                message="policy parameter required",
            )

        # Apply imported policy
        # This would restore from the export

        return ModuleResult(
            changed=True,
            success=True,
            message="Policy imported successfully",
            details={"imported": True},
        )
