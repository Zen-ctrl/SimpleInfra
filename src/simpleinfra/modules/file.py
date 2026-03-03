"""File module for SimpleInfra.

Handles file operations: copy, upload, download, template,
create file, create directory, set permissions, set owner.
Uses hash comparison for idempotency.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .base import Module, ModuleResult

if TYPE_CHECKING:
    from ..connectors.base import Connector
    from ..engine.context import ExecutionContext


class FileModule(Module):
    """Handles all file-related operations."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action")
        if action is None:
            return ModuleResult(changed=False, success=False, message="No action provided")

        from ..ast.nodes import (
            CopyAction, UploadAction, DownloadAction, TemplateAction,
            CreateFileAction, CreateDirectoryAction, SetPermissionsAction, SetOwnerAction,
        )

        if isinstance(action, (CopyAction, UploadAction)):
            return await self._upload(connector, context, action.source, action.destination)
        elif isinstance(action, DownloadAction):
            return await self._download(connector, context, action.source, action.destination)
        elif isinstance(action, TemplateAction):
            return await self._template(connector, context, action.source, action.destination)
        elif isinstance(action, CreateFileAction):
            return await self._create_file(connector, context, action.path, action.content)
        elif isinstance(action, CreateDirectoryAction):
            return await self._create_directory(connector, context, action.path)
        elif isinstance(action, SetPermissionsAction):
            return await self._set_permissions(connector, action.permissions, action.path)
        elif isinstance(action, SetOwnerAction):
            return await self._set_owner(connector, action.owner, action.path)
        else:
            return ModuleResult(changed=False, success=False, message=f"Unknown action: {type(action)}")

    async def _upload(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        source: str,
        destination: str,
    ) -> ModuleResult:
        source = context.resolver.resolve(source)
        destination = context.resolver.resolve(destination)

        local_path = Path(source)
        if not local_path.exists():
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Source file not found: {source}",
            )

        # Check if destination already has same content (idempotency)
        local_hash = hashlib.sha256(local_path.read_bytes()).hexdigest()
        remote_hash = await connector.get_file_hash(destination)

        if local_hash == remote_hash:
            return ModuleResult(
                changed=False,
                success=True,
                message=f"File unchanged: {destination}",
            )

        try:
            await connector.upload_file(source, destination)
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Copied {source} -> {destination}",
            )
        except Exception as e:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to copy {source} -> {destination}: {e}",
            )

    async def _download(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        source: str,
        destination: str,
    ) -> ModuleResult:
        source = context.resolver.resolve(source)
        destination = context.resolver.resolve(destination)

        try:
            await connector.download_file(source, destination)
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Downloaded {source} -> {destination}",
            )
        except Exception as e:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to download {source}: {e}",
            )

    async def _template(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        source: str,
        destination: str,
    ) -> ModuleResult:
        source = context.resolver.resolve(source)
        destination = context.resolver.resolve(destination)

        local_path = Path(source)
        if not local_path.exists():
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Template file not found: {source}",
            )

        # Read template, resolve variables, write to destination
        template_content = local_path.read_text(encoding="utf-8")
        rendered = context.resolver.resolve(template_content)

        # Check if destination already has same content
        rendered_hash = hashlib.sha256(rendered.encode()).hexdigest()
        remote_hash = await connector.get_file_hash(destination)

        if rendered_hash == remote_hash:
            return ModuleResult(
                changed=False,
                success=True,
                message=f"Template unchanged: {destination}",
            )

        try:
            await connector.write_file(destination, rendered)
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Rendered template {source} -> {destination}",
            )
        except Exception as e:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to render template: {e}",
            )

    async def _create_file(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        path: str,
        content: str,
    ) -> ModuleResult:
        path = context.resolver.resolve(path)
        content = context.resolver.resolve(content)

        try:
            await connector.write_file(path, content)
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Created file: {path}",
            )
        except Exception as e:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to create file {path}: {e}",
            )

    async def _create_directory(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        path: str,
    ) -> ModuleResult:
        path = context.resolver.resolve(path)

        exists = await connector.file_exists(path)
        if exists:
            return ModuleResult(
                changed=False,
                success=True,
                message=f"Directory already exists: {path}",
            )

        result = await connector.run_command(f"mkdir -p {path}", sudo=True)
        if result.success:
            return ModuleResult(changed=True, success=True, message=f"Created directory: {path}")
        else:
            return ModuleResult(changed=False, success=False, message=f"Failed to create directory: {path}")

    async def _set_permissions(
        self,
        connector: "Connector",
        permissions: str,
        path: str,
    ) -> ModuleResult:
        result = await connector.run_command(f"chmod {permissions} {path}", sudo=True)
        if result.success:
            return ModuleResult(changed=True, success=True, message=f"Set permissions {permissions} on {path}")
        return ModuleResult(changed=False, success=False, message=f"Failed to set permissions on {path}")

    async def _set_owner(
        self,
        connector: "Connector",
        owner: str,
        path: str,
    ) -> ModuleResult:
        result = await connector.run_command(f"chown {owner} {path}", sudo=True)
        if result.success:
            return ModuleResult(changed=True, success=True, message=f"Set owner {owner} on {path}")
        return ModuleResult(changed=False, success=False, message=f"Failed to set owner on {path}")
