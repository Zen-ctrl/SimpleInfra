# Advanced SimpleInfra Usage Examples

## 1. Secure Production Deployment with Vault

```simpleinfra
# secrets.si - Production deployment with encrypted secrets

# Load secrets from HashiCorp Vault
secret db_password from vault "database/prod/password"
secret api_key from vault "app/prod/api_key"
secret ssl_cert from vault "pki/ssl/cert"

# Variables
set app_name "myapp"
set app_version "2.1.0"
set deploy_path "/opt/{app_name}"

# Servers
server web1:
    host "10.0.1.10"
    user "deploy"
    key "~/.ssh/deploy_key"

server web2:
    host "10.0.1.11"
    user "deploy"
    key "~/.ssh/deploy_key"

server db:
    host "10.0.2.10"
    user "postgres"
    password secret db_password

group webservers:
    server web1
    server web2

# Deployment task with audit logging
task "Deploy Production" on webservers:
    # Pull latest code
    git pull at "{deploy_path}"
    git checkout "v{app_version}" at "{deploy_path}"

    # Update dependencies
    run "cd {deploy_path} && npm ci --production"

    # Template config with secrets
    template "config/app.conf.tmpl" to "{deploy_path}/config/app.conf"

    # Restart application
    restart service "{app_name}"

    # Health check
    wait for url "http://localhost:3000/health"
    check url "http://localhost:3000/health" returns 200

task "Setup Database" on db:
    install postgresql-14

    # Use secret for database password
    run "psql -c \"ALTER USER postgres PASSWORD '{db_password}';\""

    # Create application database
    run "psql -c 'CREATE DATABASE {app_name};'"
```

## 2. Docker-Based Microservices

```simpleinfra
# microservices.si - Deploy containerized microservices

set registry "docker.io/mycompany"
set version "1.5.0"

# Docker containers
docker "api":
    image "{registry}/api:{version}"
    ports:
        3000: 3000
    env:
        NODE_ENV: "production"
        DB_HOST: "postgres"
    volumes:
        "/opt/api/logs": "/app/logs"

docker "frontend":
    image "{registry}/frontend:{version}"
    ports:
        80: 80
        443: 443
    env:
        API_URL: "http://api:3000"

docker "postgres":
    image "postgres:14"
    ports:
        5432: 5432
    env:
        POSTGRES_PASSWORD: secret db_password
    volumes:
        "/opt/postgres/data": "/var/lib/postgresql/data"

docker "redis":
    image "redis:7-alpine"
    ports:
        6379: 6379

task "Deploy Stack" on local:
    # Pull images
    docker pull "{registry}/api:{version}"
    docker pull "{registry}/frontend:{version}"
    docker pull "postgres:14"
    docker pull "redis:7-alpine"

    # Start services
    docker run "postgres"
    docker run "redis"
    wait for port 5432
    wait for port 6379

    docker run "api"
    wait for url "http://localhost:3000/health"

    docker run "frontend"
    wait for port 80

    # Verify stack
    check url "http://localhost/health" returns 200
```

## 3. Programmatic Python API Usage

```python
# deploy.py - Programmatic infrastructure automation

import asyncio
from simpleinfra.api.client import SimpleInfraClient
from simpleinfra.variables.vault import LocalEncryptedVault

async def deploy_application():
    """Deploy application programmatically."""

    # Initialize client
    client = SimpleInfraClient()

    # Load secrets from vault
    vault = LocalEncryptedVault(
        vault_file=Path(".vault/secrets.enc"),
        password="my-vault-password"
    )
    db_password = await vault.get_secret("db_password")

    # Define infrastructure
    client.add_server(
        name="web",
        host="192.168.1.10",
        user="deploy",
        key="~/.ssh/id_rsa"
    )

    client.set_variable("app_name", "myapp")
    client.set_variable("db_password", db_password)

    # Build deployment task
    (client.create_task("deploy", target="web")
        .install("nginx", "python3", "python3-pip")
        .run("systemctl enable nginx")
        .copy("nginx.conf", "/etc/nginx/nginx.conf")
        .run("git clone https://github.com/me/app.git /opt/app")
        .run("cd /opt/app && pip3 install -r requirements.txt")
        .run("systemctl restart myapp")
        .build())

    # Execute
    result = await client.execute_task("deploy")

    if result["success"]:
        print("✅ Deployment successful!")
    else:
        print("❌ Deployment failed!")
        print(result)

    return result

# Run deployment
asyncio.run(deploy_application())
```

