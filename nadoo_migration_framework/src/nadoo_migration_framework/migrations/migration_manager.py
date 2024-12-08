"""Migration manager for NADOO Migration Framework.

This module provides a unified manager for handling project migrations, including
version tracking, dependency resolution, and migration execution.
"""

import os
import logging
from typing import List, Optional, Type, Dict, Any
import toml
from .base_migration import BaseMigration
from .base import Migration
from ..version import Version, ProjectVersion
from ..functions.project_structure_migrator import ProjectStructure
from . import MIGRATIONS


class MigrationManager:
    """Manages migrations for NADOO projects.

    This class provides functionality to:
    - Track and update project versions
    - Manage migration dependencies
    - Execute migrations in the correct order
    - Handle rollbacks
    - Support dry runs

    Attributes:
        project_path (str): Absolute path to the project being migrated
        logger (logging.Logger): Logger instance for the migration manager
        migrations (List[BaseMigration]): List of available migrations
    """

    def __init__(self, project_path: str):
        """Initialize the migration manager.

        Args:
            project_path (str): Path to the project to migrate
        """
        self.project_path = os.path.abspath(project_path)
        self.logger = logging.getLogger("nadoo.migration.manager")
        self.migrations = MIGRATIONS
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler('migration.log'), logging.StreamHandler()],
        )

    def get_project_version(self) -> ProjectVersion:
        """Get the current version of the project.

        Returns:
            ProjectVersion: Object containing project name and version
        """
        try:
            pyproject_path = os.path.join(self.project_path, "pyproject.toml")

            with open(pyproject_path, 'r') as f:
                config = toml.load(f)

            version_str = config.get('tool', {}).get('nadoo', {}).get('version', '0.1.0')
            return ProjectVersion(
                project_name=os.path.basename(self.project_path),
                current_version=Version.from_string(version_str),
            )
        except Exception as e:
            self.logger.warning(f"Failed to get project version: {e}")
            return ProjectVersion(
                project_name=os.path.basename(self.project_path), current_version=None
            )

    def _update_project_version(self, version: Version) -> None:
        """Update the project's version in pyproject.toml.

        Args:
            version (Version): New version to set
        """
        try:
            pyproject_path = os.path.join(self.project_path, "pyproject.toml")

            with open(pyproject_path, 'r') as f:
                config = toml.load(f)

            if 'tool' not in config:
                config['tool'] = {}
            if 'nadoo' not in config['tool']:
                config['tool']['nadoo'] = {}

            config['tool']['nadoo']['version'] = str(version)

            with open(pyproject_path, 'w') as f:
                toml.dump(config, f)
        except Exception as e:
            self.logger.error(f"Failed to update project version: {e}")

    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations.

        Returns:
            List[str]: Names of applied migrations
        """
        project_version = self.get_project_version()
        if project_version.current_version is None:
            return []

        return [m.name for m in self.migrations if m.version <= project_version.current_version]

    def get_pending_migrations(self) -> List[BaseMigration]:
        """Get list of pending migrations.

        Returns:
            List[BaseMigration]: List of migrations that need to be applied
        """
        project_version = self.get_project_version()
        if project_version.current_version is None:
            return self.migrations

        return [m for m in self.migrations if m.version > project_version.current_version]

    def check_dependencies(self, migration: BaseMigration) -> bool:
        """Check if all dependencies for a migration are met.

        Args:
            migration (BaseMigration): Migration to check dependencies for

        Returns:
            bool: True if all dependencies are met, False otherwise
        """
        applied = self.get_applied_migrations()
        return all(dep in applied for dep in migration.dependencies)

    def migrate(self, migration: BaseMigration, dry_run: bool = False) -> bool:
        """Run a specific migration.

        Args:
            migration (BaseMigration): Migration to run
            dry_run (bool, optional): If True, only simulate the migration

        Returns:
            bool: True if migration was successful, False otherwise
        """
        if not self.check_dependencies(migration):
            self.logger.error(f"Dependencies not met for {migration.name}")
            return False

        try:
            self.logger.info(f"Running migration: {migration.name}")
            if migration.migrate(self.project_path, dry_run):
                if not dry_run:
                    self._update_project_version(migration.version)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to run migration {migration.name}: {e}")
            return False

    def apply_migrations(self, dry_run: bool = False) -> bool:
        """Apply all pending migrations in order.

        Args:
            dry_run (bool, optional): If True, only simulate the migrations

        Returns:
            bool: True if all migrations were successful, False otherwise
        """
        pending = self.get_pending_migrations()
        if not pending:
            self.logger.info("No migrations to apply")
            return True

        success = True
        for migration in pending:
            if not self.migrate(migration, dry_run):
                success = False
                break

        return success

    def rollback_migration(self, migration_name: str) -> bool:
        """Rollback a specific migration.

        Args:
            migration_name (str): Name of the migration to rollback

        Returns:
            bool: True if rollback was successful, False otherwise
        """
        migration = next((m for m in self.migrations if m.name == migration_name), None)

        if not migration:
            self.logger.error(f"Migration not found: {migration_name}")
            return False

        try:
            if migration.rollback(self.project_path):
                self._update_project_version(migration.previous_version)
                self.logger.info(f"Rolled back migration: {migration_name}")
                return True
            self.logger.info(f"Skipped rollback: {migration_name} (not applied)")
            return False
        except Exception as e:
            self.logger.error(f"Error rolling back migration {migration_name}: {e}")
            return False

    def rollback_all(self) -> bool:
        """Rollback all applied migrations in reverse order.

        Returns:
            bool: True if all rollbacks were successful, False otherwise
        """
        applied = self.get_applied_migrations()
        success = True

        for migration_name in reversed(applied):
            if not self.rollback_migration(migration_name):
                success = False
                break

        return success

    def show_migrations(self) -> Dict[str, List[str]]:
        """Show the status of all migrations.

        Returns:
            Dict[str, List[str]]: Dictionary with 'applied' and 'pending' migrations
        """
        applied = self.get_applied_migrations()
        pending = [m.name for m in self.get_pending_migrations()]

        return {'applied': applied, 'pending': pending}
