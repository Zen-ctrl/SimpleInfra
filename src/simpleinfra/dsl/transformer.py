"""Lark Transformer that converts parse trees into typed AST nodes.

Each method corresponds to a grammar rule and returns the appropriate
AST node from simpleinfra.ast.nodes.
"""

from __future__ import annotations

from lark import Transformer, v_args, Token, Tree

from ..ast.nodes import (
    AgentAction,
    AppDependencyAction,
    BooleanValue,
    CheckAction,
    CheckCondition,
    CloudDecl,
    CommandCondition,
    CommandSucceedsCheck,
    CopyAction,
    CreateDirectoryAction,
    CreateFileAction,
    CreateUserAction,
    DeleteUserAction,
    DiskCondition,
    DockerDecl,
    Document,
    DownloadAction,
    EnsureAction,
    FileContainsCondition,
    FileExistsCheck,
    FileExistsCondition,
    FlowAnalysisAction,
    NetworkAction,
    PolicyAction,
    SecurityScanAction,
    ForBlock,
    GroupDecl,
    GroupMember,
    HandlerDecl,
    IfBlock,
    ImportDecl,
    InstallAction,
    ListValue,
    NotifyAction,
    NumberValue,
    PlanDecl,
    PlanStep,
    PortCondition,
    RemoveAction,
    RunAction,
    SecretDecl,
    ServerDecl,
    ServiceAction,
    ServiceActionNode,
    ServiceCondition,
    SetOwnerAction,
    SetPermissionsAction,
    SetVariable,
    SimpleCondition,
    SourceLocation,
    StringValue,
    TaskDecl,
    TemplateAction,
    UnlessBlock,
    UploadAction,
    UrlCondition,
    VariableRef,
    WaitAction,
)


def _unquote(s: str) -> str:
    """Strip surrounding double quotes from a string token."""
    if isinstance(s, Token):
        s = str(s)
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s


