"""Security scanning module for SimpleInfra.

Scan for vulnerabilities, misconfigurations, and security issues.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class SecurityScannerModule(Module):
    """Comprehensive security scanning."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        scan_type = kwargs.get("scan_type", "vulnerability")

        if scan_type == "vulnerability":
            return await self._vulnerability_scan(connector, kwargs)
        elif scan_type == "ports":
            return await self._port_scan(connector, kwargs)
        elif scan_type == "ssl":
            return await self._ssl_scan(connector, kwargs)
        elif scan_type == "dependencies":
            return await self._dependency_scan(connector, kwargs)
        elif scan_type == "cis":
            return await self._cis_benchmark(connector, kwargs)
        elif scan_type == "docker":
            return await self._docker_scan(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown scan type: {scan_type}",
            )

    async def _vulnerability_scan(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Scan for vulnerabilities using Trivy."""
        target = params.get("target", "filesystem")

        # Install Trivy if not present
        install_check = await connector.run_command("which trivy")
        if not install_check.success:
            await connector.run_command(
                "wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | "
                "gpg --dearmor | sudo tee /usr/share/keyrings/trivy.gpg > /dev/null && "
                'echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] '
                'https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | '
                "sudo tee /etc/apt/sources.list.d/trivy.list && "
                "sudo apt-get update && sudo apt-get install -y trivy",
                sudo=True,
            )

        # Run scan
        if target == "filesystem":
            result = await connector.run_command("trivy fs --severity HIGH,CRITICAL /")
        elif target == "docker":
            image = params.get("image", "")
            result = await connector.run_command(f"trivy image {image}")
        else:
            result = await connector.run_command(f"trivy fs {target}")

        # Parse results
        vulnerabilities_found = "Total: 0" not in result.stdout

        return ModuleResult(
            changed=False,
            success=not vulnerabilities_found,
            message=(
                "Security scan complete - vulnerabilities found!"
                if vulnerabilities_found
                else "Security scan complete - no critical vulnerabilities"
            ),
            details={"stdout": result.stdout, "has_vulnerabilities": vulnerabilities_found},
        )

    async def _port_scan(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Scan open ports."""
        # Install nmap
        await connector.run_command("apt-get install -y nmap", sudo=True)

        # Scan localhost
        result = await connector.run_command("nmap -p- localhost")

        # Parse open ports
        import re
        open_ports = re.findall(r"(\d+)/tcp\s+open", result.stdout)

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Found {len(open_ports)} open ports",
            details={"open_ports": open_ports, "scan_output": result.stdout},
        )

    async def _ssl_scan(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Scan SSL/TLS configuration."""
        domain = params.get("domain", "localhost")

        # Install testssl.sh
        result = await connector.run_command(
            "if [ ! -d /opt/testssl.sh ]; then "
            "git clone --depth 1 https://github.com/drwetter/testssl.sh.git /opt/testssl.sh; "
            "fi"
        )

        # Run SSL test
        result = await connector.run_command(f"/opt/testssl.sh/testssl.sh {domain}")

        # Check for issues
        has_issues = "NOT ok" in result.stdout or "WARN" in result.stdout

        return ModuleResult(
            changed=False,
            success=not has_issues,
            message="SSL/TLS scan complete",
            details={"stdout": result.stdout, "has_issues": has_issues},
        )

    async def _dependency_scan(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Scan dependencies for known vulnerabilities."""
        project_path = params.get("path", ".")
        lang = params.get("language", "auto")

        if lang == "python" or lang == "auto":
            # Check for Python
            result = await connector.run_command(
                f"cd {project_path} && "
                "pip install safety && "
                "safety check --json"
            )

            if result.success:
                import json
                try:
                    safety_result = json.loads(result.stdout)
                    has_vulns = len(safety_result) > 0
                    return ModuleResult(
                        changed=False,
                        success=not has_vulns,
                        message=f"Found {len(safety_result)} vulnerable dependencies",
                        details={"vulnerabilities": safety_result},
                    )
                except json.JSONDecodeError:
                    pass

        if lang == "javascript" or lang == "auto":
            # npm audit
            result = await connector.run_command(
                f"cd {project_path} && npm audit --json"
            )

        return ModuleResult(
            changed=False,
            success=True,
            message="Dependency scan complete",
            details={"stdout": result.stdout if result.success else ""},
        )

    async def _cis_benchmark(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Run CIS benchmark security checks."""
        # Install Lynis (CIS benchmark tool)
        install_result = await connector.run_command(
            "apt-get install -y lynis", sudo=True
        )

        # Run audit
        result = await connector.run_command("lynis audit system --quick", sudo=True)

        # Parse hardening index
        import re
        hardening_match = re.search(r"Hardening index : \[(\d+)\]", result.stdout)
        hardening_score = int(hardening_match.group(1)) if hardening_match else 0

        is_secure = hardening_score >= 70

        return ModuleResult(
            changed=False,
            success=is_secure,
            message=f"CIS Benchmark score: {hardening_score}/100",
            details={
                "score": hardening_score,
                "passed": is_secure,
                "stdout": result.stdout,
            },
        )

    async def _docker_scan(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Scan Docker containers and images."""
        image = params.get("image")

        if image:
            # Scan specific image
            result = await connector.run_command(f"trivy image {image}")
        else:
            # Scan all running containers
            result = await connector.run_command(
                "docker ps -q | xargs -I {} docker inspect --format='{{.Config.Image}}' {} | "
                "xargs -I {} trivy image {}"
            )

        vulnerabilities = "Total: 0" not in result.stdout

        return ModuleResult(
            changed=False,
            success=not vulnerabilities,
            message="Docker security scan complete",
            details={"has_vulnerabilities": vulnerabilities, "stdout": result.stdout},
        )


# DSL Syntax:
# task "Security Audit" on servers:
#     security scan type="vulnerability"
#     security scan type="ports"
#     security scan type="ssl" domain="example.com"
#     security scan type="cis"
#
#     check security score >= 70
