"""Migration management for NADOO project structures."""

from .add_briefcase_toga import AddBriefcaseTogaMigration
from .cleanup_project_structure import CleanupProjectStructureMigration

__all__ = [
    'BaseMigration',
    'AddBriefcaseTogaMigration',
    'CleanupProjectStructureMigration',
]

MIGRATIONS = [
    AddBriefcaseTogaMigration(),
    CleanupProjectStructureMigration(),
]
