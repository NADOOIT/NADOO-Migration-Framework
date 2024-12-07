"""Dry run functionality for migrations."""

import os
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from pathlib import Path
from .base import Migration
from ..version import Version, ProjectVersion

@dataclass
class FileChange:
    """Represents a change to a file."""
    path: str
    action: str  # 'create', 'modify', 'delete', 'move'
    content_changes: Optional[Dict[str, str]] = None  # old -> new content
    new_path: Optional[str] = None  # for 'move' action

@dataclass
class DryRunResult:
    """Results of a dry run."""
    project_path: str
    changes: List[FileChange] = field(default_factory=list)
    version_before: Optional[Version] = None
    version_after: Optional[Version] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class DryRunMigration(Migration):
    """Base class for dry run migrations."""
    
    def __init__(self, project_path: str):
        super().__init__(project_path)
        self.changes: List[FileChange] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def record_change(self, change: FileChange) -> None:
        """Record a file change."""
        self.changes.append(change)
    
    def record_error(self, error: str) -> None:
        """Record an error."""
        self.errors.append(error)
    
    def record_warning(self, warning: str) -> None:
        """Record a warning."""
        self.warnings.append(warning)
    
    def would_create_file(self, path: str, content: str) -> None:
        """Record that a file would be created."""
        self.record_change(FileChange(
            path=path,
            action='create',
            content_changes={'': content}
        ))
    
    def would_modify_file(self, path: str, old_content: str, new_content: str) -> None:
        """Record that a file would be modified."""
        self.record_change(FileChange(
            path=path,
            action='modify',
            content_changes={old_content: new_content}
        ))
    
    def would_delete_file(self, path: str) -> None:
        """Record that a file would be deleted."""
        self.record_change(FileChange(
            path=path,
            action='delete'
        ))
    
    def would_move_file(self, old_path: str, new_path: str) -> None:
        """Record that a file would be moved."""
        self.record_change(FileChange(
            path=old_path,
            action='move',
            new_path=new_path
        ))
    
    def get_dry_run_result(self) -> DryRunResult:
        """Get the results of the dry run."""
        return DryRunResult(
            project_path=self.project_path,
            changes=self.changes,
            version_before=Version.from_string('0.0.0'),
            version_after=Version.from_string('0.1.0'),
            errors=self.errors,
            warnings=self.warnings
        )

class DryRunManager:
    """Manager for dry run migrations."""
    
    def __init__(self, project_path: str):
        self.project_path = project_path
    
    def dry_run_migration(self, migration_class: type) -> DryRunResult:
        """Perform a dry run of a migration."""
        migration = migration_class(self.project_path)
        migration.apply()
        return migration.get_dry_run_result()
    
    def dry_run_all(self, migrations: List[type]) -> List[DryRunResult]:
        """Perform dry runs of all migrations."""
        results = []
        for migration_class in migrations:
            try:
                result = self.dry_run_migration(migration_class)
                results.append(result)
            except Exception as e:
                result = DryRunResult(
                    project_path=self.project_path,
                    errors=[str(e)]
                )
                results.append(result)
        return results
