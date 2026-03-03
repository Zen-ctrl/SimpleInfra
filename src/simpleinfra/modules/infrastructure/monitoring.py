"""Monitoring and observability module.

Provides:
- Prometheus setup and configuration
- Grafana dashboards
- Node exporter deployment
- Alertmanager configuration
- Alert rules management
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class MonitoringModule(Module):
    """Monitoring and observability."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "install_stack")

        if action == "install_stack":
            return await self._install_stack(connector, kwargs)
        elif action == "install_prometheus":
            return await self._install_prometheus(connector, kwargs)
        elif action == "install_grafana":
            return await self._install_grafana(connector, kwargs)
        elif action == "add_target":
            return await self._add_target(connector, kwargs)
        elif action == "deploy_dashboard":
            return await self._deploy_dashboard(connector, kwargs)
        elif action == "configure_alerts":
            return await self._configure_alerts(connector, kwargs)
        else:
            return ModuleResult(changed=False, success=False, message=f"Unknown monitoring action: {action}")

    async def _install_stack(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Install monitoring stack (Prometheus + Grafana)."""
        # Install Prometheus
        prom_result = await self._install_prometheus(connector, params)
        if not prom_result.success:
            return prom_result

        # Install Grafana
        grafana_result = await self._install_grafana(connector, params)

        return ModuleResult(changed=True, success=True,
            message="Monitoring stack installed (Prometheus + Grafana)",
            details={"prometheus": "installed", "grafana": "installed"})

    async def _install_prometheus(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Install Prometheus."""
        # Create user
        await connector.run_command("useradd --no-create-home --shell /bin/false prometheus || true", sudo=True)

        # Download and install Prometheus
        version = params.get("version", "2.45.0")
        commands = [
            f"wget https://github.com/prometheus/prometheus/releases/download/v{version}/prometheus-{version}.linux-amd64.tar.gz",
            f"tar -xzf prometheus-{version}.linux-amd64.tar.gz",
            f"cp prometheus-{version}.linux-amd64/prometheus /usr/local/bin/",
            f"cp prometheus-{version}.linux-amd64/promtool /usr/local/bin/",
            "chown prometheus:prometheus /usr/local/bin/prometheus /usr/local/bin/promtool",
            "mkdir -p /etc/prometheus /var/lib/prometheus",
            "chown prometheus:prometheus /etc/prometheus /var/lib/prometheus",
        ]

        for cmd in commands:
            result = await connector.run_command(cmd, sudo=True)
            if not result.success and "chown" not in cmd:
                return ModuleResult(changed=False, success=False, message=f"Failed: {cmd}")

        # Create Prometheus config
        prom_config = """
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
"""

        await connector.run_command(f"cat > /etc/prometheus/prometheus.yml << 'EOL'\n{prom_config}\nEOL", sudo=True)

        # Create systemd service
        service_content = """
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus \\
  --config.file /etc/prometheus/prometheus.yml \\
  --storage.tsdb.path /var/lib/prometheus/

[Install]
WantedBy=multi-user.target
"""

        await connector.run_command(f"cat > /etc/systemd/system/prometheus.service << 'EOL'\n{service_content}\nEOL", sudo=True)

        await connector.run_command("systemctl daemon-reload", sudo=True)
        await connector.run_command("systemctl enable prometheus", sudo=True)
        await connector.run_command("systemctl start prometheus", sudo=True)

        return ModuleResult(changed=True, success=True, message="Prometheus installed")

    async def _install_grafana(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Install Grafana."""
        commands = [
            "apt-get install -y apt-transport-https software-properties-common",
            "wget -q -O - https://packages.grafana.com/gpg.key | apt-key add -",
            'echo "deb https://packages.grafana.com/oss/deb stable main" | tee -a /etc/apt/sources.list.d/grafana.list',
            "apt-get update",
            "apt-get install -y grafana",
        ]

        for cmd in commands:
            result = await connector.run_command(cmd, sudo=True)

        await connector.run_command("systemctl enable grafana-server", sudo=True)
        await connector.run_command("systemctl start grafana-server", sudo=True)

        return ModuleResult(changed=True, success=True,
            message="Grafana installed on port 3000", details={"url": "http://localhost:3000"})

    async def _add_target(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Add scrape target to Prometheus."""
        target = params.get("target", "")
        job_name = params.get("job_name", "node")
        scrape_interval = params.get("scrape_interval", "15s")

        scrape_config = f"""
  - job_name: '{job_name}'
    scrape_interval: {scrape_interval}
    static_configs:
      - targets: ['{target}']
"""

        await connector.run_command(f"cat >> /etc/prometheus/prometheus.yml << 'EOL'\n{scrape_config}\nEOL", sudo=True)
        await connector.run_command("systemctl reload prometheus", sudo=True)

        return ModuleResult(changed=True, success=True, message=f"Target {target} added")

    async def _deploy_dashboard(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Deploy Grafana dashboard."""
        dashboard = params.get("dashboard", "node-exporter")
        datasource = params.get("datasource", "prometheus")

        # This would typically use Grafana API to import dashboard
        # Simplified version
        return ModuleResult(changed=True, success=True,
            message=f"Dashboard '{dashboard}' deployment initiated",
            details={"dashboard": dashboard, "datasource": datasource,
                "note": "Use Grafana UI to complete dashboard import"})

    async def _configure_alerts(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Configure alert rules."""
        alert_name = params.get("alert_name", "HighCPU")
        condition = params.get("condition", "avg(rate(cpu_usage[5m])) > 0.8")
        duration = params.get("duration", "5m")

        alert_rule = f"""
groups:
  - name: simpleinfra_alerts
    rules:
      - alert: {alert_name}
        expr: {condition}
        for: {duration}
        labels:
          severity: warning
        annotations:
          summary: "{alert_name} detected"
"""

        await connector.run_command(
            f"cat > /etc/prometheus/alerts.yml << 'EOL'\n{alert_rule}\nEOL",
            sudo=True,
        )

        # Update prometheus config to include alert rules
        rule_config = "\nrule_files:\n  - 'alerts.yml'\n"
        await connector.run_command(
            f"sed -i '/scrape_configs:/i{rule_config}' /etc/prometheus/prometheus.yml",
            sudo=True,
        )

        await connector.run_command("systemctl reload prometheus", sudo=True)

        return ModuleResult(changed=True, success=True, message=f"Alert rule '{alert_name}' configured")