## 4. CI/CD Integration

```yaml
# .github/workflows/deploy.yml - GitHub Actions integration

name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install SimpleInfra
        run: pip install simpleinfra

      - name: Validate infrastructure
        run: si validate deploy.si

      - name: Deploy to staging
        env:
          VAULT_TOKEN: ${{ secrets.VAULT_TOKEN }}
          SSH_KEY: ${{ secrets.SSH_DEPLOY_KEY }}
        run: |
          echo "$SSH_KEY" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          si run deploy.si --task "Deploy Staging"

      - name: Run health checks
        run: si run deploy.si --task "Verify Deployment"

      - name: Deploy to production
        if: github.ref == 'refs/heads/main'
        run: si run deploy.si --task "Deploy Production"
```

## 5. REST API Server Usage

```bash
# Start SimpleInfra API server
python -m simpleinfra.api.server

# Or with custom host/port
python -c "from simpleinfra.api.server import run_server; run_server('0.0.0.0', 8000)"
```

```bash
# Execute task via API
curl -X POST http://localhost:8000/tasks/execute \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "deploy.si",
    "task_name": "Deploy Production"
  }'

# Validate configuration
curl -X POST http://localhost:8000/tasks/validate?file_path=deploy.si

# Check task status
curl http://localhost:8000/tasks/abc123/status
```

## 6. Multi-Environment Management

```simpleinfra
# infrastructure.si - Manage multiple environments

# Development environment
inventory "dev" from file "inventory/dev.ini"

# Staging environment
inventory "staging" from file "inventory/staging.ini"

# Production environment
inventory "production" from file "inventory/prod.ini"

# Common setup for all environments
task "Common Setup" on all:
    install curl
    install git
    install htop

    create user "deploy" with home "/home/deploy"
    copy "deploy_key.pub" to "/home/deploy/.ssh/authorized_keys"

# Environment-specific deployments
task "Deploy Dev" on inventory("dev"):
    set env "development"
    git clone "https://github.com/me/app.git" to "/opt/app"
    git checkout "develop" at "/opt/app"

    run "cd /opt/app && npm install"
    run "NODE_ENV=development npm start"

task "Deploy Production" on inventory("production"):
    set env "production"
    git clone "https://github.com/me/app.git" to "/opt/app"
    git checkout "main" at "/opt/app"

    run "cd /opt/app && npm ci --production"
    run "NODE_ENV=production pm2 start app.js"

    # Production health checks
    wait for url "http://localhost:3000/health"
    check url "http://localhost:3000/health" returns 200
    check url "http://localhost:3000/metrics" returns 200
```

## 7. Monitoring & Alerting Setup

```simpleinfra
# monitoring.si - Setup monitoring stack

server monitor:
    host "10.0.3.10"
    user "root"

task "Setup Prometheus" on monitor:
    install prometheus

    template "prometheus.yml.tmpl" to "/etc/prometheus/prometheus.yml"

    start service prometheus
    enable service prometheus

    ensure port 9090 is open

task "Setup Grafana" on monitor:
    install grafana

    copy "grafana/dashboards/" to "/var/lib/grafana/dashboards/"

    start service grafana-server
    enable service grafana-server

    ensure port 3000 is open

    # Configure data source
    run "grafana-cli admin reset-admin-password {admin_password}"
```

## 8. Disaster Recovery

```simpleinfra
# backup.si - Automated backups

set backup_bucket "s3://myapp-backups"
set retention_days 30

task "Backup Database" on db:
    run "pg_dump myapp > /tmp/myapp_backup_{date}.sql"

    run "aws s3 cp /tmp/myapp_backup_{date}.sql {backup_bucket}/db/"

    run "rm /tmp/myapp_backup_{date}.sql"

    # Cleanup old backups
    run "aws s3 ls {backup_bucket}/db/ | awk '{print $4}' | head -n -{retention_days} | xargs -I {} aws s3 rm {backup_bucket}/db/{}"

task "Backup Files" on webservers:
    run "tar -czf /tmp/app_files_{date}.tar.gz /opt/app"

    run "aws s3 cp /tmp/app_files_{date}.tar.gz {backup_bucket}/files/"

    run "rm /tmp/app_files_{date}.tar.gz"
```

---

These examples demonstrate SimpleInfra's power for production infrastructure management while maintaining simplicity!
