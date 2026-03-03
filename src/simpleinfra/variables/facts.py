"""Host fact gathering for SimpleInfra.

Auto-detects OS, architecture, hostname and other system facts
from a connected target. Facts are available as built-in variables
in task actions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..connectors.base import Connector


async def gather_facts(connector: "Connector") -> dict[str, str]:
    """Gather system facts from a connected target.

    Returns a dictionary with keys:
        - os: OS name (e.g. "ubuntu", "centos", "debian", "alpine")
        - os_family: OS family (e.g. "debian", "redhat", "alpine", "arch")
        - os_version: OS version string
        - arch: Architecture (e.g. "x86_64", "aarch64")
        - hostname: System hostname
        - kernel: Kernel version
    """
    facts: dict[str, str] = {}

    # Hostname
    result = await connector.run_command("hostname")
    facts["hostname"] = result.stdout.strip() if result.success else "unknown"

    # Architecture
    result = await connector.run_command("uname -m")
    facts["arch"] = result.stdout.strip() if result.success else "unknown"

    # Kernel
    result = await connector.run_command("uname -r")
    facts["kernel"] = result.stdout.strip() if result.success else "unknown"

    # OS detection via /etc/os-release (works on most modern Linux)
    result = await connector.run_command("cat /etc/os-release 2>/dev/null")
    if result.success:
        os_info = _parse_os_release(result.stdout)
        facts["os"] = os_info.get("id", "linux").lower()
        facts["os_version"] = os_info.get("version_id", "unknown")
        facts["os_family"] = _detect_os_family(facts["os"])
    else:
        facts["os"] = "linux"
        facts["os_version"] = "unknown"
        facts["os_family"] = "unknown"

    return facts


def get_local_facts() -> dict[str, str]:
    """Gather facts for the local machine (non-async)."""
    import platform
    import socket

    system = platform.system().lower()
    facts = {
        "hostname": socket.gethostname(),
        "arch": platform.machine(),
        "kernel": platform.release(),
        "os": system,
        "os_version": platform.version(),
    }

    if system == "linux":
        try:
            with open("/etc/os-release") as f:
                os_info = _parse_os_release(f.read())
            facts["os"] = os_info.get("id", "linux").lower()
            facts["os_version"] = os_info.get("version_id", "unknown")
        except FileNotFoundError:
            pass
    elif system == "windows":
        facts["os_family"] = "windows"
    elif system == "darwin":
        facts["os_family"] = "darwin"

    facts.setdefault("os_family", _detect_os_family(facts["os"]))
    return facts


def _parse_os_release(content: str) -> dict[str, str]:
    """Parse /etc/os-release into a dictionary."""
    result: dict[str, str] = {}
    for line in content.strip().splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip().strip('"')
    return result


def _detect_os_family(os_name: str) -> str:
    """Map OS name to OS family."""
    families = {
        "debian": ("debian", "ubuntu", "mint", "pop", "elementary", "kali", "raspbian"),
        "redhat": ("centos", "rhel", "fedora", "rocky", "alma", "oracle", "amazon"),
        "arch": ("arch", "manjaro", "endeavouros"),
        "alpine": ("alpine",),
        "suse": ("opensuse", "sles", "suse"),
    }
    for family, members in families.items():
        if os_name in members:
            return family
    return "unknown"
