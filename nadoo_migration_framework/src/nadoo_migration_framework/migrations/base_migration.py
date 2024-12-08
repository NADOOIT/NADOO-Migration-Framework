"""Base migration class for NADOO Migration Framework."""

import logging
from typing import Optional
from ..version import Version


class BaseMigration:
    """Base class for all migrations."""

    def __init__(self, name: str, description: str, version: Version):
        """Initialize the migration."""
        self.name = name
        self.description = description
        self.version = version
        self.logger = logging.getLogger(f"nadoo.migration.{name}")

    def migrate(self, project_path: str, dry_run: bool = False) -> bool:
        """Perform the migration."""
        raise NotImplementedError("Subclasses must implement migrate()")

    def rollback(self, project_path: str) -> bool:
        """Rollback the migration."""
        raise NotImplementedError("Subclasses must implement rollback()")

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.name} ({self.version}): {self.description}"