class SimpleInfraTransformer(Transformer):
    """Transforms a Lark parse tree into SimpleInfra AST nodes."""

    def __init__(self, filename: str = "<stdin>") -> None:
        super().__init__()
        self.filename = filename

    def _loc(self, meta) -> SourceLocation:
        line = getattr(meta, "line", 0)
        column = getattr(meta, "column", 0)
        return SourceLocation(self.filename, line, column)

    # -------------------------------------------------------
    # Values
    # -------------------------------------------------------

    def string_value(self, args):
        return StringValue(_unquote(args[0]))

    def number_value(self, args):
        return NumberValue(int(args[0]))

    def boolean_value(self, args):
        return BooleanValue(str(args[0]) == "true")

    def identifier_value(self, args):
        return VariableRef(str(args[0]))

    def list_value(self, args):
        return ListValue(tuple(args))

    # -------------------------------------------------------
    # Set / Secret
    # -------------------------------------------------------

    @v_args(meta=True)
    def set_stmt(self, meta, args):
        return SetVariable(name=str(args[0]), value=args[1], loc=self._loc(meta))

    def secret_env(self, args):
        return ("env", _unquote(args[0]))

    def secret_file(self, args):
        return ("file", _unquote(args[0]))

    @v_args(meta=True)
    def secret_stmt(self, meta, args):
        name = str(args[0])
        source_type, source_value = args[1]
        return SecretDecl(name=name, source_type=source_type, source_value=source_value, loc=self._loc(meta))

    # -------------------------------------------------------
    # Server Block
    # -------------------------------------------------------

    def server_host(self, args):
        return ("host", _unquote(args[0]))

    def server_user(self, args):
        return ("user", _unquote(args[0]))

    def server_key(self, args):
        return ("key", _unquote(args[0]))

    def server_password(self, args):
        return ("password_secret", str(args[0]))

    def server_port(self, args):
        return ("port", int(args[0]))

    @v_args(meta=True)
    def server_block(self, meta, args):
        name = str(args[0])
        props = {k: v for k, v in args[1:]}
        return ServerDecl(
            name=name,
            host=props.get("host", ""),
            user=props.get("user", "root"),
            key=props.get("key"),
            password_secret=props.get("password_secret"),
            port=props.get("port", 22),
            loc=self._loc(meta),
        )

    # -------------------------------------------------------
    # Group Block
    # -------------------------------------------------------

    def group_server(self, args):
        return GroupMember(kind="server", name=str(args[0]))

    def group_group(self, args):
        return GroupMember(kind="group", name=str(args[0]))

    @v_args(meta=True)
    def group_block(self, meta, args):
        name = str(args[0])
        members = tuple(a for a in args[1:] if isinstance(a, GroupMember))
        return GroupDecl(name=name, members=members, loc=self._loc(meta))

    # -------------------------------------------------------
    # Docker Block
    # -------------------------------------------------------

    def docker_name(self, args):
        return ("container_name", _unquote(args[0]))

    def docker_image(self, args):
        return ("image", _unquote(args[0]))

    def docker_network(self, args):
        return ("network", _unquote(args[0]))

    @v_args(meta=True)
    def docker_block(self, meta, args):
        name = str(args[0])
        props = {k: v for k, v in args[1:]}
        return DockerDecl(
            name=name,
            container_name=props.get("container_name", name),
            image=props.get("image", ""),
            network=props.get("network"),
            loc=self._loc(meta),
        )

    # -------------------------------------------------------
    # Cloud Block
    # -------------------------------------------------------

    def cloud_provider(self, args):
        return ("provider", str(args[0]))

    def cloud_region(self, args):
        return ("region", _unquote(args[0]))

    def cloud_profile(self, args):
        return ("profile", _unquote(args[0]))

    def cloud_credentials(self, args):
        return ("credentials", _unquote(args[0]))

    @v_args(meta=True)
    def cloud_block(self, meta, args):
        name = str(args[0])
        props = {k: v for k, v in args[1:]}
        return CloudDecl(
            name=name,
            provider=props.get("provider", ""),
            region=props.get("region", ""),
            profile=props.get("profile"),
            credentials=props.get("credentials"),
            loc=self._loc(meta),
        )

    # -------------------------------------------------------
    # Task Block
    # -------------------------------------------------------

    def target_local(self, args):
        return "local"

    def target_named(self, args):
        return str(args[0])

    @v_args(meta=True)
    def task_block(self, meta, args):
        name = _unquote(args[0])
        target = args[1]
        actions = tuple(args[2:])
        return TaskDecl(name=name, target=target, actions=actions, loc=self._loc(meta))

    # -------------------------------------------------------
    # Package actions
    # -------------------------------------------------------

    def package_list(self, args):
        return tuple(str(a) for a in args)

    @v_args(meta=True)
    def install_stmt(self, meta, args):
        packages = args[0] if isinstance(args[0], tuple) else (str(args[0]),)
        return InstallAction(packages=packages, loc=self._loc(meta))

    @v_args(meta=True)
    def remove_stmt(self, meta, args):
        packages = args[0] if isinstance(args[0], tuple) else (str(args[0]),)
        return RemoveAction(packages=packages, loc=self._loc(meta))

    # -------------------------------------------------------
    # File operations
    # -------------------------------------------------------

    @v_args(meta=True)
    def copy_stmt(self, meta, args):
        return CopyAction(source=_unquote(args[0]), destination=_unquote(args[1]), loc=self._loc(meta))

    @v_args(meta=True)
    def upload_stmt(self, meta, args):
        return UploadAction(source=_unquote(args[0]), destination=_unquote(args[1]), loc=self._loc(meta))

    @v_args(meta=True)
    def download_stmt(self, meta, args):
        return DownloadAction(source=_unquote(args[0]), destination=_unquote(args[1]), loc=self._loc(meta))

    @v_args(meta=True)
    def template_stmt(self, meta, args):
        return TemplateAction(source=_unquote(args[0]), destination=_unquote(args[1]), loc=self._loc(meta))

    # -------------------------------------------------------
    # Commands
    # -------------------------------------------------------

    @v_args(meta=True)
    def run_stmt(self, meta, args):
        return RunAction(command=_unquote(args[0]), loc=self._loc(meta))

    # -------------------------------------------------------
    # Services
    # -------------------------------------------------------

    def action_start(self, args):
        return ServiceAction.START

    def action_stop(self, args):
        return ServiceAction.STOP

    def action_restart(self, args):
        return ServiceAction.RESTART

    def action_enable(self, args):
        return ServiceAction.ENABLE

    def action_disable(self, args):
        return ServiceAction.DISABLE

    @v_args(meta=True)
    def service_stmt(self, meta, args):
        action = args[0]
        service_name = str(args[1])
        return ServiceActionNode(action=action, service_name=service_name, loc=self._loc(meta))

    # -------------------------------------------------------
    # Ensure / Check conditions
    # -------------------------------------------------------

    def port_open(self, args):
        return PortCondition(port=args[0], state="open")

    def port_closed(self, args):
        return PortCondition(port=args[0], state="closed")

    def service_running(self, args):
        return ServiceCondition(service_name=str(args[0]), state="running")

    def service_stopped(self, args):
        return ServiceCondition(service_name=str(args[0]), state="stopped")

    def file_exists(self, args):
        return FileExistsCondition(path=_unquote(args[0]))

    def dir_exists(self, args):
        return FileExistsCondition(path=_unquote(args[0]))

    def user_exists(self, args):
        # Reuse FileExistsCondition pattern for simplicity -- checked differently in module
        return ServiceCondition(service_name=str(args[0]), state="exists")

    def url_returns(self, args):
        return UrlCondition(url=_unquote(args[0]), expected_status=int(args[1]))

    def file_contains(self, args):
        return FileContainsCondition(path=_unquote(args[0]), content=_unquote(args[1]))

    def disk_free(self, args):
        return DiskCondition(path=_unquote(args[0]), threshold=str(args[1]))

    def command_returns(self, args):
        return CommandCondition(command=_unquote(args[0]), expected_code=int(args[1]))

    @v_args(meta=True)
    def ensure_stmt(self, meta, args):
        return EnsureAction(condition=args[0], loc=self._loc(meta))

    @v_args(meta=True)
    def check_stmt(self, meta, args):
        return CheckAction(condition=args[0], loc=self._loc(meta))

    # -------------------------------------------------------
    # Wait
    # -------------------------------------------------------

    def wait_port(self, args):
        return ("port", args[0])

    def wait_url(self, args):
        return ("url", _unquote(args[0]))

    def wait_seconds(self, args):
        return ("seconds", int(args[0]))

    @v_args(meta=True)
    def wait_stmt(self, meta, args):
        target_type, target_value = args[0]
        return WaitAction(target_type=target_type, target_value=target_value, loc=self._loc(meta))

    # -------------------------------------------------------
    # User Management
    # -------------------------------------------------------

    @v_args(meta=True)
    def create_user_stmt(self, meta, args):
        return CreateUserAction(username=str(args[0]), loc=self._loc(meta))

    @v_args(meta=True)
    def create_user_home(self, meta, args):
        return CreateUserAction(username=str(args[0]), home_dir=_unquote(args[1]), loc=self._loc(meta))

    @v_args(meta=True)
    def delete_user_stmt(self, meta, args):
        return DeleteUserAction(username=str(args[0]), loc=self._loc(meta))

    # -------------------------------------------------------
    # File/Directory Management
    # -------------------------------------------------------

    @v_args(meta=True)
    def create_file_stmt(self, meta, args):
        return CreateFileAction(path=_unquote(args[0]), content=_unquote(args[1]), loc=self._loc(meta))

    @v_args(meta=True)
    def create_dir_stmt(self, meta, args):
        return CreateDirectoryAction(path=_unquote(args[0]), loc=self._loc(meta))

    @v_args(meta=True)
    def set_perms_stmt(self, meta, args):
        return SetPermissionsAction(permissions=_unquote(args[0]), path=_unquote(args[1]), loc=self._loc(meta))

    @v_args(meta=True)
    def set_owner_stmt(self, meta, args):
        return SetOwnerAction(owner=str(args[0]), path=_unquote(args[1]), loc=self._loc(meta))

    # -------------------------------------------------------
    # Notify
    # -------------------------------------------------------

    @v_args(meta=True)
    def notify_stmt(self, meta, args):
        # Standalone notify -- stored as a simple marker
        return NotifyAction(
            action=RunAction(command="", loc=self._loc(meta)),
            handler_name=_unquote(args[0]),
            loc=self._loc(meta),
        )

    # -------------------------------------------------------
    # Security Scanning
    # -------------------------------------------------------

    def module_params(self, args):
        """Parse inline module parameters like: type="vulnerability" target="filesystem" """
        params = {}
        i = 0
        while i < len(args):
            if i + 1 < len(args):
                key = str(args[i])
                value = _unquote(args[i + 1]) if isinstance(args[i + 1], str) else str(args[i + 1])
                params[key] = value
                i += 2
            else:
                i += 1
        return params

    def module_param(self, args):
        """Parse block-style module parameter like: type "vulnerability" """
        key = str(args[0])
        # Value is already converted to StringValue, NumberValue, etc. by the value rules
        value_node = args[1]
        # Extract the actual value
        if hasattr(value_node, 'value'):
            value = value_node.value
        else:
            value = str(value_node)
        return (key, value)

    @v_args(meta=True)
    def security_scan_stmt(self, meta, args):
        """Transform security scan statement to SecurityScanAction."""
        params = {}
        for arg in args:
            if isinstance(arg, dict):
                params.update(arg)
            elif isinstance(arg, tuple) and len(arg) == 2:
                params[arg[0]] = arg[1]
        return SecurityScanAction(params=params, loc=self._loc(meta))

    @v_args(meta=True)
    def network_stmt(self, meta, args):
        """Transform network statement to NetworkAction."""
        params = {}
        for arg in args:
            if isinstance(arg, dict):
                params.update(arg)
            elif isinstance(arg, tuple) and len(arg) == 2:
                params[arg[0]] = arg[1]
        return NetworkAction(params=params, loc=self._loc(meta))

    @v_args(meta=True)
    def agent_stmt(self, meta, args):
        """Transform agent statement to AgentAction."""
        params = {}
        for arg in args:
            if isinstance(arg, dict):
                params.update(arg)
            elif isinstance(arg, tuple) and len(arg) == 2:
                params[arg[0]] = arg[1]
        return AgentAction(params=params, loc=self._loc(meta))

    @v_args(meta=True)
    def policy_stmt(self, meta, args):
        """Transform policy statement to PolicyAction."""
        params = {}
        for arg in args:
            if isinstance(arg, dict):
                params.update(arg)
            elif isinstance(arg, tuple) and len(arg) == 2:
                params[arg[0]] = arg[1]
        return PolicyAction(params=params, loc=self._loc(meta))

    @v_args(meta=True)
    def appdep_stmt(self, meta, args):
        """Transform appdep statement to AppDependencyAction."""
        params = {}
        for arg in args:
            if isinstance(arg, dict):
                params.update(arg)
            elif isinstance(arg, tuple) and len(arg) == 2:
                params[arg[0]] = arg[1]
        return AppDependencyAction(params=params, loc=self._loc(meta))

    @v_args(meta=True)
    def flowanalysis_stmt(self, meta, args):
        """Transform flowanalysis statement to FlowAnalysisAction."""
        params = {}
        for arg in args:
            if isinstance(arg, dict):
                params.update(arg)
            elif isinstance(arg, tuple) and len(arg) == 2:
                params[arg[0]] = arg[1]
        return FlowAnalysisAction(params=params, loc=self._loc(meta))

    # -------------------------------------------------------
    # Control Flow
    # -------------------------------------------------------

    def cond_is(self, args):
        return SimpleCondition(left=str(args[0]), operator="is", right=args[1])

    def cond_is_not(self, args):
        return SimpleCondition(left=str(args[0]), operator="is_not", right=args[1])

    def cond_contains(self, args):
        return SimpleCondition(left=str(args[0]), operator="contains", right=args[1])

    def cond_gt(self, args):
        return SimpleCondition(left=str(args[0]), operator=">", right=args[1])

    def cond_lt(self, args):
        return SimpleCondition(left=str(args[0]), operator="<", right=args[1])

    def cond_file_exists(self, args):
        return FileExistsCheck(path=_unquote(args[0]))

    def cond_command_succeeds(self, args):
        return CommandSucceedsCheck(command=_unquote(args[0]))

    @v_args(meta=True)
    def if_block(self, meta, args):
        condition = args[0]
        body = tuple(args[1:])
        return IfBlock(condition=condition, body=body, loc=self._loc(meta))

    @v_args(meta=True)
    def unless_block(self, meta, args):
        condition = args[0]
        body = tuple(args[1:])
        return UnlessBlock(condition=condition, body=body, loc=self._loc(meta))

    @v_args(meta=True)
    def for_block(self, meta, args):
        variable = str(args[0])
        iterable = str(args[1])
        body = tuple(args[2:])
        return ForBlock(variable=variable, iterable=iterable, body=body, loc=self._loc(meta))

    # -------------------------------------------------------
    # Handler Block
    # -------------------------------------------------------

    @v_args(meta=True)
    def handler_block(self, meta, args):
        name = _unquote(args[0])
        actions = tuple(args[1:])
        return HandlerDecl(name=name, actions=actions, loc=self._loc(meta))

    # -------------------------------------------------------
    # Plan Block
    # -------------------------------------------------------

    def plan_run(self, args):
        return PlanStep(task_name=_unquote(args[0]))

    def plan_run_if(self, args):
        return PlanStep(task_name=_unquote(args[0]), condition=args[1])

    @v_args(meta=True)
    def plan_block(self, meta, args):
        name = _unquote(args[0])
        steps = tuple(a for a in args[1:] if isinstance(a, PlanStep))
        return PlanDecl(name=name, steps=steps, loc=self._loc(meta))

    # -------------------------------------------------------
    # Import
    # -------------------------------------------------------

    @v_args(meta=True)
    def import_stmt(self, meta, args):
        return ImportDecl(path=_unquote(args[0]), loc=self._loc(meta))

    # -------------------------------------------------------
    # Root
    # -------------------------------------------------------

    def start(self, args):
        # Filter out None values (from empty lines / comments)
        stmts = [a for a in args if a is not None]
        return Document(
            variables=tuple(s for s in stmts if isinstance(s, SetVariable)),
            secrets=tuple(s for s in stmts if isinstance(s, SecretDecl)),
            servers=tuple(s for s in stmts if isinstance(s, ServerDecl)),
            groups=tuple(s for s in stmts if isinstance(s, GroupDecl)),
            dockers=tuple(s for s in stmts if isinstance(s, DockerDecl)),
            clouds=tuple(s for s in stmts if isinstance(s, CloudDecl)),
            tasks=tuple(s for s in stmts if isinstance(s, TaskDecl)),
            handlers=tuple(s for s in stmts if isinstance(s, HandlerDecl)),
            plans=tuple(s for s in stmts if isinstance(s, PlanDecl)),
            imports=tuple(s for s in stmts if isinstance(s, ImportDecl)),
        )
