# Testing SimpleInfra Locally

Quick guide to test SimpleInfra on your local machine!

## Prerequisites

- Python 3.10+
- Linux, macOS, or Windows with WSL
- SimpleInfra installed

## Quick Start

**Note:** SimpleInfra now runs **ALL tasks** in a file by default (sequentially). Use `--task "Name"` to run a specific task only.

### 1. Quick Test (30 seconds)

The simplest test to verify everything works:

```bash
cd simpleinfra
python -m simpleinfra.cli.app run examples/quick_test.si
```

**What it does:**
- ✅ Shows system info
- ✅ Creates a test directory
- ✅ Creates a test file
- ✅ Displays the file contents

**Windows Compatible:** ✅ Yes

**Expected output:**
```
================================
🚀 SimpleInfra Quick Test
================================

📊 System Info:
User: yourname
Directory: /path/to/simpleinfra
Date: Mon Jan 1 12:00:00 2024

📁 Created: /tmp/simpleinfra-test
📝 Created: /tmp/simpleinfra-test/hello.txt

📄 File contents:
Hello from SimpleInfra! This file was created by infrastructure-as-code.

✅ Success! SimpleInfra is working correctly.
```

---

### 2. Features Showcase (1 minute)

Test variables and multiple tasks:

```bash
python -m simpleinfra.cli.app run examples/showcase_features.si
```

**What it does:**
- ✅ Demonstrates variable interpolation
- ✅ Creates directory structure
- ✅ Creates configuration files
- ✅ Shows file operations

**Check the results:**
```bash
ls -la /tmp/simpleinfra-showcase/
cat /tmp/simpleinfra-showcase/config/app.conf
```

---

### 3. Local Web Server (2 minutes)

Start a web server and see it in your browser:

```bash
python -m simpleinfra.cli.app run examples/local_webserver.si
```

**What it does:**
- ✅ Creates HTML files
- ✅ Starts Python web server on port 8080
- ✅ Makes it accessible in browser

**Test it:**
1. Run the example
2. Open your browser to: **http://localhost:8080**
3. You should see "SimpleInfra Demo" page

**Stop the server:**
```bash
pkill -f http.server
```

---

## Validation Only

To validate syntax without running:

```bash
# Validate single file
python -m simpleinfra.cli.app validate examples/quick_test.si

# Validate all examples
python -m simpleinfra.cli.app validate examples/*.si
```

---

## Command Reference

### Basic Commands

```bash
# Run ALL tasks in a .si file (default behavior)
python -m simpleinfra.cli.app run <file.si>

# Run a specific task only
python -m simpleinfra.cli.app run <file.si> --task "Task Name"

# Show execution plan for all tasks
python -m simpleinfra.cli.app run <file.si> --plan

# Validate syntax
python -m simpleinfra.cli.app validate <file.si>

# Show help
python -m simpleinfra.cli.app --help
```

### Task Execution Behavior

- **Default:** Runs ALL tasks in the file sequentially
- **With --task flag:** Runs only the specified task
- **Failure handling:** Stops on first failure
- **Multiple files:** Run separately with multiple commands

### Common Examples

```bash
# Hello world example
python -m simpleinfra.cli.app run examples/hello_world.si

# Web server setup
python -m simpleinfra.cli.app run examples/web_server.si

# Full deployment example
python -m simpleinfra.cli.app run examples/full_deploy.si

# Security scanning
python -m simpleinfra.cli.app run examples/security_scan.si

# Network segmentation
python -m simpleinfra.cli.app run examples/network_segmentation.si
```

---

## Troubleshooting

### Permission Errors

Some tasks may need `sudo`. Either:
1. Run with sudo: `sudo python -m simpleinfra.cli.app run examples/example.si`
2. Or modify the example to not need root

### Port Already in Use

If port 8080 is busy:
```bash
# Find what's using port 8080
lsof -i :8080

# Or kill it
pkill -f http.server
```

### File Not Found

Make sure you're in the `simpleinfra` directory:
```bash
cd simpleinfra
pwd  # Should show .../simpleinfra
```

---

## Creating Your Own Examples

### Minimal Example

Create a file `my_test.si`:

```simpleinfra
task "Hello World" on local:
    run "echo 'Hello from SimpleInfra!'"
```

Run it:
```bash
python -m simpleinfra.cli.app run my_test.si
```

### With Variables

```simpleinfra
set name "MyApp"
set version "1.0.0"

task "Show Info" on local:
    run "echo 'App: {name}'"
    run "echo 'Version: {version}'"
```

### Multiple Tasks

```simpleinfra
task "Setup" on local:
    run "mkdir -p /tmp/myapp"
    run "echo 'Setup complete'"

task "Deploy" on local:
    run "echo 'Deploying to /tmp/myapp'"
    run "echo 'Hello' > /tmp/myapp/index.html"

task "Verify" on local:
    run "cat /tmp/myapp/index.html"
```

---

## Next Steps

Once local testing works, try:

1. **Remote Execution** - Define servers and run tasks remotely via SSH
2. **Security Scanning** - Use the security modules
3. **Network Segmentation** - Try the network modules
4. **Infrastructure Deployment** - Use web server, database, and container modules

See the documentation:
- `NETWORK_MODULES_GUIDE.md` - Network segmentation features
- `SECURITY_TOOLS.md` - Security scanning
- `ILLUMIO_FEATURES.md` - Advanced network policies
- `INFRASTRUCTURE_MODULES_COMPLETE.md` - Infrastructure modules
- `IOT_MODULES_COMPLETE.md` - IoT and embedded systems

---

## Windows Compatibility

### Windows-Compatible Examples (Local Testing)

These examples work on Windows without modifications:

✅ **hello_world.si** - Basic hello world
✅ **quick_test.si** - Quick test with file creation
✅ **showcase_features.si** - Variables and multiple tasks demo
✅ **local_webserver.si** - Local web server on port 8080

### Linux-Only Examples (Require Remote Linux Server)

These examples are designed for Linux servers via SSH:

⚠️ **web_server.si** - Nginx setup (uses systemctl)
⚠️ **full_deploy.si** - Multi-server deployment
⚠️ **security_hardening.si** - Linux security tools
⚠️ **security_scan.si** - Security scanning tools

### Windows Command Differences

| Unix | Windows |
|------|---------|
| `mkdir -p dir` | `if not exist dir mkdir dir` |
| `cat file.txt` | `type file.txt` |
| `ls -la` | `dir` |
| `echo ''` | `echo.` |
| `$(pwd)` | `cd` |
| `$(date)` | `date /t` |
| Paths: `/tmp/file` | `file` or `C:\path\file` |

## Pro Tips

1. **Start Small** - Test with `quick_test.si` first
2. **Validate First** - Always validate before running
3. **Check Output** - Look for error messages
4. **Local First** - Test locally (`on local`) before SSH
5. **Use Variables** - Makes examples reusable
6. **Run All Tasks** - By default, all tasks run sequentially
7. **Windows Users** - Stick to the Windows-compatible examples for local testing

Happy testing! 🚀
