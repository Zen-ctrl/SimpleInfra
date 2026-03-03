"""Network agent deployment module for SimpleInfra.

Deploys lightweight, temporary agents for network monitoring and segmentation.
Agents are:
- Deployed via SSH (agentless deployment)
- Lightweight (single Python script or shell script)
- Temporary (can be easily removed)
- Autonomous (report back to coordinator)

Use cases:
- Continuous network monitoring
- Distributed traffic analysis
- Network policy enforcement
- Automated segmentation adjustments
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING
import json

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


# Lightweight network monitoring agent (Python)
NETWORK_AGENT_SCRIPT = '''#!/usr/bin/env python3
"""
SimpleInfra Network Monitoring Agent
Lightweight agent for network segmentation monitoring
"""
import json
import socket
import subprocess
import time
import sys
from datetime import datetime

CONFIG_FILE = "/tmp/simpleinfra_agent_config.json"
LOG_FILE = "/tmp/simpleinfra_agent.log"

def load_config():
    """Load agent configuration."""
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "interval": 60,
            "coordinator": None,
            "zone": "default",
            "actions": ["monitor_connections", "check_firewall"]
        }

def log(message):
    """Log message to file."""
    timestamp = datetime.now().isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} - {message}\\n")
    print(f"[{timestamp}] {message}")

def get_active_connections():
    """Get active network connections."""
    try:
        result = subprocess.run(
            ["ss", "-tunap"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout
    except Exception as e:
        log(f"Error getting connections: {e}")
        return ""

def check_firewall_rules():
    """Check current firewall rules."""
    try:
        # Try iptables
        result = subprocess.run(
            ["iptables", "-L", "-n", "-v"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout

        # Try ufw
        result = subprocess.run(
            ["ufw", "status", "verbose"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout
    except Exception as e:
        log(f"Error checking firewall: {e}")
        return ""

def monitor_network():
    """Main monitoring loop."""
    config = load_config()
    log(f"Agent started in zone: {config['zone']}")
    log(f"Monitoring interval: {config['interval']}s")

    while True:
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "hostname": socket.gethostname(),
                "zone": config["zone"],
                "data": {}
            }

            if "monitor_connections" in config["actions"]:
                report["data"]["connections"] = get_active_connections()

            if "check_firewall" in config["actions"]:
                report["data"]["firewall"] = check_firewall_rules()

            # Log report
            log(f"Report: {len(report['data'])} metrics collected")

            # Send to coordinator if configured
            if config.get("coordinator"):
                send_report(config["coordinator"], report)

            time.sleep(config["interval"])

        except KeyboardInterrupt:
            log("Agent stopped by user")
            break
        except Exception as e:
            log(f"Error in monitoring loop: {e}")
            time.sleep(config["interval"])

def send_report(coordinator, report):
    """Send report to coordinator."""
    try:
        # Simple HTTP POST (requires requests library)
        # For production, could use socket-based communication
        log(f"Would send report to {coordinator}")
    except Exception as e:
        log(f"Error sending report: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "daemon":
        monitor_network()
    else:
        # Single run
        config = load_config()
        log("Agent: Single run mode")
        if "monitor_connections" in config["actions"]:
            print(get_active_connections())
        if "check_firewall" in config["actions"]:
            print(check_firewall_rules())
'''


class NetworkAgentModule(Module):
    """Deploy and manage network monitoring agents."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "deploy")

        if action == "deploy":
            return await self._deploy_agent(connector, kwargs)
        elif action == "remove":
            return await self._remove_agent(connector, kwargs)
        elif action == "status":
            return await self._check_agent_status(connector, kwargs)
        elif action == "configure":
            return await self._configure_agent(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown agent action: {action}",
            )

    async def _deploy_agent(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Deploy network monitoring agent to remote host.

        The agent is deployed via SSH (agentless), but runs autonomously
        to provide continuous monitoring capabilities.
        """
        zone = params.get("zone", "default")
        interval = params.get("interval", 60)
        coordinator = params.get("coordinator")
        actions = params.get("actions", ["monitor_connections", "check_firewall"])
        mode = params.get("mode", "daemon")  # daemon or oneshot

        agent_path = "/usr/local/bin/simpleinfra-agent"
        config_path = "/tmp/simpleinfra_agent_config.json"

        # Create agent configuration
        config = {
            "zone": zone,
            "interval": interval,
            "coordinator": coordinator,
            "actions": actions,
        }

        # Write agent script to remote host
        write_agent = f'''cat > {agent_path} << 'AGENTEOF'
{NETWORK_AGENT_SCRIPT}
AGENTEOF
chmod +x {agent_path}
'''

        result = await connector.run_command(write_agent, sudo=True)
        if not result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message="Failed to deploy agent script",
                details={"error": result.stderr},
            )

        # Write configuration
        config_json = json.dumps(config, indent=2)
        write_config = f'''cat > {config_path} << 'CONFIGEOF'
{config_json}
CONFIGEOF
'''

        result = await connector.run_command(write_config, sudo=True)
        if not result.success:
            return ModuleResult(
                changed=True,
                success=False,
                message="Agent deployed but configuration failed",
                details={"error": result.stderr},
            )

        # Start agent if daemon mode
        if mode == "daemon":
            # Create systemd service
            service_content = f'''[Unit]
Description=SimpleInfra Network Monitoring Agent
After=network.target

[Service]
Type=simple
ExecStart={agent_path} daemon
Restart=on-failure
RestartSec=10
StandardOutput=append:/tmp/simpleinfra_agent.log
StandardError=append:/tmp/simpleinfra_agent.log

[Install]
WantedBy=multi-user.target
'''

            write_service = f'''cat > /etc/systemd/system/simpleinfra-agent.service << 'SERVICEEOF'
{service_content}
SERVICEEOF
systemctl daemon-reload
systemctl enable simpleinfra-agent
systemctl start simpleinfra-agent
'''

            result = await connector.run_command(write_service, sudo=True)
            if not result.success:
                return ModuleResult(
                    changed=True,
                    success=False,
                    message="Agent deployed but service start failed",
                    details={"error": result.stderr},
                )

            return ModuleResult(
                changed=True,
                success=True,
                message=f"Network agent deployed and started in zone '{zone}'",
                details={
                    "zone": zone,
                    "mode": "daemon",
                    "interval": interval,
                    "actions": actions,
                    "agent_path": agent_path,
                },
            )

        else:
            # One-shot mode - just deploy, don't start
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Network agent deployed in oneshot mode for zone '{zone}'",
                details={
                    "zone": zone,
                    "mode": "oneshot",
                    "agent_path": agent_path,
                    "usage": f"Run with: {agent_path}",
                },
            )

    async def _remove_agent(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Remove deployed agent."""
        # Stop service
        await connector.run_command("systemctl stop simpleinfra-agent", sudo=True)
        await connector.run_command("systemctl disable simpleinfra-agent", sudo=True)

        # Remove files
        commands = [
            "rm -f /usr/local/bin/simpleinfra-agent",
            "rm -f /tmp/simpleinfra_agent_config.json",
            "rm -f /tmp/simpleinfra_agent.log",
            "rm -f /etc/systemd/system/simpleinfra-agent.service",
            "systemctl daemon-reload",
        ]

        for cmd in commands:
            await connector.run_command(cmd, sudo=True)

        return ModuleResult(
            changed=True,
            success=True,
            message="Network agent removed",
        )

    async def _check_agent_status(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Check if agent is running."""
        result = await connector.run_command("systemctl status simpleinfra-agent", sudo=True)

        is_running = "active (running)" in result.stdout
        is_enabled = "enabled" in result.stdout

        # Get agent log tail
        log_result = await connector.run_command("tail -20 /tmp/simpleinfra_agent.log")

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Agent is {'running' if is_running else 'not running'}",
            details={
                "running": is_running,
                "enabled": is_enabled,
                "status": result.stdout,
                "recent_logs": log_result.stdout if log_result.success else "",
            },
        )

    async def _configure_agent(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Update agent configuration."""
        config_path = "/tmp/simpleinfra_agent_config.json"

        # Read current config
        result = await connector.run_command(f"cat {config_path}")
        if not result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message="Agent not deployed or config file missing",
            )

        try:
            current_config = json.loads(result.stdout)
        except json.JSONDecodeError:
            current_config = {}

        # Update with new params
        if "interval" in params:
            current_config["interval"] = params["interval"]
        if "coordinator" in params:
            current_config["coordinator"] = params["coordinator"]
        if "actions" in params:
            current_config["actions"] = params["actions"]
        if "zone" in params:
            current_config["zone"] = params["zone"]

        # Write updated config
        config_json = json.dumps(current_config, indent=2)
        write_config = f'''cat > {config_path} << 'CONFIGEOF'
{config_json}
CONFIGEOF
'''

        result = await connector.run_command(write_config, sudo=True)
        if not result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message="Failed to update configuration",
            )

        # Restart agent to pick up new config
        await connector.run_command("systemctl restart simpleinfra-agent", sudo=True)

        return ModuleResult(
            changed=True,
            success=True,
            message="Agent configuration updated and restarted",
            details={"config": current_config},
        )
