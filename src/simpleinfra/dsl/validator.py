"""Semantic validator for the SimpleInfra AST.

Checks for:
- Undefined server/group references in tasks
- Duplicate names
- Missing required properties
- Invalid target references
"""

from ..ast.nodes import Document, TaskDecl, PlanDecl, GroupDecl
from ..errors.parse_errors import ValidationError


def validate(document: Document, filename: str = "<stdin>") -> None:
    """Validate a parsed Document for semantic correctness.

    Raises:
        ValidationError: If any semantic errors are found.
    """
    errors: list[str] = []

    # Collect all known names
    server_names = {s.name for s in document.servers}
    group_names = {g.name for g in document.groups}
    docker_names = {d.name for d in document.dockers}
    cloud_names = {c.name for c in document.clouds}
    task_names = {t.name for t in document.tasks}
    handler_names = {h.name for h in document.handlers}
    variable_names = {v.name for v in document.variables}
    secret_names = {s.name for s in document.secrets}

    all_target_names = server_names | group_names | docker_names | cloud_names | {"local"}

    # Check for duplicate server names
    _check_duplicates(document.servers, "server", errors, filename)
    _check_duplicates(document.groups, "group", errors, filename)
    _check_duplicates(document.tasks, "task", errors, filename)
    _check_duplicates(document.handlers, "handler", errors, filename)

    # Validate task target references
    for task in document.tasks:
        if task.target not in all_target_names:
            errors.append(
                f"{filename}:{task.loc.line}: Task '{task.name}' references "
                f"undefined target '{task.target}'. "
                f"Available targets: {', '.join(sorted(all_target_names - {'local'}))}"
            )

    # Validate group member references
    for group in document.groups:
        for member in group.members:
            if member.kind == "server" and member.name not in server_names:
                errors.append(
                    f"{filename}:{group.loc.line}: Group '{group.name}' references "
                    f"undefined server '{member.name}'"
                )
            elif member.kind == "group" and member.name not in group_names:
                errors.append(
                    f"{filename}:{group.loc.line}: Group '{group.name}' references "
                    f"undefined group '{member.name}'"
                )

    # Validate plan task references
    for plan in document.plans:
        for step in plan.steps:
            if step.task_name not in task_names:
                errors.append(
                    f"{filename}:{plan.loc.line}: Plan '{plan.name}' references "
                    f"undefined task '{step.task_name}'"
                )

    # Validate server password secret references
    for server in document.servers:
        if server.password_secret and server.password_secret not in secret_names:
            errors.append(
                f"{filename}:{server.loc.line}: Server '{server.name}' references "
                f"undefined secret '{server.password_secret}'"
            )

    # Validate required server properties
    for server in document.servers:
        if not server.host:
            errors.append(
                f"{filename}:{server.loc.line}: Server '{server.name}' is missing "
                f"required 'host' property"
            )

    if errors:
        raise ValidationError("\n".join(errors), filename=filename)


def _check_duplicates(items: tuple, kind: str, errors: list[str], filename: str) -> None:
    """Check for duplicate names in a collection."""
    seen: set[str] = set()
    for item in items:
        if item.name in seen:
            errors.append(
                f"{filename}:{item.loc.line}: Duplicate {kind} name '{item.name}'"
            )
        seen.add(item.name)
