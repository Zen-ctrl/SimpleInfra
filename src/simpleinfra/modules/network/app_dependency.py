"""Application dependency mapping module.

Discovers and maps application dependencies:
- Service discovery
- Connection tracking
- Dependency graph generation
- Application groups
- Communication patterns
"""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING
from collections import defaultdict

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class ApplicationDependencyModule(Module):
    """Application dependency mapping and service discovery."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "discover")

        if action == "discover":
            return await self._discover_services(connector, kwargs)
        elif action == "map_dependencies":
            return await self._map_dependencies(connector, kwargs)
        elif action == "create_app_group":
            return await self._create_app_group(connector, kwargs)
        elif action == "analyze_flows":
            return await self._analyze_traffic_flows(connector, kwargs)
        elif action == "generate_graph":
            return await self._generate_dependency_graph(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown app dependency action: {action}",
            )

    async def _discover_services(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Discover running services and listening ports."""

        # Get listening ports
        listen_result = await connector.run_command("ss -tlnp")

        # Get process information
        process_result = await connector.run_command("ps aux")

        # Parse listening services
        import re
        services = []

        if listen_result.success:
            for line in listen_result.stdout.split('\n'):
                if 'LISTEN' in line:
                    # Extract port and process
                    port_match = re.search(r':(\d+)\s', line)
                    process_match = re.search(r'users:\(\("([^"]+)"', line)

                    if port_match:
                        port = port_match.group(1)
                        process_name = process_match.group(1) if process_match else "unknown"

                        # Identify service type
                        service_type = self._identify_service_type(port, process_name)

                        services.append({
                            "port": port,
                            "process": process_name,
                            "type": service_type,
                            "protocol": "tcp",
                        })

        # Get hostname for identification
        hostname_result = await connector.run_command("hostname")
        hostname = hostname_result.stdout.strip() if hostname_result.success else "unknown"

        # Save discovered services
        services_data = {
            "hostname": hostname,
            "services": services,
            "discovery_time": "$(date -Iseconds)",
        }

        await connector.run_command(
            f"echo '{json.dumps(services_data, indent=2)}' > /etc/simpleinfra-services.json",
            sudo=True,
        )

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Service discovery complete: {len(services)} services found",
            details={
                "hostname": hostname,
                "services": services,
                "service_count": len(services),
            },
        )

    def _identify_service_type(self, port: str, process: str) -> str:
        """Identify service type from port and process name."""
        # Common port mappings
        port_map = {
            "80": "http",
            "443": "https",
            "22": "ssh",
            "3306": "mysql",
            "5432": "postgresql",
            "6379": "redis",
            "27017": "mongodb",
            "8080": "http-alt",
            "8443": "https-alt",
            "9200": "elasticsearch",
            "3000": "grafana",
        }

        if port in port_map:
            return port_map[port]

        # Process name heuristics
        process_lower = process.lower()
        if "nginx" in process_lower or "apache" in process_lower:
            return "web-server"
        elif "mysql" in process_lower or "mariadb" in process_lower:
            return "database-mysql"
        elif "postgres" in process_lower:
            return "database-postgresql"
        elif "redis" in process_lower:
            return "cache-redis"
        elif "mongo" in process_lower:
            return "database-mongodb"
        elif "node" in process_lower:
            return "nodejs-app"
        elif "python" in process_lower:
            return "python-app"
        elif "java" in process_lower:
            return "java-app"
        else:
            return "unknown"

    async def _map_dependencies(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Map dependencies between services by analyzing connections."""
        duration = params.get("duration", 60)  # Monitor for 60 seconds

        # Track connections over time
        await connector.run_command(
            f"timeout {duration} tcpdump -i any -n -c 1000 'tcp' -w /tmp/traffic.pcap 2>/dev/null || true",
            sudo=True,
        )

        # Analyze active connections
        connections_result = await connector.run_command("ss -tnp")

        # Parse connections to find dependencies
        dependencies = defaultdict(list)
        import re

        if connections_result.success:
            for line in connections_result.stdout.split('\n'):
                if 'ESTAB' in line:
                    # Extract local and remote addresses
                    addr_match = re.search(r'(\d+\.\d+\.\d+\.\d+):(\d+)\s+(\d+\.\d+\.\d+\.\d+):(\d+)', line)
                    process_match = re.search(r'users:\(\("([^"]+)"', line)

                    if addr_match and process_match:
                        local_ip = addr_match.group(1)
                        local_port = addr_match.group(2)
                        remote_ip = addr_match.group(3)
                        remote_port = addr_match.group(4)
                        process = process_match.group(1)

                        # Create dependency entry
                        dep_key = f"{process}:{local_port}"
                        dependencies[dep_key].append({
                            "remote_ip": remote_ip,
                            "remote_port": remote_port,
                            "connection_type": self._identify_service_type(remote_port, ""),
                        })

        # Convert to list format
        dependency_list = []
        for source, targets in dependencies.items():
            dependency_list.append({
                "source": source,
                "targets": targets,
                "target_count": len(targets),
            })

        # Save dependency map
        dependency_data = {
            "dependencies": dependency_list,
            "mapped_at": "$(date -Iseconds)",
        }

        await connector.run_command(
            f"echo '{json.dumps(dependency_data, indent=2)}' > /etc/simpleinfra-dependencies.json",
            sudo=True,
        )

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Dependency mapping complete: {len(dependency_list)} dependencies found",
            details={
                "dependencies": dependency_list,
                "dependency_count": len(dependency_list),
            },
        )

    async def _create_app_group(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Create application group with multiple services."""
        group_name = params.get("group")
        services = params.get("services", [])
        labels = params.get("labels", [])

        if not group_name or not services:
            return ModuleResult(
                changed=False,
                success=False,
                message="group and services parameters required",
            )

        # Create application group
        app_group = {
            "name": group_name,
            "services": services,
            "labels": labels,
            "created_at": "$(date -Iseconds)",
        }

        # Save group configuration
        await connector.run_command(
            f"echo '{json.dumps(app_group, indent=2)}' > /etc/simpleinfra-appgroup-{group_name}.json",
            sudo=True,
        )

        # Apply group-level policies
        # All services in group get same base policies
        for service in services:
            port = service.get("port")
            if port:
                await connector.run_command(
                    f"iptables -A INPUT -p tcp --dport {port} -m comment --comment 'AppGroup:{group_name}' -j ACCEPT",
                    sudo=True,
                )

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Application group '{group_name}' created with {len(services)} services",
            details={
                "group": group_name,
                "services": services,
                "labels": labels,
            },
        )

    async def _analyze_traffic_flows(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Analyze traffic flows between services."""
        duration = params.get("duration", 60)
        show_top = params.get("top", 10)

        # Capture traffic statistics
        result = await connector.run_command(
            f"timeout {duration} iftop -t -s {duration} -o 40s 2>/dev/null || ss -s",
            sudo=True,
        )

        # Get connection statistics
        stats_result = await connector.run_command("ss -s")

        # Parse statistics
        stats = {}
        if stats_result.success:
            import re
            tcp_match = re.search(r'TCP:\s+(\d+)', stats_result.stdout)
            udp_match = re.search(r'UDP:\s+(\d+)', stats_result.stdout)

            stats = {
                "tcp_connections": int(tcp_match.group(1)) if tcp_match else 0,
                "udp_connections": int(udp_match.group(1)) if udp_match else 0,
            }

        # Get top connections by traffic
        conn_result = await connector.run_command("ss -tinp | head -n 20")

        flows = []
        if conn_result.success:
            import re
            for line in conn_result.stdout.split('\n'):
                if 'ESTAB' in line:
                    addr_match = re.search(r'(\d+\.\d+\.\d+\.\d+):(\d+)\s+(\d+\.\d+\.\d+\.\d+):(\d+)', line)
                    if addr_match:
                        flows.append({
                            "source": f"{addr_match.group(1)}:{addr_match.group(2)}",
                            "destination": f"{addr_match.group(3)}:{addr_match.group(4)}",
                        })

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Traffic flow analysis complete: {len(flows)} active flows",
            details={
                "statistics": stats,
                "active_flows": flows[:show_top],
                "total_flows": len(flows),
            },
        )

    async def _generate_dependency_graph(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Generate dependency graph in various formats."""
        format_type = params.get("format", "json")  # json, dot, mermaid

        # Load dependencies
        deps_result = await connector.run_command("cat /etc/simpleinfra-dependencies.json 2>/dev/null")

        if not deps_result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message="No dependency data found. Run 'map_dependencies' first.",
            )

        try:
            deps_data = json.loads(deps_result.stdout)
        except:
            return ModuleResult(
                changed=False,
                success=False,
                message="Invalid dependency data",
            )

        dependencies = deps_data.get("dependencies", [])

        # Generate graph based on format
        if format_type == "json":
            graph = {
                "nodes": [],
                "edges": [],
            }

            nodes_set = set()
            for dep in dependencies:
                source = dep["source"]
                nodes_set.add(source)

                for target in dep.get("targets", []):
                    target_id = f"{target['remote_ip']}:{target['remote_port']}"
                    nodes_set.add(target_id)

                    graph["edges"].append({
                        "from": source,
                        "to": target_id,
                        "type": target.get("connection_type", "unknown"),
                    })

            graph["nodes"] = [{"id": n} for n in nodes_set]

        elif format_type == "dot":
            # Generate GraphViz DOT format
            graph = "digraph Dependencies {\n"
            for dep in dependencies:
                source = dep["source"].replace(":", "_")
                for target in dep.get("targets", []):
                    target_id = f"{target['remote_ip']}_{target['remote_port']}"
                    graph += f'  "{source}" -> "{target_id}";\n'
            graph += "}\n"

        elif format_type == "mermaid":
            # Generate Mermaid diagram format
            graph = "graph TD\n"
            for dep in dependencies:
                source = dep["source"].replace(":", "_")
                for target in dep.get("targets", []):
                    target_id = f"{target['remote_ip']}_{target['remote_port']}"
                    graph += f"  {source} --> {target_id}\n"

        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown format: {format_type}",
            )

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Dependency graph generated in {format_type} format",
            details={
                "format": format_type,
                "graph": graph,
                "node_count": len(dependencies),
            },
        )
