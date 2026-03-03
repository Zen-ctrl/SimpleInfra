# Network Segmentation Guide for SimpleInfra

## Overview

SimpleInfra provides powerful **agentless** network segmentation capabilities while optionally allowing deployment of lightweight monitoring agents when needed. The core tool remains completely agentless - using SSH for all operations.

### Key Principles

1. **Agentless by Default** - All segmentation uses SSH, no daemons required
2. **Optional Agents** - Deploy temporary monitoring agents only when needed
3. **Easy Cleanup** - Agents can be removed with a single command
4. **Declarative** - Define network topology in simple `.si` files
5. **Automated** - No manual firewall rule management

---

## Agentless Architecture

SimpleInfra is **completely agentless**:

```
Your Machine (SimpleInfra CLI)
         ↓ SSH
Target Machine (No agent!)
         ↓
Configure firewall/network via SSH
         ↓
Done!
```

**No persistent agents** - all configuration happens via SSH and standard Linux tools.

---

## Network Segmentation Capabilities

### 1. Network Isolation

Create isolated network zones with firewall rules:

```simpleinfra
task "Isolate DMZ" on dmz_server:
    network:
        action "isolate"
        zone "dmz"
        allowed_ips ["192.168.1.0/24"]
        allowed_ports [80, 443, 22]
        default_policy "deny"
```

**What it does:**
- Creates firewall rules to isolate the zone
- Only allows specific IPs and ports
- Defaults to deny-all for security
- Works with UFW or iptables (auto-detected)

### 2. VLAN Management

Create and manage VLANs for network segmentation:

```simpleinfra
task "Create VLANs" on network_host:
    # Web tier VLAN
    network:
        action "vlan"
        vlan_id 10
        interface "eth0"
        ip_address "10.0.10.1"
        operation "create"

    # App tier VLAN
    network:
        action "vlan"
        vlan_id 20
        interface "eth0"
        ip_address "10.0.20.1"
        operation "create"
```

**Features:**
- Creates 802.1Q VLAN interfaces
- Assigns IP addresses automatically
- Works with standard Linux networking
- Can delete VLANs: `operation "delete"`

### 3. Network Discovery

Discover network topology and connected devices:

```simpleinfra
task "Map Network" on gateway:
    network:
        action "discover"
        subnet "192.168.0.0/16"
        scan_type "ping"  # or "fast", "full"
```

**Scan types:**
- `ping` - Quick ping scan to find alive hosts
- `fast` - Fast port scan on common ports
- `full` - Comprehensive scan with OS detection

### 4. Firewall Zones (firewalld)

Create security zones with firewalld:

```simpleinfra
task "Create Zones" on firewall_host:
    network:
        action "zone"
        zone "dmz"
        interfaces ["eth0"]
        sources ["192.168.1.0/24"]
        services ["http", "https"]
        ports ["8080/tcp"]
```

**Benefits:**
- High-level zone management
- Service-based rules (no port numbers needed)
- Persistent configuration
- Runtime and permanent rules

### 5. Micro-Segmentation

Create precise segmentation rules between hosts:

```simpleinfra
task "Microsegment" on app_server:
    network:
        action "microsegment"
        from ["10.0.10.0/24"]  # Web tier
        to ["10.0.20.0/24"]    # App tier
        ports [8080, 8443]
        protocol "tcp"
```

**Use cases:**
- Zero-trust networking
- East-west traffic control
- Service-to-service security
- Compliance requirements (PCI-DSS, etc.)

### 6. Traffic Control (QoS)

Control network traffic with traffic shaping:

```simpleinfra
task "Apply QoS" on router:
    # Limit bandwidth
    network:
        action "traffic_control"
        interface "eth0"
        tc_action "limit"
        bandwidth "100mbit"

    # Add delay (testing)
    network:
        action "traffic_control"
        interface "eth1"
        tc_action "delay"
        delay "100ms"

    # Simulate packet loss (testing)
    network:
        action "traffic_control"
        interface "eth2"
        tc_action "loss"
        packet_loss "0.1%"
```

---

## Optional Agent Deployment

While SimpleInfra is agentless, you can optionally deploy lightweight monitoring agents for continuous monitoring.

### When to Use Agents

**Use agents when:**
- Need continuous real-time monitoring
- Want automated alerting
- Require distributed traffic analysis
- Need policy enforcement checking

**Don't use agents when:**
- One-time configuration is sufficient
- Security policy prohibits agents
- Resources are constrained

### Deploying Agents (Agentless!)

Agents are deployed via SSH - no manual installation needed:

```simpleinfra
task "Deploy Monitoring" on servers:
    agent:
        action "deploy"
        zone "web-tier"
        interval 60
        mode "daemon"
        actions ["monitor_connections", "check_firewall"]
```

