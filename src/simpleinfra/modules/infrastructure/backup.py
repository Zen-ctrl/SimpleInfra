"""Backup and recovery module.

Provides:
- Automated file system backups
- S3/cloud storage synchronization
- Database backup integration
- Incremental backups
- Backup verification
- Restore procedures
- Retention policies
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class BackupModule(Module):
    """Backup and recovery management."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "create_job")

        if action == "create_job":
            return await self._create_backup_job(connector, kwargs)
        elif action == "backup_now":
            return await self._backup_now(connector, kwargs)
        elif action == "sync_to_s3":
            return await self._sync_to_s3(connector, kwargs)
        elif action == "restore":
            return await self._restore(connector, kwargs)
        elif action == "list_backups":
            return await self._list_backups(connector, kwargs)
        elif action == "verify":
            return await self._verify_backup(connector, kwargs)
        elif action == "cleanup":
            return await self._cleanup_old_backups(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown backup action: {action}",
            )

    async def _create_backup_job(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Create automated backup job."""
        name = params.get("name", "backup")
        source = params.get("source", "/var/www")
        destination = params.get("destination", "/var/backups")
        schedule = params.get("schedule", "0 2 * * *")  # Cron format
        retention = params.get("retention", "30")
        compression = params.get("compression", "true") == "true"
        encryption = params.get("encryption", "false") == "true"
        incremental = params.get("incremental", "false") == "true"

        # Create backup script
        backup_script = f"""#!/bin/bash
# SimpleInfra Backup Job: {name}
set -e

SOURCE="{source}"
DEST="{destination}"
RETENTION_DAYS={retention}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="{name}_$TIMESTAMP"
BACKUP_PATH="$DEST/$BACKUP_NAME"

# Create destination directory
mkdir -p "$DEST"

echo "Starting backup: $BACKUP_NAME"
"""

        if incremental:
            backup_script += f"""
# Incremental backup using rsync
rsync -av --delete --link-dest="$DEST/{name}_latest" "$SOURCE/" "$BACKUP_PATH/"
ln -snf "$BACKUP_NAME" "$DEST/{name}_latest"
"""
        else:
            backup_script += """
# Full backup
cp -r "$SOURCE" "$BACKUP_PATH"
"""

        if compression:
            backup_script += """
# Compress backup
tar -czf "$BACKUP_PATH.tar.gz" -C "$DEST" "$BACKUP_NAME"
rm -rf "$BACKUP_PATH"
BACKUP_PATH="$BACKUP_PATH.tar.gz"
"""

        if encryption:
            backup_script += """
# Encrypt backup (requires gpg key setup)
gpg --encrypt --recipient backup@localhost "$BACKUP_PATH"
rm "$BACKUP_PATH"
BACKUP_PATH="$BACKUP_PATH.gpg"
"""

        backup_script += f"""
# Clean up old backups
find "$DEST" -name "{name}_*" -mtime +$RETENTION_DAYS -delete

# Log completion
echo "Backup completed: $BACKUP_PATH"
echo "$(date): Backup $BACKUP_NAME completed" >> /var/log/simpleinfra-backup.log
"""

        # Write backup script
        script_path = f"/usr/local/bin/backup-{name}.sh"
        await connector.run_command(
            f"cat > {script_path} << 'EOL'\n{backup_script}\nEOL",
            sudo=True,
        )
        await connector.run_command(f"chmod +x {script_path}", sudo=True)

        # Create cron job
        cron_entry = f"{schedule} root {script_path} >> /var/log/backup-{name}.log 2>&1"
        await connector.run_command(
            f"echo '{cron_entry}' > /etc/cron.d/backup-{name}",
            sudo=True,
        )

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Backup job '{name}' created",
            details={
                "name": name,
                "source": source,
                "destination": destination,
                "schedule": schedule,
                "retention": retention,
                "compression": compression,
                "encryption": encryption,
                "incremental": incremental,
                "script": script_path,
            },
        )

    async def _backup_now(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Perform immediate backup."""
        source = params.get("source", "/var/www")
        destination = params.get("destination", "/var/backups")
        compression = params.get("compression", "true") == "true"

        timestamp = "$(date +%Y%m%d_%H%M%S)"
        backup_name = f"backup_{timestamp}"

        if compression:
            cmd = f"tar -czf {destination}/{backup_name}.tar.gz {source}"
        else:
            cmd = f"cp -r {source} {destination}/{backup_name}"

        result = await connector.run_command(cmd, sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Backup created: {destination}/{backup_name}",
                details={"path": f"{destination}/{backup_name}"},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Backup failed",
                details={"error": result.stderr},
            )

    async def _sync_to_s3(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Sync backups to S3."""
        source = params.get("source", "/var/backups")
        bucket = params.get("bucket", "")
        prefix = params.get("prefix", "backups/")
        storage_class = params.get("storage_class", "STANDARD_IA")
        delete = params.get("delete", "false") == "true"

        if not bucket:
            return ModuleResult(
                changed=False,
                success=False,
                message="S3 bucket is required",
            )

        # Install AWS CLI if not present
        check_result = await connector.run_command("which aws")
        if not check_result.success:
            install_result = await connector.run_command(
                "apt-get update && apt-get install -y awscli",
                sudo=True,
            )
            if not install_result.success:
                return ModuleResult(
                    changed=False,
                    success=False,
                    message="Failed to install AWS CLI",
                    details={"error": install_result.stderr},
                )

        # Sync to S3
        delete_flag = "--delete" if delete else ""
        cmd = (
            f"aws s3 sync {source} s3://{bucket}/{prefix} "
            f"--storage-class {storage_class} {delete_flag}"
        )

        result = await connector.run_command(cmd, sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Backups synced to s3://{bucket}/{prefix}",
                details={
                    "bucket": bucket,
                    "prefix": prefix,
                    "storage_class": storage_class,
                },
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="S3 sync failed",
                details={"error": result.stderr},
            )

    async def _restore(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Restore from backup."""
        backup_path = params.get("backup_path", "")
        destination = params.get("destination", "")
        verify_first = params.get("verify_first", "true") == "true"

        if not backup_path or not destination:
            return ModuleResult(
                changed=False,
                success=False,
                message="Both backup_path and destination are required",
            )

        # Verify backup exists
        check_result = await connector.run_command(f"test -f {backup_path}", sudo=True)
        if not check_result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Backup file not found: {backup_path}",
            )

        # Determine if compressed/encrypted
        is_encrypted = backup_path.endswith(".gpg")
        is_compressed = backup_path.endswith(".tar.gz") or backup_path.endswith(".tgz")

        temp_path = backup_path

        # Decrypt if needed
        if is_encrypted:
            temp_path = backup_path[:-4]  # Remove .gpg
            decrypt_cmd = f"gpg --decrypt {backup_path} > {temp_path}"
            decrypt_result = await connector.run_command(decrypt_cmd, sudo=True)
            if not decrypt_result.success:
                return ModuleResult(
                    changed=False,
                    success=False,
                    message="Decryption failed",
                    details={"error": decrypt_result.stderr},
                )

        # Extract if compressed
        if is_compressed or temp_path.endswith(".tar.gz"):
            extract_cmd = f"tar -xzf {temp_path} -C {destination}"
            result = await connector.run_command(extract_cmd, sudo=True)
        else:
            # Direct copy
            result = await connector.run_command(f"cp -r {temp_path} {destination}", sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Backup restored to {destination}",
                details={"backup_path": backup_path, "destination": destination},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Restore failed",
                details={"error": result.stderr},
            )

    async def _list_backups(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """List available backups."""
        backup_dir = params.get("backup_dir", "/var/backups")
        pattern = params.get("pattern", "*")

        cmd = f"ls -lh {backup_dir}/{pattern} 2>/dev/null || echo 'No backups found'"
        result = await connector.run_command(cmd, sudo=True)

        return ModuleResult(
            changed=False,
            success=True,
            message="Backup list retrieved",
            details={"backups": result.stdout},
        )

    async def _verify_backup(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Verify backup integrity."""
        backup_path = params.get("backup_path", "")

        if not backup_path:
            return ModuleResult(
                changed=False,
                success=False,
                message="Backup path is required",
            )

        # Check if file exists
        exists_result = await connector.run_command(f"test -f {backup_path}", sudo=True)
        if not exists_result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Backup not found: {backup_path}",
            )

        # Verify based on file type
        if backup_path.endswith(".tar.gz") or backup_path.endswith(".tgz"):
            # Test tar archive
            verify_cmd = f"tar -tzf {backup_path} > /dev/null 2>&1"
            result = await connector.run_command(verify_cmd, sudo=True)

            if result.success:
                # Get file count
                count_cmd = f"tar -tzf {backup_path} | wc -l"
                count_result = await connector.run_command(count_cmd, sudo=True)

                return ModuleResult(
                    changed=False,
                    success=True,
                    message="Backup verified successfully",
                    details={
                        "backup_path": backup_path,
                        "file_count": count_result.stdout.strip(),
                        "status": "valid",
                    },
                )
            else:
                return ModuleResult(
                    changed=False,
                    success=False,
                    message="Backup verification failed",
                    details={"backup_path": backup_path, "status": "corrupted"},
                )

        # Get file size and modification time
        stat_cmd = f"stat -c '%s %y' {backup_path}"
        stat_result = await connector.run_command(stat_cmd, sudo=True)

        return ModuleResult(
            changed=False,
            success=True,
            message="Backup file exists",
            details={
                "backup_path": backup_path,
                "info": stat_result.stdout.strip(),
            },
        )

    async def _cleanup_old_backups(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Clean up old backups based on retention policy."""
        backup_dir = params.get("backup_dir", "/var/backups")
        retention_days = params.get("retention_days", "30")
        pattern = params.get("pattern", "backup_*")
        dry_run = params.get("dry_run", "false") == "true"

        # Find old backups
        find_cmd = f"find {backup_dir} -name '{pattern}' -mtime +{retention_days}"

        if dry_run:
            result = await connector.run_command(find_cmd, sudo=True)
            return ModuleResult(
                changed=False,
                success=True,
                message=f"Dry run: Found backups older than {retention_days} days",
                details={"files_to_delete": result.stdout},
            )
        else:
            # Delete old backups
            delete_cmd = f"{find_cmd} -delete"
            result = await connector.run_command(delete_cmd, sudo=True)

            if result.success:
                return ModuleResult(
                    changed=True,
                    success=True,
                    message=f"Cleaned up backups older than {retention_days} days",
                    details={"retention_days": retention_days},
                )
            else:
                return ModuleResult(
                    changed=False,
                    success=False,
                    message="Cleanup failed",
                    details={"error": result.stderr},
                )
