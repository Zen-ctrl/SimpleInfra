"""Database management module.

Provides:
- PostgreSQL installation and configuration
- MySQL/MariaDB setup
- MongoDB deployment
- Database and user management
- Automated backups
- Replication setup
- Performance tuning
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING
import json

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class DatabaseModule(Module):
    """Database installation, configuration, and management."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "install")

        if action == "install":
            return await self._install_database(connector, kwargs)
        elif action == "create_database":
            return await self._create_database(connector, kwargs)
        elif action == "create_user":
            return await self._create_user(connector, kwargs)
        elif action == "grant_privileges":
            return await self._grant_privileges(connector, kwargs)
        elif action == "configure_backup":
            return await self._configure_backup(connector, kwargs)
        elif action == "backup":
            return await self._backup(connector, kwargs)
        elif action == "restore":
            return await self._restore(connector, kwargs)
        elif action == "configure_replication":
            return await self._configure_replication(connector, kwargs)
        elif action == "tune_performance":
            return await self._tune_performance(connector, kwargs)
        elif action == "secure":
            return await self._secure_database(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown database action: {action}",
            )

    async def _install_database(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Install database server."""
        db_type = params.get("type", "postgresql")
        version = params.get("version", "15")

        if db_type == "postgresql":
            # Install PostgreSQL
            commands = [
                "apt-get update",
                f"apt-get install -y postgresql-{version} postgresql-contrib",
            ]

            for cmd in commands:
                result = await connector.run_command(cmd, sudo=True)
                if not result.success:
                    return ModuleResult(
                        changed=False,
                        success=False,
                        message=f"Failed to install PostgreSQL: {cmd}",
                        details={"error": result.stderr},
                    )

            # Start and enable
            await connector.run_command("systemctl start postgresql", sudo=True)
            await connector.run_command("systemctl enable postgresql", sudo=True)

            # Get version
            version_cmd = "su - postgres -c 'psql --version'"
            version_result = await connector.run_command(version_cmd, sudo=True)

            return ModuleResult(
                changed=True,
                success=True,
                message=f"PostgreSQL {version} installed",
                details={
                    "type": "postgresql",
                    "version": version_result.stdout.strip() if version_result.success else version,
                    "status": "running",
                },
            )

        elif db_type == "mysql":
            # Install MySQL
            install_cmd = "DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server"
            result = await connector.run_command(install_cmd, sudo=True)

            if result.success:
                await connector.run_command("systemctl start mysql", sudo=True)
                await connector.run_command("systemctl enable mysql", sudo=True)

                return ModuleResult(
                    changed=True,
                    success=True,
                    message="MySQL installed",
                    details={"type": "mysql", "status": "running"},
                )

        elif db_type == "mariadb":
            # Install MariaDB
            install_cmd = "apt-get install -y mariadb-server mariadb-client"
            result = await connector.run_command(install_cmd, sudo=True)

            if result.success:
                await connector.run_command("systemctl start mariadb", sudo=True)
                await connector.run_command("systemctl enable mariadb", sudo=True)

                return ModuleResult(
                    changed=True,
                    success=True,
                    message="MariaDB installed",
                    details={"type": "mariadb", "status": "running"},
                )

        elif db_type == "mongodb":
            # Install MongoDB
            commands = [
                "apt-get install -y gnupg curl",
                "curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor",
                'echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list',
                "apt-get update",
                "apt-get install -y mongodb-org",
            ]

            for cmd in commands:
                result = await connector.run_command(cmd, sudo=True)
                if not result.success:
                    return ModuleResult(
                        changed=False,
                        success=False,
                        message=f"Failed to install MongoDB: {cmd}",
                        details={"error": result.stderr},
                    )

            await connector.run_command("systemctl start mongod", sudo=True)
            await connector.run_command("systemctl enable mongod", sudo=True)

            return ModuleResult(
                changed=True,
                success=True,
                message="MongoDB installed",
                details={"type": "mongodb", "status": "running"},
            )

        return ModuleResult(
            changed=False,
            success=False,
            message=f"Unsupported database type: {db_type}",
        )

    async def _create_database(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Create a database."""
        db_type = params.get("type", "postgresql")
        name = params.get("name", "")
        owner = params.get("owner", "")
        encoding = params.get("encoding", "UTF8")

        if not name:
            return ModuleResult(
                changed=False,
                success=False,
                message="Database name is required",
            )

        if db_type == "postgresql":
            owner_clause = f"OWNER {owner}" if owner else ""
            cmd = f"su - postgres -c \"psql -c 'CREATE DATABASE {name} {owner_clause} ENCODING {encoding};'\""
            result = await connector.run_command(cmd, sudo=True)

            if result.success or "already exists" in result.stderr:
                return ModuleResult(
                    changed="already exists" not in result.stderr,
                    success=True,
                    message=f"Database '{name}' created" if "already exists" not in result.stderr else f"Database '{name}' already exists",
                    details={"name": name, "owner": owner, "encoding": encoding},
                )
            else:
                return ModuleResult(
                    changed=False,
                    success=False,
                    message=f"Failed to create database '{name}'",
                    details={"error": result.stderr},
                )

        elif db_type in ["mysql", "mariadb"]:
            cmd = f"mysql -e 'CREATE DATABASE IF NOT EXISTS {name};'"
            result = await connector.run_command(cmd, sudo=True)

            if result.success:
                return ModuleResult(
                    changed=True,
                    success=True,
                    message=f"Database '{name}' created",
                    details={"name": name},
                )

        elif db_type == "mongodb":
            # MongoDB creates databases on first use
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Database '{name}' will be created on first use",
                details={"name": name, "note": "MongoDB creates databases lazily"},
            )

        return ModuleResult(
            changed=False,
            success=False,
            message=f"Database creation not supported for {db_type}",
        )

    async def _create_user(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Create database user."""
        db_type = params.get("type", "postgresql")
        username = params.get("username", "")
        password = params.get("password", "")
        database = params.get("database", "")

        if not username or not password:
            return ModuleResult(
                changed=False,
                success=False,
                message="Username and password are required",
            )

        if db_type == "postgresql":
            cmd = f"su - postgres -c \"psql -c \\\"CREATE USER {username} WITH PASSWORD '{password}';\\\"\""
            result = await connector.run_command(cmd, sudo=True)

            if result.success or "already exists" in result.stderr:
                return ModuleResult(
                    changed="already exists" not in result.stderr,
                    success=True,
                    message=f"User '{username}' created",
                    details={"username": username},
                )

        elif db_type in ["mysql", "mariadb"]:
            cmd = f"mysql -e \"CREATE USER IF NOT EXISTS '{username}'@'localhost' IDENTIFIED BY '{password}';\""
            result = await connector.run_command(cmd, sudo=True)

            if result.success:
                return ModuleResult(
                    changed=True,
                    success=True,
                    message=f"MySQL user '{username}' created",
                )

        return ModuleResult(
            changed=False,
            success=False,
            message="Failed to create user",
        )

    async def _grant_privileges(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Grant database privileges to user."""
        db_type = params.get("type", "postgresql")
        username = params.get("username", "")
        database = params.get("database", "")
        privileges = params.get("privileges", "ALL")

        if db_type == "postgresql":
            cmd = f"su - postgres -c \"psql -c 'GRANT {privileges} PRIVILEGES ON DATABASE {database} TO {username};'\""
            result = await connector.run_command(cmd, sudo=True)

            if result.success:
                return ModuleResult(
                    changed=True,
                    success=True,
                    message=f"Privileges granted to {username} on {database}",
                )

        elif db_type in ["mysql", "mariadb"]:
            cmd = f"mysql -e \"GRANT {privileges} ON {database}.* TO '{username}'@'localhost'; FLUSH PRIVILEGES;\""
            result = await connector.run_command(cmd, sudo=True)

            if result.success:
                return ModuleResult(
                    changed=True,
                    success=True,
                    message=f"MySQL privileges granted",
                )

        return ModuleResult(
            changed=False,
            success=False,
            message="Failed to grant privileges",
        )

    async def _configure_backup(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Configure automated database backups."""
        db_type = params.get("type", "postgresql")
        schedule = params.get("schedule", "daily")
        retention = params.get("retention", "7")
        destination = params.get("destination", "/var/backups/db")

        # Create backup directory
        await connector.run_command(f"mkdir -p {destination}", sudo=True)

        # Create backup script
        if db_type == "postgresql":
            backup_script = f"""#!/bin/bash
# PostgreSQL Backup Script
BACKUP_DIR="{destination}"
RETENTION_DAYS={retention}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup all databases
su - postgres -c "pg_dumpall > $BACKUP_DIR/postgresql_$TIMESTAMP.sql"

# Compress
gzip $BACKUP_DIR/postgresql_$TIMESTAMP.sql

# Remove old backups
find $BACKUP_DIR -name "postgresql_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_DIR/postgresql_$TIMESTAMP.sql.gz"
"""
        elif db_type in ["mysql", "mariadb"]:
            backup_script = f"""#!/bin/bash
# MySQL Backup Script
BACKUP_DIR="{destination}"
RETENTION_DAYS={retention}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup all databases
mysqldump --all-databases > $BACKUP_DIR/mysql_$TIMESTAMP.sql

# Compress
gzip $BACKUP_DIR/mysql_$TIMESTAMP.sql

# Remove old backups
find $BACKUP_DIR -name "mysql_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_DIR/mysql_$TIMESTAMP.sql.gz"
"""
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Backup not supported for {db_type}",
            )

        # Write backup script
        script_path = f"/usr/local/bin/db-backup-{db_type}.sh"
        await connector.run_command(
            f"cat > {script_path} << 'EOL'\n{backup_script}\nEOL",
            sudo=True,
        )
        await connector.run_command(f"chmod +x {script_path}", sudo=True)

        # Setup cron job
        cron_time = {
            "hourly": "0 * * * *",
            "daily": "0 2 * * *",
            "weekly": "0 2 * * 0",
        }.get(schedule, "0 2 * * *")

        cron_entry = f"{cron_time} root {script_path} >> /var/log/db-backup.log 2>&1"
        await connector.run_command(
            f"echo '{cron_entry}' > /etc/cron.d/db-backup-{db_type}",
            sudo=True,
        )

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Backup configured ({schedule})",
            details={
                "schedule": schedule,
                "retention": retention,
                "destination": destination,
                "script": script_path,
            },
        )

    async def _backup(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Perform immediate database backup."""
        db_type = params.get("type", "postgresql")
        database = params.get("database", "")
        output = params.get("output", f"/tmp/{database}_backup.sql")

        if db_type == "postgresql":
            if database:
                cmd = f"su - postgres -c 'pg_dump {database} > {output}'"
            else:
                cmd = f"su - postgres -c 'pg_dumpall > {output}'"

            result = await connector.run_command(cmd, sudo=True)

            if result.success:
                # Compress
                await connector.run_command(f"gzip -f {output}", sudo=True)

                return ModuleResult(
                    changed=True,
                    success=True,
                    message=f"Backup created: {output}.gz",
                    details={"output": f"{output}.gz"},
                )

        elif db_type in ["mysql", "mariadb"]:
            if database:
                cmd = f"mysqldump {database} > {output}"
            else:
                cmd = f"mysqldump --all-databases > {output}"

            result = await connector.run_command(cmd, sudo=True)

            if result.success:
                await connector.run_command(f"gzip -f {output}", sudo=True)

                return ModuleResult(
                    changed=True,
                    success=True,
                    message=f"Backup created: {output}.gz",
                )

        return ModuleResult(
            changed=False,
            success=False,
            message="Backup failed",
        )

    async def _restore(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Restore database from backup."""
        db_type = params.get("type", "postgresql")
        database = params.get("database", "")
        backup_file = params.get("backup_file", "")

        if not backup_file:
            return ModuleResult(
                changed=False,
                success=False,
                message="Backup file is required",
            )

        # Decompress if needed
        if backup_file.endswith(".gz"):
            await connector.run_command(f"gunzip {backup_file}", sudo=True)
            backup_file = backup_file[:-3]

        if db_type == "postgresql":
            if database:
                cmd = f"su - postgres -c 'psql {database} < {backup_file}'"
            else:
                cmd = f"su - postgres -c 'psql < {backup_file}'"

            result = await connector.run_command(cmd, sudo=True)

        elif db_type in ["mysql", "mariadb"]:
            if database:
                cmd = f"mysql {database} < {backup_file}"
            else:
                cmd = f"mysql < {backup_file}"

            result = await connector.run_command(cmd, sudo=True)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Restore not supported for {db_type}",
            )

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Database restored from {backup_file}",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Restore failed",
                details={"error": result.stderr},
            )

    async def _configure_replication(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Configure database replication."""
        db_type = params.get("type", "postgresql")
        role = params.get("role", "primary")  # primary or replica
        primary_host = params.get("primary_host", "")

        if db_type == "postgresql":
            if role == "primary":
                # Configure primary for replication
                config = """
wal_level = replica
max_wal_senders = 3
wal_keep_size = 64
"""
                await connector.run_command(
                    f"echo '{config}' >> /etc/postgresql/*/main/postgresql.conf",
                    sudo=True,
                )

                # Add replication user in pg_hba.conf
                hba_entry = "host replication replicator 0.0.0.0/0 md5"
                await connector.run_command(
                    f"echo '{hba_entry}' >> /etc/postgresql/*/main/pg_hba.conf",
                    sudo=True,
                )

                # Restart PostgreSQL
                await connector.run_command("systemctl restart postgresql", sudo=True)

                return ModuleResult(
                    changed=True,
                    success=True,
                    message="Primary replication configured",
                    details={"role": "primary"},
                )

        return ModuleResult(
            changed=False,
            success=False,
            message=f"Replication not yet supported for {db_type}/{role}",
        )

    async def _tune_performance(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Apply performance tuning."""
        db_type = params.get("type", "postgresql")
        workload = params.get("workload", "mixed")  # web, oltp, dw, mixed

        if db_type == "postgresql":
            # Get system memory
            mem_result = await connector.run_command("free -m | grep Mem | awk '{print $2}'")
            total_mem_mb = int(mem_result.stdout.strip()) if mem_result.success else 4096

            # Calculate settings based on workload and memory
            shared_buffers = total_mem_mb // 4
            effective_cache_size = total_mem_mb * 3 // 4
            work_mem = (total_mem_mb // 100) if workload == "web" else (total_mem_mb // 50)

            tuning_config = f"""
# Performance Tuning - {workload} workload
shared_buffers = {shared_buffers}MB
effective_cache_size = {effective_cache_size}MB
work_mem = {work_mem}MB
maintenance_work_mem = {total_mem_mb // 16}MB
random_page_cost = 1.1
effective_io_concurrency = 200
max_worker_processes = 4
max_parallel_workers_per_gather = 2
max_parallel_workers = 4
"""

            await connector.run_command(
                f"echo '{tuning_config}' >> /etc/postgresql/*/main/postgresql.conf",
                sudo=True,
            )

            # Restart PostgreSQL
            await connector.run_command("systemctl restart postgresql", sudo=True)

            return ModuleResult(
                changed=True,
                success=True,
                message=f"Performance tuning applied ({workload})",
                details={
                    "workload": workload,
                    "shared_buffers": f"{shared_buffers}MB",
                    "effective_cache_size": f"{effective_cache_size}MB",
                },
            )

        return ModuleResult(
            changed=False,
            success=False,
            message=f"Performance tuning not supported for {db_type}",
        )

    async def _secure_database(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Apply security hardening."""
        db_type = params.get("type", "postgresql")

        if db_type in ["mysql", "mariadb"]:
            # Run mysql_secure_installation steps programmatically
            commands = [
                "mysql -e \"DELETE FROM mysql.user WHERE User='';\"",
                "mysql -e \"DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');\"",
                "mysql -e \"DROP DATABASE IF EXISTS test;\"",
                "mysql -e \"DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';\"",
                "mysql -e \"FLUSH PRIVILEGES;\"",
            ]

            for cmd in commands:
                await connector.run_command(cmd, sudo=True)

            return ModuleResult(
                changed=True,
                success=True,
                message="MySQL security hardening applied",
            )

        elif db_type == "postgresql":
            # Restrict pg_hba.conf to local connections only
            hba_config = """
# Secure configuration
local   all             postgres                                peer
local   all             all                                     peer
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256
"""
            await connector.run_command(
                f"echo '{hba_config}' > /etc/postgresql/*/main/pg_hba.conf",
                sudo=True,
            )

            await connector.run_command("systemctl reload postgresql", sudo=True)

            return ModuleResult(
                changed=True,
                success=True,
                message="PostgreSQL security hardening applied",
            )

        return ModuleResult(
            changed=False,
            success=False,
            message=f"Security hardening not supported for {db_type}",
        )
