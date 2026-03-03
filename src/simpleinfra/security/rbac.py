"""Role-Based Access Control for SimpleInfra.

Defines who can do what on which targets.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class Permission(Enum):
    """Permission types."""
    READ = auto()           # View configuration, dry-run
    EXECUTE = auto()        # Run tasks on targets
    MANAGE_SECRETS = auto() # Access/modify secrets
    MANAGE_USERS = auto()   # Create/delete users
    ADMIN = auto()          # Full control


@dataclass
class Role:
    """A role with specific permissions."""
    name: str
    permissions: set[Permission]
    targets: set[str]  # Which servers/groups this role can access
    description: str = ""


class RBACManager:
    """Manages roles and permissions."""

    def __init__(self):
        self.roles: dict[str, Role] = {
            "admin": Role(
                name="admin",
                permissions={Permission.ADMIN, Permission.READ, Permission.EXECUTE,
                           Permission.MANAGE_SECRETS, Permission.MANAGE_USERS},
                targets={"*"},
                description="Full administrative access",
            ),
            "operator": Role(
                name="operator",
                permissions={Permission.READ, Permission.EXECUTE},
                targets={"*"},
                description="Can run tasks but not manage secrets",
            ),
            "readonly": Role(
                name="readonly",
                permissions={Permission.READ},
                targets={"*"},
                description="Read-only access, dry-run only",
            ),
        }
        self.user_roles: dict[str, set[str]] = {}

    def assign_role(self, user: str, role_name: str) -> None:
        """Assign a role to a user."""
        if role_name not in self.roles:
            raise ValueError(f"Role '{role_name}' does not exist")
        if user not in self.user_roles:
            self.user_roles[user] = set()
        self.user_roles[user].add(role_name)

    def has_permission(self, user: str, permission: Permission, target: str = "*") -> bool:
        """Check if user has a specific permission on a target."""
        if user not in self.user_roles:
            return False

        for role_name in self.user_roles[user]:
            role = self.roles.get(role_name)
            if not role:
                continue

            # Check if role has the permission
            if Permission.ADMIN in role.permissions or permission in role.permissions:
                # Check if role can access this target
                if "*" in role.targets or target in role.targets:
                    return True

        return False

    def create_role(
        self,
        name: str,
        permissions: set[Permission],
        targets: set[str],
        description: str = "",
    ) -> None:
        """Create a custom role."""
        self.roles[name] = Role(
            name=name,
            permissions=permissions,
            targets=targets,
            description=description,
        )


# Updated DSL syntax for RBAC:
# role "devops":
#     permissions: [execute, read]
#     targets: [web, db]
#
# role "security_team":
#     permissions: [manage_secrets, admin]
#     targets: [*]
