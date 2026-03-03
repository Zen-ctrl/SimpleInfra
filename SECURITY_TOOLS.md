# Security Tools Guide for SimpleInfra

SimpleInfra includes comprehensive security scanning and hardening tools to help you secure your infrastructure.

## Security Scanner Module

The `security scan` action provides multiple types of security scans to identify vulnerabilities, misconfigurations, and compliance issues.

### Scan Types

#### 1. Vulnerability Scanning

Scans for known vulnerabilities using [Trivy](https://github.com/aquasecurity/trivy), a comprehensive vulnerability scanner.

**Filesystem Scan:**
```simpleinfra
task "Scan System" on prod:
    security scan:
        type "vulnerability"
        target "filesystem"
```

**Docker Image Scan:**
```simpleinfra
task "Scan Container" on prod:
    security scan:
        type "vulnerability"
        target "docker"
        image "nginx:latest"
```

**Inline Syntax:**
```simpleinfra
security scan type="vulnerability" target="filesystem"
```

#### 2. Port Scanning

Identifies open ports on the target system using nmap.

```simpleinfra
task "Audit Ports" on prod:
    security scan:
        type "ports"
```

**Use Cases:**
- Verify firewall rules
- Identify unexpected open ports
- Security compliance audits

#### 3. SSL/TLS Scanning

Checks SSL/TLS configuration using [testssl.sh](https://github.com/drwetter/testssl.sh).

```simpleinfra
task "Check SSL" on web:
    security scan:
        type "ssl"
        domain "example.com"
```

**Detects:**
- Weak ciphers
- Protocol vulnerabilities
- Certificate issues
- Configuration problems

#### 4. Dependency Scanning

Scans project dependencies for known vulnerabilities.

**Python Projects:**
```simpleinfra
task "Scan Python Dependencies" on dev:
    security scan:
        type "dependencies"
        path "/opt/myapp"
        language "python"
```

**JavaScript Projects:**
```simpleinfra
task "Scan NPM Dependencies" on dev:
    security scan:
        type "dependencies"
        path "/opt/myapp"
        language "javascript"
```

**Auto-detect:**
```simpleinfra
security scan type="dependencies" path="." language="auto"
```

#### 5. CIS Benchmark Compliance

Runs CIS (Center for Internet Security) benchmark tests using Lynis.

```simpleinfra
task "CIS Audit" on prod:
    security scan:
        type "cis"

    # Ensure minimum security score
    check security score >= 70
```

**What it checks:**
- System hardening
- File permissions
- User accounts
- Service configurations
- Kernel parameters
- Network security

#### 6. Docker Security Scan

Scans Docker containers and images for vulnerabilities.

**Scan specific image:**
```simpleinfra
task "Scan Docker Image" on docker_host:
    security scan:
        type "docker"
        image "myapp:latest"
```

**Scan all running containers:**
```simpleinfra
task "Scan All Containers" on docker_host:
    security scan:
        type "docker"
```

---

## Complete Security Hardening Example

Here's a full example that deploys a web server with comprehensive security:

```simpleinfra
# security_deployment.si

set app_name "secure-webapp"
set domain "example.com"

server web:
    host "192.168.1.10"
    user "deploy"
    key "~/.ssh/id_ed25519"

# Phase 1: System Hardening
task "Harden System" on web:
    # Update system
    run "apt-get update && apt-get upgrade -y"

    # Install security tools
    install ufw fail2ban aide

    # Configure firewall
    ensure port 22 is open
    ensure port 80 is open
    ensure port 443 is open
    run "ufw --force enable"

    # Harden SSH
    copy "configs/sshd_hardened.conf" to "/etc/ssh/sshd_config"
    restart service ssh

    # Setup intrusion detection
    run "aide --init"
    run "mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db"

# Phase 2: Deploy Application
task "Deploy Application" on web:
    install nginx certbot python3-certbot-nginx

    copy "configs/nginx-secure.conf" to "/etc/nginx/sites-available/{app_name}"
    run "ln -sf /etc/nginx/sites-available/{app_name} /etc/nginx/sites-enabled/"

    # Get SSL certificate
    run "certbot --nginx -d {domain} --non-interactive --agree-tos -m admin@{domain}"

    start service nginx
    ensure service nginx is running

# Phase 3: Security Validation
task "Security Audit" on web:
    run "echo 'Running comprehensive security audit...'"

    # Vulnerability scan
    security scan:
        type "vulnerability"
        target "filesystem"

    # Port scan - verify only required ports are open
    security scan:
        type "ports"

    # SSL/TLS check
    security scan:
        type "ssl"
        domain "{domain}"

    # CIS Benchmark
    security scan:
        type "cis"

    # Application dependencies
    security scan:
        type "dependencies"
        path "/var/www/app"
        language "auto"

    # Verify security score
    check security score >= 70

    run "echo 'Security audit complete!'"

# Phase 4: Continuous Monitoring
task "Setup Monitoring" on web:
    # Daily security scans
    copy "scripts/daily-security-scan.sh" to "/etc/cron.daily/security-scan"
    run "chmod +x /etc/cron.daily/security-scan"

    # Automatic security updates
    install unattended-upgrades
    run "dpkg-reconfigure -plow unattended-upgrades"

    # Log monitoring
    install logwatch
    run "echo 'Security monitoring configured'"
```

**Deploy the complete stack:**
```bash
si run security_deployment.si --task "Harden System"
si run security_deployment.si --task "Deploy Application"
si run security_deployment.si --task "Security Audit"
si run security_deployment.si --task "Setup Monitoring"
```

---

## Security Scan Results

### Understanding Results

Each security scan returns a `ModuleResult` with:
- `success`: Whether the scan passed (no critical issues found)
- `changed`: Always `false` for scans (read-only)
- `message`: Summary of findings
- `details`: Full scan output and structured data

### Example Results

**Vulnerability Scan:**
```json
{
  "success": false,
  "changed": false,
  "message": "Security scan complete - vulnerabilities found!",
  "details": {
    "has_vulnerabilities": true,
    "stdout": "... Trivy output ..."
  }
}
```

**CIS Benchmark:**
```json
{
  "success": true,
  "changed": false,
  "message": "CIS Benchmark score: 85/100",
  "details": {
    "score": 85,
    "passed": true,
    "stdout": "... Lynis output ..."
  }
}
```

---

## Best Practices

### 1. Run Scans Regularly

Include security scans in your CI/CD pipeline:

```simpleinfra
plan "Deploy with Security":
    run task "Deploy Application"
    run task "Security Audit"
    run task "Verify Security Score"
```

### 2. Set Minimum Security Thresholds

Use `check` statements to enforce security requirements:

```simpleinfra
task "Validate Security" on prod:
    security scan type="cis"
    check security score >= 70
```

### 3. Scan Before and After Deployment

```simpleinfra
plan "Secure Deployment":
    run task "Baseline Security Scan"
    run task "Deploy Application"
    run task "Post-Deploy Security Scan"
    run task "Compare Results"
```

### 4. Automate Remediation

```simpleinfra
task "Auto-Remediate" on prod:
    security scan type="vulnerability"

    if vulnerabilities found:
        run "apt-get update && apt-get upgrade -y"
        security scan type="vulnerability"
```

### 5. Layer Security Scans

Use multiple scan types for comprehensive coverage:

```simpleinfra
task "Complete Security Audit" on prod:
    security scan type="vulnerability"
    security scan type="ports"
    security scan type="ssl" domain="myapp.com"
    security scan type="dependencies" path="/opt/app"
    security scan type="cis"
    security scan type="docker"
```

---

## Security Tools Reference

### Trivy
- **Purpose:** Vulnerability scanner
- **Scans:** OS packages, application dependencies, Docker images
- **Speed:** Fast (uses cached vulnerability DB)
- **Output:** JSON, table, or SARIF

### Nmap
- **Purpose:** Port scanner
- **Scans:** Open ports, services, versions
- **Use Cases:** Network security audits
- **Flags:** `-p-` (all ports), `-sV` (version detection)

### testssl.sh
- **Purpose:** SSL/TLS scanner
- **Checks:** Protocols, ciphers, certificates
- **Standards:** Follows OWASP recommendations
- **Output:** Color-coded results

### Safety (Python)
- **Purpose:** Python dependency scanner
- **Database:** PyPI vulnerability database
- **Coverage:** 50,000+ known vulnerabilities
- **Integration:** Works with requirements.txt

### npm audit (JavaScript)
- **Purpose:** Node.js dependency scanner
- **Database:** npm security advisories
- **Features:** Auto-fix available
- **Integration:** Built into npm

### Lynis
- **Purpose:** System auditing tool
- **Standards:** CIS benchmarks
- **Coverage:** 300+ security checks
- **Output:** Hardening index score (0-100)

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install SimpleInfra
        run: pip install simpleinfra

      - name: Run Security Scans
        run: |
          si run security_audit.si --task "Complete Security Audit"

      - name: Check Security Score
        run: |
          si run security_audit.si --task "Verify Minimum Score"
```

### GitLab CI Example

```yaml
security_scan:
  stage: test
  script:
    - pip install simpleinfra
    - si run security_audit.si --task "Security Audit"
  only:
    - main
    - merge_requests
```

---

## Troubleshooting

### Common Issues

**1. Trivy installation fails:**
```simpleinfra
# Manual installation
task "Install Trivy" on prod:
    run "wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor | sudo tee /usr/share/keyrings/trivy.gpg"
    run "echo 'deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main' | sudo tee /etc/apt/sources.list.d/trivy.list"
    run "apt-get update && apt-get install -y trivy"
```

**2. Port scan requires root:**
```simpleinfra
# Run with sudo
task "Port Scan" on prod:
    run "nmap -p- localhost" sudo=true
```

**3. SSL scan fails for internal domains:**
```simpleinfra
# Use IP instead of domain
task "Internal SSL Check" on prod:
    security scan:
        type "ssl"
        domain "192.168.1.10:443"
```

---

## Compliance

SimpleInfra security tools help you meet compliance requirements:

- **PCI-DSS:** Port scanning, vulnerability scanning, SSL checks
- **SOC 2:** CIS benchmarks, audit logging, access controls
- **HIPAA:** Encryption checks, access audits, system hardening
- **ISO 27001:** Risk assessments, vulnerability management
- **GDPR:** Security by design, data protection measures

---

## Next Steps

1. **Review** the [examples/security_scan.si](examples/security_scan.si) file
2. **Run** a baseline security scan on your infrastructure
3. **Set** minimum security score thresholds
4. **Automate** regular security scans
5. **Integrate** with your CI/CD pipeline
6. **Monitor** security scores over time

---

## Resources

- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Nmap Guide](https://nmap.org/book/)
- [testssl.sh Documentation](https://testssl.sh/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [OWASP Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)

---

**Security is a journey, not a destination. Use SimpleInfra to make it simple!** 🔒
