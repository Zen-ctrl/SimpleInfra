# SimpleInfra - Infrastructure as Code Framework

**Infrastructure as Code, simplified.**

SimpleInfra is a comprehensive Infrastructure as Code (IaC) framework built in Python. It uses a custom DSL that reads almost like English, making infrastructure automation accessible to everyone—from beginners to advanced users.

## Key Features

- **Beginner-Friendly DSL** - Reads like natural language, minimal syntax
- **Multi-Domain Support** - Infrastructure, networking, security, and IoT automation
- **Agentless Architecture** - No daemons or agents required on target servers
- **Multiple Targets** - Local machine, SSH servers, Docker containers, Cloud APIs
- **18+ Built-in Modules** - Infrastructure, network security, and IoT modules
- **Cross-Platform** - Works on Windows, Linux, and macOS
- **Async Execution** - Fast parallel execution across multiple servers
- **Pretty Output** - Rich terminal output with colors and formatting

## Installation

```bash
# Basic installation
pip install simpleinfra

# With all optional dependencies
pip install simpleinfra[all]

# Development installation
git clone <repo>
cd simpleinfra
pip install -e .
```

## Quick Start

### 1. Create a `.si` file

```simpleinfra
# hello.si

task "Hello World" on local:
    run "echo Hello from SimpleInfra!"
    run "echo Current date: $(date)"
```

### 2. Run it

```bash
si run hello.si
```

## DSL Syntax

### Variables

```simpleinfra
set app_name "myapp"
set app_port 8080
```

Use variables with `{variable_name}`:

```simpleinfra
run "echo App: {app_name} on port {app_port}"
```

### Secrets

```simpleinfra
secret db_password from env "DB_PASSWORD"
secret api_key from file ".secrets/api.key"
```

### Servers

```simpleinfra
server web:
    host "192.168.1.10"
    user "root"
    key "~/.ssh/id_rsa"
```

### Groups

```simpleinfra
group webservers:
    server web1
    server web2
```

### Tasks

```simpleinfra
task "Setup Web Server" on web:
    install nginx
    install python3

    copy "nginx.conf" to "/etc/nginx/nginx.conf"

    start service nginx
    enable service nginx

    ensure port 80 is open

    run "echo Setup complete!"
```

### Control Flow

**If/Unless:**

```simpleinfra
if os is "ubuntu":
    run "ufw allow 80"

if os is "centos":
    run "firewall-cmd --add-port=80/tcp"
```

**For loops:**

```simpleinfra
set ports [80, 443, 8080]

for port in ports:
    ensure port {port} is open
```

### Available Modules

**Infrastructure Modules (9 modules):**
- **Certificate** - SSL/TLS certificates, Let's Encrypt automation
- **WebServer** - Nginx, Apache configuration and deployment
- **Database** - PostgreSQL, MySQL, MongoDB management
- **Backup** - Automated backups, S3 sync, restoration
- **Container** - Docker, Docker Compose orchestration
- **CI/CD** - Git operations, builds, deployments, rollbacks
- **LoadBalancer** - HAProxy, Keepalived configuration
- **Monitoring** - Prometheus, Grafana setup
- **Config** - Template management, secret rotation

**Network Security Modules (8 modules):**
- **Firewall** - iptables, firewalld, ufw management
- **VLAN** - VLAN creation, trunk port configuration
- **Zone** - Network zones, isolation policies
- **MicroSegmentation** - Host-based network segmentation
- **PolicyEngine** - Illumio-style policy templates (PCI-DSS, HIPAA, NIST)
- **AppDependency** - Service discovery, dependency mapping
- **FlowAnalysis** - Traffic analysis, anomaly detection
- **Agent** - Deploy and manage monitoring agents

**IoT & Embedded Modules (2 modules):**
- **RaspberryPi** - GPIO control, sensors, camera, IoT gateway
- **Arduino** - Sketch upload, Firmata protocol, serial communication

**Core Actions:**
- **Package:** `install`, `remove`
- **Files:** `copy`, `upload`, `download`, `template`, `create file`, `create directory`
- **Services:** `start service`, `stop service`, `restart service`, `enable service`, `disable service`
- **Commands:** `run "command"`
- **Firewall:** `ensure port X is open`, `ensure port X is closed`
- **Checks:** `check url`, `check port`, `check file`, `check service`
- **Wait:** `wait for port`, `wait for url`, `wait for X seconds`
- **Users:** `create user`, `delete user`

### Built-in Variables

Always available:
- `{hostname}` - Target hostname
- `{os}` - OS name (ubuntu, centos, debian, etc.)
- `{os_family}` - OS family (debian, redhat, arch, alpine)
- `{arch}` - Architecture (x86_64, aarch64)
- `{date}` - Current date
- `{timestamp}` - Unix timestamp

## CLI Commands

```bash
# Run ALL tasks in a file (default)
si run myfile.si

# Run a specific task only
si run myfile.si --task "Deploy App"

# Show execution plan for all tasks (dry run)
si run myfile.si --plan

# Validate syntax
si validate myfile.si

# Create example project
si init

# Show version
si version
```

**Note:** By default, SimpleInfra runs ALL tasks in a file sequentially. Use `--task` to run a specific task only.

## Examples

See the `examples/` directory for complete examples:

**Windows-Compatible (Local Testing):**
- `hello_world.si` - Simplest possible example
- `quick_test.si` - Quick test with file operations
- `showcase_features.si` - Variables and multiple tasks demo
- `local_webserver.si` - Local web server on port 8080

**Linux Servers (Remote SSH):**
- `web_server.si` - Web server setup with nginx
- `full_deploy.si` - Complete multi-server deployment
- `security_hardening.si` - Security configuration
- `network_segmentation.si` - Network segmentation with VLANs
- `policy_templates.si` - Illumio-style security policies
- `app_dependency_mapping.si` - Service discovery and mapping
- `flow_analysis.si` - Traffic flow analysis

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for detailed testing instructions.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/
```

## Architecture

SimpleInfra follows a clean architecture:

1. **Parser** - Lark-based LALR parser converts `.si` files to AST
2. **Validator** - Semantic validation (undefined refs, type checking)
3. **Executor** - Walks AST and dispatches to modules
4. **Connectors** - Abstract interface for SSH/Local/Docker/Cloud
5. **Modules** - Pluggable action handlers (package, file, service, etc.)

## Comparison to Ansible

| Feature | SimpleInfra | Ansible |
|---------|-------------|---------|
| **Syntax** | Custom DSL (readable) | YAML (verbose) |
| **Learning curve** | Minutes | Hours to days |
| **File size** | Small | Large (lots of boilerplate) |
| **Speed** | Fast (async Python) | Slower (sync execution) |
| **Modules** | Built-in essentials | 3000+ modules |
| **Maturity** | New | Battle-tested |

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.
