"""Basic parser tests for SimpleInfra."""

import pytest
from simpleinfra.dsl.parser import SimpleInfraParser
from simpleinfra.ast.nodes import Document, TaskDecl, ServerDecl


def test_parse_simple_task():
    """Test parsing a simple task."""
    source = """
task "Hello" on local:
    run "echo hello"
"""
    parser = SimpleInfraParser()
    doc = parser.parse(source)

    assert len(doc.tasks) == 1
    assert doc.tasks[0].name == "Hello"
    assert doc.tasks[0].target == "local"


def test_parse_server_definition():
    """Test parsing server definition."""
    source = """
server web:
    host "192.168.1.10"
    user "root"
    port 22
"""
    parser = SimpleInfraParser()
    doc = parser.parse(source)

    assert len(doc.servers) == 1
    assert doc.servers[0].name == "web"
    assert doc.servers[0].host == "192.168.1.10"
    assert doc.servers[0].user == "root"
    assert doc.servers[0].port == 22


def test_parse_variables():
    """Test parsing variables."""
    source = """
set app_name "myapp"
set app_port 8080

task "Test" on local:
    run "echo {app_name}"
"""
    parser = SimpleInfraParser()
    doc = parser.parse(source)

    assert len(doc.variables) == 2
    assert doc.variables[0].name == "app_name"
    assert doc.variables[1].name == "app_port"


def test_parse_install_action():
    """Test parsing install action."""
    source = """
task "Setup" on local:
    install nginx
    install python3, git
"""
    parser = SimpleInfraParser()
    doc = parser.parse(source)

    from simpleinfra.ast.nodes import InstallAction
    assert len(doc.tasks) == 1
    assert len(doc.tasks[0].actions) == 2
    assert isinstance(doc.tasks[0].actions[0], InstallAction)
    assert doc.tasks[0].actions[1].packages == ("python3", "git")


def test_parse_invalid_syntax():
    """Test that invalid syntax raises an error."""
    source = """
task "Broken" on local
    run "oops no colon"
"""
    parser = SimpleInfraParser()

    with pytest.raises(Exception):
        parser.parse(source)


def test_variable_resolution():
    """Test variable resolution."""
    from simpleinfra.variables.resolver import VariableResolver

    resolver = VariableResolver(
        variables={"app_name": "myapp", "port": 8080},
        secrets={},
        facts={},
        builtins={},
    )

    result = resolver.resolve("App: {app_name} on port {port}")
    assert result == "App: myapp on port 8080"
