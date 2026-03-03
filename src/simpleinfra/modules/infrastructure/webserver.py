"""Web server configuration module.

Provides:
- Nginx configuration and management
- Apache configuration and management
- Virtual host setup
- Reverse proxy configuration
- Load balancer configuration
- SSL/TLS integration
- Security headers and hardening
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


# Pre-configured site templates
NGINX_TEMPLATES = {
    "static-site": """server {{
    listen 80;
    listen [::]:80;
    server_name {domain};

    root {root};
    index index.html index.htm;

    location / {{
        try_files $uri $uri/ =404;
    }}

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss;
}}
""",

    "reverse-proxy": """server {{
    listen 80;
    listen [::]:80;
    server_name {domain};

    location / {{
        proxy_pass {backend};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }}
}}
""",

    "load-balancer": """upstream {upstream_name} {{
    {backend_servers}
}}

server {{
    listen 80;
    listen [::]:80;
    server_name {domain};

    location / {{
        proxy_pass http://{upstream_name};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }}
}}
""",

    "nodejs-app": """server {{
    listen 80;
    listen [::]:80;
    server_name {domain};

    location / {{
        proxy_pass http://localhost:{port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }}

    # Static files
    location /static/ {{
        alias {static_path}/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }}
}}
""",

    "wordpress": """server {{
    listen 80;
    listen [::]:80;
    server_name {domain};

    root {root};
    index index.php index.html;

    location / {{
        try_files $uri $uri/ /index.php?$args;
    }}

    location ~ \\.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php{php_version}-fpm.sock;
    }}

    location ~ /\\.ht {{
        deny all;
    }}
}}
""",
}


class WebServerModule(Module):
    """Web server configuration and management."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "install")

        if action == "install":
            return await self._install_webserver(connector, kwargs)
        elif action == "configure_site":
            return await self._configure_site(connector, kwargs)
        elif action == "enable_site":
            return await self._enable_site(connector, kwargs)
        elif action == "disable_site":
            return await self._disable_site(connector, kwargs)
        elif action == "configure_proxy":
            return await self._configure_proxy(connector, kwargs)
        elif action == "configure_load_balancer":
            return await self._configure_load_balancer(connector, kwargs)
        elif action == "enable_ssl":
            return await self._enable_ssl(connector, kwargs)
        elif action == "test_config":
            return await self._test_config(connector, kwargs)
        elif action == "reload":
            return await self._reload(connector, kwargs)
        elif action == "configure_rate_limit":
            return await self._configure_rate_limit(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown webserver action: {action}",
            )

    async def _install_webserver(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Install web server (nginx or apache)."""
        server = params.get("server", "nginx")
        version = params.get("version", "latest")

        if server == "nginx":
            # Install nginx
            install_cmd = "apt-get update && apt-get install -y nginx"
            result = await connector.run_command(install_cmd, sudo=True)

            if result.success:
                # Start and enable nginx
                await connector.run_command("systemctl start nginx", sudo=True)
                await connector.run_command("systemctl enable nginx", sudo=True)

                # Get version
                version_result = await connector.run_command("nginx -v")

                return ModuleResult(
                    changed=True,
                    success=True,
                    message="Nginx installed successfully",
                    details={
                        "server": "nginx",
                        "version": version_result.stderr.strip() if version_result.success else "unknown",
                        "status": "running",
                    },
                )
            else:
                return ModuleResult(
                    changed=False,
                    success=False,
                    message="Failed to install nginx",
                    details={"error": result.stderr},
                )

        elif server == "apache":
            # Install Apache
            install_cmd = "apt-get update && apt-get install -y apache2"
            result = await connector.run_command(install_cmd, sudo=True)

            if result.success:
                # Start and enable Apache
                await connector.run_command("systemctl start apache2", sudo=True)
                await connector.run_command("systemctl enable apache2", sudo=True)

                # Enable common modules
                await connector.run_command("a2enmod rewrite ssl headers", sudo=True)

                return ModuleResult(
                    changed=True,
                    success=True,
                    message="Apache installed successfully",
                    details={"server": "apache", "status": "running"},
                )
            else:
                return ModuleResult(
                    changed=False,
                    success=False,
                    message="Failed to install Apache",
                    details={"error": result.stderr},
                )

        return ModuleResult(
            changed=False,
            success=False,
            message=f"Unsupported web server: {server}",
        )

    async def _configure_site(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Configure a website/virtual host."""
        server = params.get("server", "nginx")
        domain = params.get("domain", "")
        template = params.get("template", "static-site")
        root = params.get("root", "/var/www/html")
        backend = params.get("backend", "http://localhost:3000")
        port = params.get("port", "3000")
        static_path = params.get("static_path", f"{root}/static")
        php_version = params.get("php_version", "8.1")

        if not domain:
            return ModuleResult(
                changed=False,
                success=False,
                message="Domain is required",
            )

        if server == "nginx":
            # Get template
            if template not in NGINX_TEMPLATES:
                return ModuleResult(
                    changed=False,
                    success=False,
                    message=f"Unknown template: {template}",
                )

            config_content = NGINX_TEMPLATES[template].format(
                domain=domain,
                root=root,
                backend=backend,
                port=port,
                static_path=static_path,
                php_version=php_version,
                upstream_name=domain.replace(".", "_"),
                backend_servers="",  # Will be filled in load balancer action
            )

            # Write config file
            config_path = f"/etc/nginx/sites-available/{domain}"
            await connector.run_command(
                f"cat > {config_path} << 'EOL'\n{config_content}\nEOL",
                sudo=True,
            )

            # Create document root if needed
            await connector.run_command(f"mkdir -p {root}", sudo=True)
            await connector.run_command(f"chown -R www-data:www-data {root}", sudo=True)

            return ModuleResult(
                changed=True,
                success=True,
                message=f"Site configured for {domain}",
                details={
                    "domain": domain,
                    "config_path": config_path,
                    "template": template,
                    "root": root,
                },
            )

        elif server == "apache":
            # Apache virtual host configuration
            if template == "static-site":
                config_content = f"""<VirtualHost *:80>
    ServerName {domain}
    DocumentRoot {root}

    <Directory {root}>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${{APACHE_LOG_DIR}}/{domain}-error.log
    CustomLog ${{APACHE_LOG_DIR}}/{domain}-access.log combined
</VirtualHost>
"""
            elif template == "reverse-proxy":
                config_content = f"""<VirtualHost *:80>
    ServerName {domain}

    ProxyPreserveHost On
    ProxyPass / {backend}/
    ProxyPassReverse / {backend}/

    ErrorLog ${{APACHE_LOG_DIR}}/{domain}-error.log
    CustomLog ${{APACHE_LOG_DIR}}/{domain}-access.log combined
</VirtualHost>
"""
            else:
                return ModuleResult(
                    changed=False,
                    success=False,
                    message=f"Template {template} not supported for Apache",
                )

            config_path = f"/etc/apache2/sites-available/{domain}.conf"
            await connector.run_command(
                f"cat > {config_path} << 'EOL'\n{config_content}\nEOL",
                sudo=True,
            )

            # Create document root
            await connector.run_command(f"mkdir -p {root}", sudo=True)
            await connector.run_command(f"chown -R www-data:www-data {root}", sudo=True)

            return ModuleResult(
                changed=True,
                success=True,
                message=f"Apache site configured for {domain}",
                details={
                    "domain": domain,
                    "config_path": config_path,
                    "template": template,
                },
            )

        return ModuleResult(
            changed=False,
            success=False,
            message=f"Unsupported server: {server}",
        )

    async def _enable_site(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Enable a configured site."""
        server = params.get("server", "nginx")
        domain = params.get("domain", "")

        if not domain:
            return ModuleResult(
                changed=False,
                success=False,
                message="Domain is required",
            )

        if server == "nginx":
            # Create symlink
            result = await connector.run_command(
                f"ln -sf /etc/nginx/sites-available/{domain} /etc/nginx/sites-enabled/{domain}",
                sudo=True,
            )

            if result.success:
                # Test config
                test_result = await connector.run_command("nginx -t", sudo=True)
                if not test_result.success:
                    # Remove symlink if test fails
                    await connector.run_command(
                        f"rm /etc/nginx/sites-enabled/{domain}",
                        sudo=True,
                    )
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
                    message=f"Site enabled: {domain}",
                    details={"domain": domain, "server": "nginx"},
                )

        elif server == "apache":
            result = await connector.run_command(f"a2ensite {domain}", sudo=True)
            if result.success:
                await connector.run_command("systemctl reload apache2", sudo=True)
                return ModuleResult(
                    changed=True,
                    success=True,
                    message=f"Apache site enabled: {domain}",
                )

        return ModuleResult(
            changed=False,
            success=False,
            message="Failed to enable site",
        )

    async def _disable_site(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Disable a site."""
        server = params.get("server", "nginx")
        domain = params.get("domain", "")

        if server == "nginx":
            result = await connector.run_command(
                f"rm -f /etc/nginx/sites-enabled/{domain}",
                sudo=True,
            )
            await connector.run_command("systemctl reload nginx", sudo=True)

        elif server == "apache":
            result = await connector.run_command(f"a2dissite {domain}", sudo=True)
            await connector.run_command("systemctl reload apache2", sudo=True)

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Site disabled: {domain}",
        )

    async def _configure_proxy(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Configure reverse proxy."""
        domain = params.get("domain", "")
        backend = params.get("backend", "")
        ssl = params.get("ssl", "false") == "true"

        # Use configure_site with reverse-proxy template
        params["template"] = "reverse-proxy"
        params["server"] = params.get("server", "nginx")

        result = await self._configure_site(connector, params)

        if result.success:
            # Enable the site
            await self._enable_site(connector, params)

        return result

    async def _configure_load_balancer(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Configure load balancer."""
        server = params.get("server", "nginx")
        domain = params.get("domain", "")
        backend_servers = params.get("backend_servers", "")
        algorithm = params.get("algorithm", "roundrobin")

        if isinstance(backend_servers, str):
            backend_servers = [s.strip() for s in backend_servers.split(",")]

        if server == "nginx":
            upstream_name = domain.replace(".", "_")

            # Build backend server list
            server_lines = []
            for backend in backend_servers:
                weight = ""
                if algorithm == "weighted":
                    weight = " weight=1"
                server_lines.append(f"    server {backend}{weight};")

            if algorithm == "ip_hash":
                server_lines.insert(0, "    ip_hash;")
            elif algorithm == "least_conn":
                server_lines.insert(0, "    least_conn;")

            backend_config = "\n".join(server_lines)

            config_content = NGINX_TEMPLATES["load-balancer"].format(
                domain=domain,
                upstream_name=upstream_name,
                backend_servers=backend_config,
            )

            config_path = f"/etc/nginx/sites-available/{domain}"
            await connector.run_command(
                f"cat > {config_path} << 'EOL'\n{config_content}\nEOL",
                sudo=True,
            )

            return ModuleResult(
                changed=True,
                success=True,
                message=f"Load balancer configured for {domain}",
                details={
                    "domain": domain,
                    "backends": backend_servers,
                    "algorithm": algorithm,
                },
            )

        return ModuleResult(
            changed=False,
            success=False,
            message=f"Load balancer not supported for {server}",
        )

    async def _enable_ssl(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Enable SSL for a site."""
        server = params.get("server", "nginx")
        domain = params.get("domain", "")
        cert_path = params.get("cert_path", f"/etc/letsencrypt/live/{domain}")

        if server == "nginx":
            ssl_config = f"""
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    ssl_certificate {cert_path}/fullchain.pem;
    ssl_certificate_key {cert_path}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
"""

            # Add SSL config and redirect
            config_path = f"/etc/nginx/sites-available/{domain}"

            # Add redirect server block
            redirect = f"""
server {{
    listen 80;
    listen [::]:80;
    server_name {domain};
    return 301 https://$server_name$request_uri;
}}
"""

            # Prepend redirect and add SSL config
            await connector.run_command(
                f"sed -i '1i {redirect}' {config_path}",
                sudo=True,
            )
            await connector.run_command(
                f"sed -i '/listen 80;/a {ssl_config}' {config_path}",
                sudo=True,
            )

            # Test and reload
            test_result = await connector.run_command("nginx -t", sudo=True)
            if test_result.success:
                await connector.run_command("systemctl reload nginx", sudo=True)
                return ModuleResult(
                    changed=True,
                    success=True,
                    message=f"SSL enabled for {domain}",
                )

        return ModuleResult(
            changed=False,
            success=False,
            message="Failed to enable SSL",
        )

    async def _test_config(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Test web server configuration."""
        server = params.get("server", "nginx")

        if server == "nginx":
            result = await connector.run_command("nginx -t", sudo=True)
        elif server == "apache":
            result = await connector.run_command("apache2ctl configtest", sudo=True)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unsupported server: {server}",
            )

        return ModuleResult(
            changed=False,
            success=result.success,
            message="Configuration test passed" if result.success else "Configuration test failed",
            details={"output": result.stderr + result.stdout},
        )

    async def _reload(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Reload web server."""
        server = params.get("server", "nginx")

        if server == "nginx":
            result = await connector.run_command("systemctl reload nginx", sudo=True)
        elif server == "apache":
            result = await connector.run_command("systemctl reload apache2", sudo=True)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unsupported server: {server}",
            )

        return ModuleResult(
            changed=True,
            success=result.success,
            message=f"{server.capitalize()} reloaded",
        )

    async def _configure_rate_limit(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Configure rate limiting."""
        server = params.get("server", "nginx")
        domain = params.get("domain", "")
        rate = params.get("rate", "10r/s")
        burst = params.get("burst", "20")

        if server == "nginx":
            # Add rate limit zone to nginx.conf
            zone_config = f"""
limit_req_zone $binary_remote_addr zone={domain}_limit:10m rate={rate};
"""

            # Add to http block
            await connector.run_command(
                f"sed -i '/http {{/a {zone_config}' /etc/nginx/nginx.conf",
                sudo=True,
            )

            # Add to site config
            rate_limit_config = f"    limit_req zone={domain}_limit burst={burst} nodelay;"
            config_path = f"/etc/nginx/sites-available/{domain}"
            await connector.run_command(
                f"sed -i '/location \\/ {{/a {rate_limit_config}' {config_path}",
                sudo=True,
            )

            return ModuleResult(
                changed=True,
                success=True,
                message=f"Rate limiting configured: {rate}",
                details={"rate": rate, "burst": burst},
            )

        return ModuleResult(
            changed=False,
            success=False,
            message=f"Rate limiting not supported for {server}",
        )
