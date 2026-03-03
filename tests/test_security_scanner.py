"""Tests for Security Scanner module."""

import pytest
from simpleinfra.modules.security.scanner import SecurityScannerModule
from simpleinfra.modules.base import ModuleResult
from simpleinfra.connectors.local import LocalConnector
from simpleinfra.engine.context import ExecutionContext


@pytest.mark.asyncio
async def test_security_scanner_module_import():
    """Test that SecurityScannerModule can be imported."""
    scanner = SecurityScannerModule()
    assert scanner is not None


@pytest.mark.asyncio
async def test_security_scanner_invalid_type():
    """Test that invalid scan type returns error."""
    scanner = SecurityScannerModule()
    connector = LocalConnector()
    context = ExecutionContext(variables={}, secrets={})

    result = await scanner.execute(
        connector,
        context,
        scan_type="invalid_type"
    )

    assert result.success is False
    assert "Unknown scan type" in result.message


@pytest.mark.asyncio
async def test_parse_security_scan_syntax():
    """Test that security scan syntax parses correctly."""
    from simpleinfra.dsl.parser import SimpleInfraParser

    source = """
task "Security Test" on local:
    security scan:
        type "vulnerability"
        target "filesystem"
"""

    parser = SimpleInfraParser()
    doc = parser.parse(source)

    assert len(doc.tasks) == 1
    assert doc.tasks[0].name == "Security Test"

    # Check that we have a SecurityScanAction
    from simpleinfra.ast.nodes import SecurityScanAction
    actions = doc.tasks[0].actions
    assert len(actions) > 0
    assert isinstance(actions[0], SecurityScanAction)
    assert actions[0].params.get("type") == "vulnerability"
    assert actions[0].params.get("target") == "filesystem"


@pytest.mark.asyncio
async def test_parse_inline_security_scan():
    """Test inline security scan syntax."""
    from simpleinfra.dsl.parser import SimpleInfraParser

    source = """
task "Quick Scan" on local:
    security scan type="ports"
"""

    parser = SimpleInfraParser()
    doc = parser.parse(source)

    assert len(doc.tasks) == 1
    from simpleinfra.ast.nodes import SecurityScanAction
    actions = doc.tasks[0].actions
    assert isinstance(actions[0], SecurityScanAction)
    assert actions[0].params.get("type") == "ports"


def test_module_registry_has_security_scanner():
    """Test that security scanner is registered."""
    from simpleinfra.modules.registry import create_default_registry
    from simpleinfra.ast.nodes import SecurityScanAction

    registry = create_default_registry()
    assert registry.has(SecurityScanAction)

    module = registry.get(SecurityScanAction)
    assert isinstance(module, SecurityScannerModule)


@pytest.mark.asyncio
async def test_security_scan_example_parses():
    """Test that security_scan.si example file parses."""
    from pathlib import Path
    from simpleinfra.dsl.parser import SimpleInfraParser

    example_file = Path(__file__).parent.parent / "examples" / "security_scan.si"

    if example_file.exists():
        parser = SimpleInfraParser()
        doc = parser.parse_file(example_file)
        assert doc is not None
        assert len(doc.tasks) > 0