**What happens:**
1. Agent script uploaded via SSH
2. Configuration written to `/tmp/simpleinfra_agent_config.json`
3. systemd service created
4. Agent starts monitoring

**The agent is:**
- Single Python script (~200 lines)
- Minimal resource usage
- Logs to `/tmp/simpleinfra_agent.log`
- Easy to remove

### Agent Actions

Configure what the agent monitors:

```python
actions = [
    "monitor_connections",  # Track active connections
    "check_firewall",       # Monitor firewall rules
]
```

### Agent Configuration

```simpleinfra
task "Configure Agent" on server:
    agent:
        action "configure"
        interval 30          # Check every 30 seconds
        coordinator "http://monitor.local"
        zone "dmz"
```

### Check Agent Status

```simpleinfra
task "Check Status" on server:
    agent:
        action "status"
```

Returns:
- Running/stopped status
- Configuration
- Recent logs (last 20 lines)

### Remove Agents

Return to fully agentless:

```simpleinfra
task "Remove Agents" on servers:
    agent:
        action "remove"
```

**Removes:**
- Agent script
- Configuration files
- systemd service
- Log files

---

## Complete Network Segmentation Example

### Three-Tier Architecture

```simpleinfra
# Three-tier application with network segmentation

# Infrastructure
server web1:
    host "192.168.1.11"
    user "deploy"
    key "~/.ssh/id_ed25519"

server app1:
    host "192.168.2.11"
    user "deploy"
    key "~/.ssh/id_ed25519"

server db1:
    host "192.168.3.11"
    user "deploy"
    key "~/.ssh/id_ed25519"

# 1. Isolate Web Tier (Public)
task "Setup Web Tier" on web1:
    # Allow public access
    network:
        action "isolate"
        zone "web"
        allowed_ips ["0.0.0.0/0"]
        allowed_ports [80, 443, 22]
        default_policy "deny"

# 2. Isolate App Tier (Internal)
task "Setup App Tier" on app1:
    # Only allow from web tier
    network:
        action "isolate"
        zone "app"
        allowed_ips ["192.168.1.0/24"]
        allowed_ports [8080, 22]
        default_policy "deny"

# 3. Isolate Database Tier (Restricted)
task "Setup Database Tier" on db1:
    # Only allow from app tier
    network:
        action "isolate"
        zone "database"
        allowed_ips ["192.168.2.0/24"]
        allowed_ports [5432, 22]
        default_policy "deny"

# 4. Micro-segment app -> database
task "Microsegment App-DB" on db1:
    network:
        action "microsegment"
        from ["192.168.2.11"]
        to ["192.168.3.11"]
        ports [5432]
        protocol "tcp"

# 5. Optional: Deploy monitoring agents
task "Deploy Monitors" on web1:
    agent:
        action "deploy"
        zone "web"
        interval 60
        mode "daemon"

# 6. Verify segmentation
task "Verify" on web1:
    run "echo 'Testing segmentation...'"
    run "ping -c 1 192.168.2.11"  # Should work
    run "ping -c 1 192.168.3.11"  # Should fail (blocked)
```

---

## Network Syntax Reference

### Network Action

**Block style:**
```simpleinfra
network:
    action "isolate"
    zone "dmz"
    allowed_ips ["192.168.1.0/24"]
    allowed_ports [80, 443]
```

**Inline style:**
```simpleinfra
network action="discover" subnet="192.168.1.0/24" scan_type="ping"
```

### Agent Action

**Block style:**
```simpleinfra
agent:
    action "deploy"
    zone "web"
    interval 60
    mode "daemon"
```

**Inline style:**
```simpleinfra
agent action="status"
```

---

## Network Actions Reference

| Action | Purpose | Parameters |
|--------|---------|------------|
| `isolate` | Create isolated zone | zone, allowed_ips, allowed_ports, default_policy |
| `vlan` | Manage VLANs | vlan_id, interface, ip_address, operation |
| `discover` | Network discovery | subnet, scan_type |
| `zone` | Firewall zones | zone, interfaces, sources, services, ports |
| `microsegment` | Precise segmentation | from, to, ports, protocol |
| `traffic_control` | QoS/Traffic shaping | interface, tc_action, bandwidth, delay, packet_loss |

## Agent Actions Reference

| Action | Purpose | Parameters |
|--------|---------|------------|
| `deploy` | Deploy agent | zone, interval, mode, actions |
| `remove` | Remove agent | none |
| `status` | Check agent status | none |
| `configure` | Update configuration | interval, coordinator, zone, actions |

---

## Use Cases

### 1. DMZ Setup

```simpleinfra
task "Create DMZ" on edge:
    network:
        action "isolate"
        zone "dmz"
        allowed_ips ["0.0.0.0/0"]
        allowed_ports [80, 443]
```

### 2. Multi-Tenant Isolation

