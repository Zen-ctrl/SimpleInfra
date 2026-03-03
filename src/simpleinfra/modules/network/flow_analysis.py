"""Traffic flow analysis and visualization module.

Provides:
- Real-time flow monitoring
- Flow visualization
- Anomaly detection
- Baseline learning
- Flow-based policy recommendations
"""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING
from collections import Counter, defaultdict

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class FlowAnalysisModule(Module):
    """Traffic flow analysis and monitoring."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "monitor")

        if action == "monitor":
            return await self._monitor_flows(connector, kwargs)
        elif action == "baseline":
            return await self._create_baseline(connector, kwargs)
        elif action == "detect_anomalies":
            return await self._detect_anomalies(connector, kwargs)
        elif action == "visualize":
            return await self._visualize_flows(connector, kwargs)
        elif action == "top_talkers":
            return await self._identify_top_talkers(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown flow analysis action: {action}",
            )

    async def _monitor_flows(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Monitor network flows in real-time."""
        duration = params.get("duration", 60)
        interval = params.get("interval", 10)

        flows = []
        iterations = duration // interval

        for i in range(iterations):
            # Get current connections
            result = await connector.run_command("ss -tinp")

            if result.success:
                import re
                for line in result.stdout.split('\n'):
                    if 'ESTAB' in line:
                        # Parse connection
                        addr_match = re.search(
                            r'(\d+\.\d+\.\d+\.\d+):(\d+)\s+(\d+\.\d+\.\d+\.\d+):(\d+)',
                            line
                        )
                        if addr_match:
                            flows.append({
                                "timestamp": i * interval,
                                "src_ip": addr_match.group(1),
                                "src_port": addr_match.group(2),
                                "dst_ip": addr_match.group(3),
                                "dst_port": addr_match.group(4),
                                "state": "ESTAB",
                            })

            if i < iterations - 1:
                # Sleep between iterations
                await connector.run_command(f"sleep {interval}")

        # Analyze flows
        src_ips = Counter([f["src_ip"] for f in flows])
        dst_ips = Counter([f["dst_ip"] for f in flows])
        dst_ports = Counter([f["dst_port"] for f in flows])

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Flow monitoring complete: {len(flows)} flows captured",
            details={
                "total_flows": len(flows),
                "unique_sources": len(src_ips),
                "unique_destinations": len(dst_ips),
                "top_sources": src_ips.most_common(5),
                "top_destinations": dst_ips.most_common(5),
                "top_ports": dst_ports.most_common(10),
                "flows": flows[:100],  # First 100 flows
            },
        )

    async def _create_baseline(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Create traffic baseline for anomaly detection."""
        duration = params.get("duration", 300)  # 5 minutes
        baseline_name = params.get("name", "default")

        # Monitor flows for baseline period
        monitor_result = await self._monitor_flows(
            connector,
            {"duration": duration, "interval": 30}
        )

        if not monitor_result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message="Failed to create baseline",
            )

        # Extract baseline characteristics
        details = monitor_result.details

        baseline = {
            "name": baseline_name,
            "created_at": "$(date -Iseconds)",
            "duration": duration,
            "characteristics": {
                "average_flows": details["total_flows"] // (duration // 30),
                "typical_sources": details["top_sources"],
                "typical_destinations": details["top_destinations"],
                "typical_ports": details["top_ports"],
            },
        }

        # Save baseline
        await connector.run_command(
            f"echo '{json.dumps(baseline, indent=2)}' > /etc/simpleinfra-baseline-{baseline_name}.json",
            sudo=True,
        )

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Baseline '{baseline_name}' created from {duration}s of traffic",
            details=baseline,
        )

    async def _detect_anomalies(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Detect anomalies compared to baseline."""
        baseline_name = params.get("baseline", "default")
        sensitivity = params.get("sensitivity", "medium")  # low, medium, high

        # Load baseline
        baseline_result = await connector.run_command(
            f"cat /etc/simpleinfra-baseline-{baseline_name}.json 2>/dev/null"
        )

        if not baseline_result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Baseline '{baseline_name}' not found",
            )

        try:
            baseline = json.loads(baseline_result.stdout)
        except:
            return ModuleResult(
                changed=False,
                success=False,
                message="Invalid baseline data",
            )

        # Monitor current traffic
        monitor_result = await self._monitor_flows(
            connector,
            {"duration": 60, "interval": 10}
        )

        if not monitor_result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message="Failed to monitor current traffic",
            )

        current = monitor_result.details

        # Detect anomalies
        anomalies = []

        # Check for unusual sources
        baseline_sources = {src for src, _ in baseline["characteristics"]["typical_sources"]}
        current_sources = {src for src, _ in current["top_sources"]}

        new_sources = current_sources - baseline_sources
        if new_sources:
            anomalies.append({
                "type": "new_source_ips",
                "severity": "medium",
                "details": list(new_sources),
                "description": f"{len(new_sources)} new source IPs not in baseline",
            })

        # Check for unusual ports
        baseline_ports = {port for port, _ in baseline["characteristics"]["typical_ports"][:5]}
        current_top_ports = {port for port, _ in current["top_ports"][:5]}

        new_ports = current_top_ports - baseline_ports
        if new_ports:
            anomalies.append({
                "type": "new_top_ports",
                "severity": "high" if len(new_ports) > 3 else "medium",
                "details": list(new_ports),
                "description": f"{len(new_ports)} new ports in top usage",
            })

        # Check for traffic volume anomalies
        baseline_avg = baseline["characteristics"]["average_flows"]
        current_avg = current["total_flows"] // 6  # 60s / 10s intervals

        threshold = {"low": 3.0, "medium": 2.0, "high": 1.5}[sensitivity]

        if current_avg > baseline_avg * threshold:
            anomalies.append({
                "type": "traffic_spike",
                "severity": "high",
                "details": {
                    "baseline": baseline_avg,
                    "current": current_avg,
                    "multiplier": round(current_avg / baseline_avg, 2),
                },
                "description": f"Traffic {round(current_avg / baseline_avg, 1)}x higher than baseline",
            })

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Anomaly detection complete: {len(anomalies)} anomalies found",
            details={
                "anomalies": anomalies,
                "anomaly_count": len(anomalies),
                "baseline": baseline_name,
                "sensitivity": sensitivity,
            },
        )

    async def _visualize_flows(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Generate flow visualization."""
        format_type = params.get("format", "ascii")  # ascii, mermaid, json

        # Get current flows
        monitor_result = await self._monitor_flows(
            connector,
            {"duration": 30, "interval": 10}
        )

        if not monitor_result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message="Failed to capture flows for visualization",
            )

        flows = monitor_result.details.get("flows", [])

        if format_type == "ascii":
            # Simple ASCII visualization
            viz = self._create_ascii_visualization(flows)
        elif format_type == "mermaid":
            # Mermaid diagram
            viz = self._create_mermaid_visualization(flows)
        elif format_type == "json":
            # JSON format for external tools
            viz = json.dumps(flows, indent=2)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown format: {format_type}",
            )

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Flow visualization generated ({format_type} format)",
            details={
                "visualization": viz,
                "format": format_type,
                "flow_count": len(flows),
            },
        )

    def _create_ascii_visualization(self, flows: list) -> str:
        """Create simple ASCII flow visualization."""
        if not flows:
            return "No flows to visualize"

        # Group flows by source -> destination
        flow_map = defaultdict(set)
        for flow in flows:
            src = f"{flow['src_ip']}:{flow['src_port']}"
            dst = f"{flow['dst_ip']}:{flow['dst_port']}"
            flow_map[src].add(dst)

        # Create ASCII diagram
        viz = "Flow Visualization:\n"
        viz += "=" * 60 + "\n\n"

        for src, dsts in sorted(flow_map.items())[:10]:  # Top 10
            viz += f"{src}\n"
            for dst in sorted(dsts)[:3]:  # Top 3 destinations per source
                viz += f"  └─> {dst}\n"
            if len(dsts) > 3:
                viz += f"  ... and {len(dsts) - 3} more\n"
            viz += "\n"

        return viz

    def _create_mermaid_visualization(self, flows: list) -> str:
        """Create Mermaid diagram of flows."""
        if not flows:
            return "graph TD\n  NoFlows[No Flows]"

        # Simplify: group by IP only
        flow_map = defaultdict(set)
        for flow in flows[:50]:  # Limit to 50 flows for clarity
            src = flow['src_ip']
            dst = flow['dst_ip']
            flow_map[src].add(dst)

        viz = "graph LR\n"
        for src, dsts in sorted(flow_map.items())[:10]:
            src_id = src.replace(".", "_")
            for dst in sorted(dsts)[:3]:
                dst_id = dst.replace(".", "_")
                viz += f"  {src_id}[{src}] --> {dst_id}[{dst}]\n"

        return viz

    async def _identify_top_talkers(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Identify top talkers (highest traffic sources/destinations)."""
        duration = params.get("duration", 60)
        top_n = params.get("top", 10)

        # Monitor flows
        monitor_result = await self._monitor_flows(
            connector,
            {"duration": duration, "interval": 10}
        )

        if not monitor_result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message="Failed to monitor traffic",
            )

        flows = monitor_result.details.get("flows", [])

        # Count flows per IP
        source_traffic = Counter()
        dest_traffic = Counter()

        for flow in flows:
            source_traffic[flow["src_ip"]] += 1
            dest_traffic[flow["dst_ip"]] += 1

        # Identify top talkers
        top_sources = source_traffic.most_common(top_n)
        top_destinations = dest_traffic.most_common(top_n)

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Top talkers identified: {len(top_sources)} sources, {len(top_destinations)} destinations",
            details={
                "top_sources": [
                    {"ip": ip, "flow_count": count}
                    for ip, count in top_sources
                ],
                "top_destinations": [
                    {"ip": ip, "flow_count": count}
                    for ip, count in top_destinations
                ],
                "analysis_duration": duration,
                "total_flows": len(flows),
            },
        )
