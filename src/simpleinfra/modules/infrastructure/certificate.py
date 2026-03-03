"""SSL/TLS certificate management module.

Provides:
- Let's Encrypt certificate automation
- Self-signed certificate generation
- Certificate renewal and deployment
- Multi-domain and wildcard support
- Automatic renewal setup
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class CertificateModule(Module):
    """SSL/TLS certificate management."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "obtain")

        if action == "obtain":
            return await self._obtain_certificate(connector, kwargs)
        elif action == "renew":
            return await self._renew_certificate(connector, kwargs)
        elif action == "auto_renew":
            return await self._setup_auto_renew(connector, kwargs)
        elif action == "generate_self_signed":
            return await self._generate_self_signed(connector, kwargs)
        elif action == "deploy":
            return await self._deploy_certificate(connector, kwargs)
        elif action == "verify":
            return await self._verify_certificate(connector, kwargs)
        elif action == "list":
            return await self._list_certificates(connector, kwargs)
        elif action == "revoke":
            return await self._revoke_certificate(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown certificate action: {action}",
            )

    async def _obtain_certificate(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Obtain SSL certificate from Let's Encrypt."""
        provider = params.get("provider", "letsencrypt")
        domains = params.get("domains", params.get("domain", ""))
        email = params.get("email", "")
        webroot = params.get("webroot", "/var/www/html")
        staging = params.get("staging", "false") == "true"

        if isinstance(domains, str):
            domains = [d.strip() for d in domains.split(",")]

        if not domains or not email:
            return ModuleResult(
                changed=False,
                success=False,
                message="Both 'domains' and 'email' are required",
            )

        if provider == "letsencrypt":
            # Install certbot if not present
            install_check = await connector.run_command("which certbot")
            if not install_check.success:
                install_result = await connector.run_command(
                    "apt-get update && apt-get install -y certbot python3-certbot-nginx",
                    sudo=True,
                )
                if not install_result.success:
                    return ModuleResult(
                        changed=False,
                        success=False,
                        message="Failed to install certbot",
                        details={"error": install_result.stderr},
                    )

            # Build certbot command
            domain_args = " ".join([f"-d {d}" for d in domains])
            staging_flag = "--staging" if staging else ""

            cmd = (
                f"certbot certonly --webroot -w {webroot} "
                f"{domain_args} --email {email} --agree-tos --non-interactive "
                f"{staging_flag}"
            )

            result = await connector.run_command(cmd, sudo=True)

            if result.success:
                cert_path = f"/etc/letsencrypt/live/{domains[0]}"
                return ModuleResult(
                    changed=True,
                    success=True,
                    message=f"Certificate obtained for {', '.join(domains)}",
                    details={
                        "domains": domains,
                        "provider": provider,
                        "cert_path": cert_path,
                        "fullchain": f"{cert_path}/fullchain.pem",
                        "privkey": f"{cert_path}/privkey.pem",
                    },
                )
            else:
                return ModuleResult(
                    changed=False,
                    success=False,
                    message="Failed to obtain certificate",
                    details={"error": result.stderr},
                )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unsupported provider: {provider}",
            )

    async def _renew_certificate(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Renew existing certificates."""
        domain = params.get("domain")
        force = params.get("force", "false") == "true"

        force_flag = "--force-renewal" if force else ""
        domain_arg = f"--cert-name {domain}" if domain else ""

        cmd = f"certbot renew {domain_arg} {force_flag}"
        result = await connector.run_command(cmd, sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Certificate renewed{' for ' + domain if domain else ''}",
                details={"output": result.stdout},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Certificate renewal failed",
                details={"error": result.stderr},
            )

    async def _setup_auto_renew(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Setup automatic certificate renewal."""
        check_interval = params.get("check_interval", "daily")
        reload_service = params.get("reload_service", "nginx")

        # Create systemd timer for auto-renewal
        timer_content = f"""[Unit]
Description=Certbot Renewal Timer

[Timer]
OnCalendar={check_interval}
RandomizedDelaySec=3600

[Install]
WantedBy=timers.target
"""

        service_content = f"""[Unit]
Description=Certbot Renewal Service

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet
ExecStartPost=/bin/systemctl reload {reload_service}
"""

        # Write timer file
        await connector.run_command(
            f"echo '{timer_content}' > /etc/systemd/system/certbot-renew.timer",
            sudo=True,
        )

        # Write service file
        await connector.run_command(
            f"echo '{service_content}' > /etc/systemd/system/certbot-renew.service",
            sudo=True,
        )

        # Enable and start timer
        await connector.run_command("systemctl daemon-reload", sudo=True)
        await connector.run_command("systemctl enable certbot-renew.timer", sudo=True)
        result = await connector.run_command("systemctl start certbot-renew.timer", sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Auto-renewal configured ({check_interval})",
                details={
                    "check_interval": check_interval,
                    "reload_service": reload_service,
                    "timer": "/etc/systemd/system/certbot-renew.timer",
                },
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Failed to setup auto-renewal",
                details={"error": result.stderr},
            )

    async def _generate_self_signed(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Generate self-signed certificate."""
        domain = params.get("domain", "localhost")
        days = params.get("days", "365")
        key_size = params.get("key_size", "2048")
        output_dir = params.get("output_dir", "/etc/ssl/private")

        cert_file = f"{output_dir}/{domain}.crt"
        key_file = f"{output_dir}/{domain}.key"

        # Create output directory
        await connector.run_command(f"mkdir -p {output_dir}", sudo=True)

        # Generate self-signed certificate
        cmd = (
            f"openssl req -x509 -nodes -days {days} -newkey rsa:{key_size} "
            f"-keyout {key_file} -out {cert_file} "
            f"-subj '/CN={domain}/O=SimpleInfra/C=US'"
        )

        result = await connector.run_command(cmd, sudo=True)

        if result.success:
            # Set proper permissions
            await connector.run_command(f"chmod 600 {key_file}", sudo=True)
            await connector.run_command(f"chmod 644 {cert_file}", sudo=True)

            return ModuleResult(
                changed=True,
                success=True,
                message=f"Self-signed certificate generated for {domain}",
                details={
                    "domain": domain,
                    "cert_file": cert_file,
                    "key_file": key_file,
                    "days": days,
                    "key_size": key_size,
                },
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Failed to generate self-signed certificate",
                details={"error": result.stderr},
            )

    async def _deploy_certificate(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Deploy certificate to a service."""
        service = params.get("service", "nginx")
        domain = params.get("domain", "")
        cert_path = params.get("cert_path", f"/etc/letsencrypt/live/{domain}")
        config_path = params.get("config_path", "")

        if not domain:
            return ModuleResult(
                changed=False,
                success=False,
                message="Domain is required",
            )

        if service == "nginx":
            # Generate Nginx SSL configuration
            ssl_config = f"""
    ssl_certificate {cert_path}/fullchain.pem;
    ssl_certificate_key {cert_path}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
"""
            if config_path:
                # Append SSL config to existing config
                await connector.run_command(
                    f"echo '{ssl_config}' >> {config_path}",
                    sudo=True,
                )

                # Test nginx config
                test_result = await connector.run_command("nginx -t", sudo=True)
                if not test_result.success:
                    return ModuleResult(
                        changed=False,
                        success=False,
                        message="Nginx configuration test failed",
                        details={"error": test_result.stderr},
                    )

                # Reload nginx
                await connector.run_command("systemctl reload nginx", sudo=True)

            return ModuleResult(
                changed=True,
                success=True,
                message=f"Certificate deployed for {service}",
                details={
                    "service": service,
                    "domain": domain,
                    "cert_path": cert_path,
                },
            )

        return ModuleResult(
            changed=False,
            success=False,
            message=f"Unsupported service: {service}",
        )

    async def _verify_certificate(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Verify certificate validity."""
        domain = params.get("domain", "")
        cert_file = params.get("cert_file", f"/etc/letsencrypt/live/{domain}/cert.pem")

        # Check certificate expiry
        cmd = f"openssl x509 -in {cert_file} -noout -enddate"
        result = await connector.run_command(cmd, sudo=True)

        if result.success:
            # Check if certificate is valid
            check_cmd = f"openssl x509 -in {cert_file} -noout -checkend 2592000"  # 30 days
            check_result = await connector.run_command(check_cmd, sudo=True)

            expires_soon = not check_result.success

            # Get certificate details
            subject_cmd = f"openssl x509 -in {cert_file} -noout -subject"
            subject_result = await connector.run_command(subject_cmd, sudo=True)

            return ModuleResult(
                changed=False,
                success=True,
                message=f"Certificate verified for {domain}",
                details={
                    "domain": domain,
                    "expiry": result.stdout.strip(),
                    "expires_soon": expires_soon,
                    "subject": subject_result.stdout.strip() if subject_result.success else "",
                },
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Failed to verify certificate",
                details={"error": result.stderr},
            )

    async def _list_certificates(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """List all certificates."""
        result = await connector.run_command("certbot certificates", sudo=True)

        if result.success:
            return ModuleResult(
                changed=False,
                success=True,
                message="Certificates listed",
                details={"certificates": result.stdout},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Failed to list certificates",
                details={"error": result.stderr},
            )

    async def _revoke_certificate(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Revoke a certificate."""
        domain = params.get("domain", "")
        reason = params.get("reason", "unspecified")

        if not domain:
            return ModuleResult(
                changed=False,
                success=False,
                message="Domain is required",
            )

        cmd = f"certbot revoke --cert-name {domain} --reason {reason}"
        result = await connector.run_command(cmd, sudo=True)

        if result.success:
            # Delete certificate files
            await connector.run_command(f"certbot delete --cert-name {domain}", sudo=True)

            return ModuleResult(
                changed=True,
                success=True,
                message=f"Certificate revoked for {domain}",
                details={"domain": domain, "reason": reason},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Failed to revoke certificate",
                details={"error": result.stderr},
            )