```simpleinfra
task "Isolate Tenants" on app:
    # Tenant A
    network action="vlan" vlan_id=100 ip_address="10.0.100.1"

    # Tenant B
    network action="vlan" vlan_id=200 ip_address="10.0.200.1"
```

### 3. Zero-Trust Networking

```simpleinfra
task "Zero Trust" on servers:
    # Default deny all
    network:
        action "isolate"
        zone "zero-trust"
        default_policy "deny"

    # Explicitly allow only required traffic
    network:
        action "microsegment"
        from ["10.0.1.10"]
        to ["10.0.2.20"]
        ports [443]
```

### 4. Compliance (PCI-DSS)

```simpleinfra
task "PCI Compliance" on cardholder_data:
    # Segment cardholder data environment
    network:
        action "isolate"
        zone "cde"
        allowed_ips ["10.0.0.0/8"]
        default_policy "deny"

    # Monitor continuously
    agent:
        action "deploy"
        zone "cde"
        interval 30
        actions ["monitor_connections", "check_firewall"]
```

---

## Best Practices

### 1. Start Agentless

Always start with agentless configuration:
```simpleinfra
# ✅ Good - agentless
network action="isolate" zone="web"

# ❌ Don't jump to agents immediately
agent action="deploy"  # Only if really needed
```

### 2. Default Deny

Always use default deny policies:
```simpleinfra
network:
    action "isolate"
    default_policy "deny"  # ✅ Secure by default
    allowed_ports [80, 443]
```

### 3. Micro-Segment Critical Systems

Use micro-segmentation for high-value targets:
```simpleinfra
# Database should only accept from app tier
network:
    action "microsegment"
    from ["10.0.2.0/24"]  # App tier
    to ["10.0.3.0/24"]    # DB tier
    ports [5432]
```

### 4. Monitor Changes

Deploy agents only for continuous monitoring:
```simpleinfra
# After segmentation, optionally monitor
agent:
    action "deploy"
    mode "daemon"
    interval 60
```

### 5. Test Thoroughly

Always verify segmentation:
```simpleinfra
task "Verify" on server:
    # Should succeed
    run "ping -c 1 allowed-host"

    # Should fail
    run "ping -c 1 blocked-host" # Will fail - as expected
```

---

## Agentless vs. Agent Comparison

| Aspect | Agentless | With Agents |
|--------|-----------|-------------|
| **Deployment** | SSH only | SSH + agent script |
| **Resources** | None on target | Minimal (~10MB RAM) |
| **Monitoring** | On-demand via SSH | Continuous real-time |
| **Complexity** | Very simple | Slightly more complex |
| **Use case** | One-time config | Continuous monitoring |
| **Cleanup** | Nothing to clean | `agent action="remove"` |

---

## Troubleshooting

### Issue: Firewall rules not applying

**Check firewall system:**
```simpleinfra
task "Check Firewall" on server:
    run "which ufw"
    run "which iptables"
    run "which firewall-cmd"
```

### Issue: VLAN not created

**Check kernel module:**
```simpleinfra
task "Check VLAN Support" on server:
    run "lsmod | grep 8021q"
    run "modprobe 8021q"
```

### Issue: Agent not starting

**Check logs:**
```simpleinfra
task "Debug Agent" on server:
    run "systemctl status simpleinfra-agent"
    run "journalctl -u simpleinfra-agent -n 50"
    run "cat /tmp/simpleinfra_agent.log"
```

---

## Advanced Topics

### Network as Code

Version control your network segmentation:

```bash
git add network_segmentation.si
git commit -m "Add network segmentation for prod"
git push
```

### CI/CD Integration

Automate network changes:

```yaml
# .github/workflows/network.yml
- name: Apply Network Segmentation
  run: |
    si run network_segmentation.si --task "Setup All Zones"
```

### Multi-Cloud Segmentation

Apply same segmentation across clouds:

```simpleinfra
group all_clouds:
    server aws_web
    server azure_web
    server gcp_web

task "Segment All" on all_clouds:
    network action="isolate" zone="web"
```

---

## Summary

SimpleInfra provides:

✅ **Agentless network segmentation** - SSH-based, no daemons
✅ **Optional lightweight agents** - Deploy only when needed
✅ **Declarative configuration** - Network as code
✅ **Multiple approaches** - VLANs, firewall zones, micro-segmentation
✅ **Auto-detection** - Works with UFW, iptables, firewalld
✅ **Easy cleanup** - Remove agents with one command

**Philosophy:** Stay agentless by default, use agents only for continuous monitoring.

---

## Next Steps

1. Read [examples/network_segmentation.si](examples/network_segmentation.si)
2. Read [examples/agentless_segmentation.si](examples/agentless_segmentation.si)
3. Start with simple isolation
4. Add micro-segmentation as needed
5. Deploy agents only if continuous monitoring is required

**Network Segmentation Made Simple!** 🛡️
