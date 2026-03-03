"""Integration tests for SimpleInfra."""

import asyncio
import pytest
from pathlib import Path
from simpleinfra.api.client import SimpleInfraClient


@pytest.mark.asyncio
async def test_local_execution():
    """Test executing a task locally."""
    client = SimpleInfraClient()

    # Create a simple task
    (client.create_task("test", target="local")
        .run("echo 'test'")
        .build())

    # Execute
    result = await client.execute_task("test")

    assert result["success"] is True


@pytest.mark.asyncio
async def test_programmatic_api():
    """Test using the Python API."""
    client = SimpleInfraClient()

    # Add server
    client.add_server("test_server", host="localhost", user="test")

    # Set variables
    client.set_variable("app_name", "testapp")

    # Create task
    (client.create_task("deploy", target="local")
        .run("echo 'deploying'")
        .build())

    # Execute
    result = await client.execute_task("deploy")

    assert result["success"] is True


def test_parse_example_files():
    """Test that all example files parse correctly."""
    examples_dir = Path(__file__).parent.parent / "examples"

    from simpleinfra.dsl.parser import SimpleInfraParser

    parser = SimpleInfraParser()

    for example_file in examples_dir.glob("*.si"):
        # Skip files that use API-only modules (no DSL syntax yet)
        skip_files = {
            "web3_complete.si",         # Web3 module (not implemented)
            "dmz_setup.si",             # DMZ module (API-only)
            "multitenant_example.si",   # MultiTenant module (API-only)
            "zerotrust_example.si",     # ZeroTrust module (API-only)
        }
        if example_file.name in skip_files:
            continue

        # Should not raise
        doc = parser.parse_file(example_file)
        assert doc is not None
