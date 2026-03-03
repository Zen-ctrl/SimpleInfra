"""AST node definitions for the SimpleInfra DSL.

Every node is a frozen dataclass carrying a SourceLocation for error reporting.
These types form the contract between the parser and the execution engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Union


# ------------------------------------------------------------------
# Source tracking
# ------------------------------------------------------------------

@dataclass(frozen=True)
class SourceLocation:
    file: str = ""
    line: int = 0
    column: int = 0


_DEFAULT_LOC = SourceLocation()


# ------------------------------------------------------------------
# Value types
# ------------------------------------------------------------------

@dataclass(frozen=True)
class StringValue:
    value: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class NumberValue:
    value: int
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class BooleanValue:
    value: bool
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class ListValue:
    items: tuple[Value, ...]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class VariableRef:
    name: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


Value = Union[StringValue, NumberValue, BooleanValue, ListValue, VariableRef]


# ------------------------------------------------------------------
# Top-level declarations
# ------------------------------------------------------------------

@dataclass(frozen=True)
class SetVariable:
    name: str
    value: Value
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class SecretDecl:
    name: str
    source_type: str          # "env" | "file"
    source_value: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class ServerDecl:
    name: str
    host: str
    user: str
    key: str | None = None
    password_secret: str | None = None
    port: int = 22
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class GroupMember:
    kind: str                 # "server" | "group"
    name: str


@dataclass(frozen=True)
class GroupDecl:
    name: str
    members: tuple[GroupMember, ...]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class DockerDecl:
    name: str
    container_name: str
    image: str
    network: str | None = None
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class CloudDecl:
    name: str
    provider: str             # "aws" | "azure" | "gcp"
    region: str
    profile: str | None = None
    credentials: str | None = None
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


# ------------------------------------------------------------------
# Check / ensure conditions
# ------------------------------------------------------------------

@dataclass(frozen=True)
class PortCondition:
    port: Value
    state: str               # "open" | "closed"


@dataclass(frozen=True)
class ServiceCondition:
    service_name: str
    state: str               # "running" | "stopped"


@dataclass(frozen=True)
class UrlCondition:
    url: str
    expected_status: int


@dataclass(frozen=True)
class FileExistsCondition:
    path: str


@dataclass(frozen=True)
class FileContainsCondition:
    path: str
    content: str


@dataclass(frozen=True)
class DiskCondition:
    path: str
    threshold: str           # e.g. "1GB", "500MB"


@dataclass(frozen=True)
class CommandCondition:
    command: str
    expected_code: int


CheckCondition = Union[
    PortCondition, ServiceCondition, UrlCondition,
    FileExistsCondition, FileContainsCondition,
    DiskCondition, CommandCondition,
]


# ------------------------------------------------------------------
# Task action nodes
# ------------------------------------------------------------------

class ServiceAction(Enum):
    START = auto()
    STOP = auto()
    RESTART = auto()
    ENABLE = auto()
    DISABLE = auto()


@dataclass(frozen=True)
class InstallAction:
    packages: tuple[str, ...]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class RemoveAction:
    packages: tuple[str, ...]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class CopyAction:
    source: str
    destination: str
    notify: str | None = None
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class UploadAction:
    source: str
    destination: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class DownloadAction:
    source: str
    destination: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class RunAction:
    command: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class ServiceActionNode:
    action: ServiceAction
    service_name: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class EnsureAction:
    condition: CheckCondition
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class CheckAction:
    condition: CheckCondition
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class WaitAction:
    target_type: str         # "port" | "url" | "seconds"
    target_value: str | int
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class CreateUserAction:
    username: str
    home_dir: str | None = None
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class DeleteUserAction:
    username: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class CreateFileAction:
    path: str
    content: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class CreateDirectoryAction:
    path: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class SetPermissionsAction:
    permissions: str
    path: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class SetOwnerAction:
    owner: str
    path: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class TemplateAction:
    source: str
    destination: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class NotifyAction:
    """Wraps another action that triggers a handler on change."""
    action: TaskAction
    handler_name: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class SecurityScanAction:
    """Security scanning action with configurable parameters."""
    params: dict[str, Any]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class NetworkAction:
    """Network segmentation and management action."""
    params: dict[str, Any]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class AgentAction:
    """Network agent deployment and management action."""
    params: dict[str, Any]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class PolicyAction:
    """Policy engine action for template-based segmentation."""
    params: dict[str, Any]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class AppDependencyAction:
    """Application dependency mapping action."""
    params: dict[str, Any]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class FlowAnalysisAction:
    """Traffic flow analysis action."""
    params: dict[str, Any]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


# ------------------------------------------------------------------
# Control flow
# ------------------------------------------------------------------

@dataclass(frozen=True)
class SimpleCondition:
    """e.g. `os is "ubuntu"`, `arch is not "arm64"`"""
    left: str
    operator: str            # "is" | "is_not" | "contains" | ">" | "<"
    right: Value
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class FileExistsCheck:
    path: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class CommandSucceedsCheck:
    command: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


ConditionExpr = Union[SimpleCondition, FileExistsCheck, CommandSucceedsCheck]


@dataclass(frozen=True)
class IfBlock:
    condition: ConditionExpr
    body: tuple[TaskAction, ...]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class UnlessBlock:
    condition: ConditionExpr
    body: tuple[TaskAction, ...]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class ForBlock:
    variable: str
    iterable: str            # Name of the list variable
    body: tuple[TaskAction, ...]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


# Union of all task actions
TaskAction = Union[
    InstallAction, RemoveAction, CopyAction, UploadAction,
    DownloadAction, RunAction, ServiceActionNode, EnsureAction,
    CheckAction, WaitAction, CreateUserAction, DeleteUserAction,
    CreateFileAction, CreateDirectoryAction, SetPermissionsAction,
    SetOwnerAction, TemplateAction, NotifyAction, SecurityScanAction,
    NetworkAction, AgentAction, PolicyAction, AppDependencyAction,
    FlowAnalysisAction,
    IfBlock, UnlessBlock, ForBlock,
]


# ------------------------------------------------------------------
# Task, Handler, Plan
# ------------------------------------------------------------------

@dataclass(frozen=True)
class TaskDecl:
    name: str
    target: str              # server name, group name, or "local"
    actions: tuple[TaskAction, ...]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class HandlerDecl:
    name: str
    actions: tuple[TaskAction, ...]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class PlanStep:
    task_name: str
    condition: ConditionExpr | None = None


@dataclass(frozen=True)
class PlanDecl:
    name: str
    steps: tuple[PlanStep, ...]
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


@dataclass(frozen=True)
class ImportDecl:
    path: str
    loc: SourceLocation = field(default_factory=lambda: _DEFAULT_LOC)


# ------------------------------------------------------------------
# Root document
# ------------------------------------------------------------------

@dataclass(frozen=True)
class Document:
    variables: tuple[SetVariable, ...] = ()
    secrets: tuple[SecretDecl, ...] = ()
    servers: tuple[ServerDecl, ...] = ()
    groups: tuple[GroupDecl, ...] = ()
    dockers: tuple[DockerDecl, ...] = ()
    clouds: tuple[CloudDecl, ...] = ()
    tasks: tuple[TaskDecl, ...] = ()
    handlers: tuple[HandlerDecl, ...] = ()
    plans: tuple[PlanDecl, ...] = ()
    imports: tuple[ImportDecl, ...] = ()
