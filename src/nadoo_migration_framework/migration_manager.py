"""Migration manager for NADOO Migration Framework."""

import importlib
import inspect
import logging
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional, Type, Union

from .base import Migration
from .version_compatibility import VersionCompatibilityMatrix
from .version_management import VersionManager, Version
from .dependency_management import DependencyManager

logger = logging.getLogger(__name__)


class MigrationType(Enum):
    """Types of migrations."""
    FORWARD = "forward"
    BACKWARD = "backward"


class MigrationFile:
    """Represents a migration file."""

    def __init__(self, path: Path):
        """Initialize migration file.
        
        Args:
            path: Path to migration file
        """
        self.path = path
        self.module = None
        self.migrations: Dict[str, Type[Migration]] = {}
        self._load()

    def _load(self):
        """Load migration file."""
        try:
            # Import module dynamically
            module_name = self.path.stem
            spec = importlib.util.spec_from_file_location(module_name, self.path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load module from {self.path}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.module = module

            # Find all Migration classes
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and issubclass(obj, Migration) and 
                    obj != Migration):
                    self.migrations[name] = obj
        except Exception as e:
            logger.error(f"Failed to load migration file {self.path}: {e}")
            raise


class MigrationManager:
    """Manages migrations between versions."""
    
    def __init__(self, project_dir: Path):
        """Initialize migration manager.
        
        Args:
            project_dir: Project directory path
        """
        self.project_dir = project_dir
        self.version_manager = VersionManager(project_dir)
        self.dependency_manager = DependencyManager(project_dir)
        self.version_matrix = VersionCompatibilityMatrix()
        self._migrations: Dict[str, Type[Migration]] = {}
        self._discover_migrations()
    
    def _discover_migrations(self):
        """Discover available migrations in the migrations directory."""
        migrations_dir = Path(__file__).parent / "migrations"
        if not migrations_dir.exists():
            return
        
        for file in migrations_dir.glob("*.py"):
            if file.name.startswith("_"):
                continue
            
            migration_file = MigrationFile(file)
            self._migrations.update(migration_file.migrations)
    
    def get_available_migrations(self) -> List[str]:
        """Get list of available migrations.
        
        Returns:
            List[str]: List of available migration versions
        """
        return sorted(self._migrations.keys())
    
    def get_migration(self, version: str) -> Optional[Type[Migration]]:
        """Get migration class for a version.
        
        Args:
            version: Version string
            
        Returns:
            Optional[Type[Migration]]: Migration class if found
        """
        return self._migrations.get(version)
    
    def check_migration_path(self, target_version: str) -> List[str]:
        """Check if migration path to target version is valid.
        
        Args:
            target_version: Target version
            
        Returns:
            List[str]: List of issues, empty if path is valid
        """
        current_version = str(self.version_manager.get_current_version())
        path = self.version_manager.get_migration_path(current_version, target_version)
        
        issues = []
        
        # Check each release in the path
        for release in path:
            version = str(release.version)
            
            # Check if migration exists
            if release.migration_required and version not in self._migrations:
                issues.append(f"Missing migration for version {version}")
            
            # Check dependencies
            for dep, ver in release.dependencies.items():
                is_compatible, reasons = self.dependency_manager.check_compatibility(dep, ver)
                if not is_compatible:
                    issues.extend(reasons)
            
            # Check framework compatibility
            is_compatible, reasons = self.version_matrix.check_framework_compatibility(
                self.version_manager.get_framework_type(),
                current_version,
                version
            )
            if not is_compatible:
                issues.extend(reasons)
        
        return issues
    
    def migrate(self, target_version: str, dry_run: bool = False) -> bool:
        """Migrate to target version.
        
        Args:
            target_version: Target version
            dry_run: If True, only check migration path without executing
            
        Returns:
            bool: True if migration successful or dry run passed
        """
        # Check migration path
        issues = self.check_migration_path(target_version)
        if issues:
            logger.error("Migration path has issues:")
            for issue in issues:
                logger.error(f"- {issue}")
            return False
        
        if dry_run:
            return True
        
        # Get migration path
        current_version = str(self.version_manager.get_current_version())
        path = self.version_manager.get_migration_path(current_version, target_version)
        
        try:
            # Execute migrations in order
            for release in path:
                version = str(release.version)
                
                # Update dependencies first
                for dep, ver in release.dependencies.items():
                    self.dependency_manager.update_dependency(dep, min_version=ver)
                
                # Apply migration if required
                if release.migration_required:
                    migration_class = self._migrations[version]
                    migration = migration_class()
                    migration.set_project_dir(self.project_dir)
                    
                    if current_version < version:
                        # Up migration
                        migration.up()
                    else:
                        # Down migration
                        migration.down()
                
                # Update version
                self.version_manager.set_version(release.version)
                current_version = version
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    def create_migration(self, version: str, migration_type: str,
                        description: str) -> Optional[Path]:
        """Create a new migration file.
        
        Args:
            version: Version for the migration
            migration_type: Type of migration (e.g., 'toga', 'django')
            description: Migration description
            
        Returns:
            Optional[Path]: Path to created migration file
        """
        migrations_dir = Path(__file__).parent / "migrations"
        migrations_dir.mkdir(exist_ok=True)
        
        # Create migration file name
        file_name = f"{migration_type}_{version.replace('.', '_')}_migration.py"
        file_path = migrations_dir / file_name
        
        if file_path.exists():
            logger.error(f"Migration file {file_name} already exists")
            return None
        
        # Create migration file
        class_name = f"{migration_type.title()}{version.replace('.', '')}Migration"
        
        content = f'''"""Migration for {migration_type} {version}."""

from pathlib import Path
from typing import Dict, Any

from ..base import Migration


class {class_name}(Migration):
    """Migration for {migration_type} {version}."""
    
    def __init__(self):
        """Initialize migration."""
        super().__init__()
        self.version = "{version}"
        self.description = "{description}"
    
    def _up(self) -> None:
        """Implement the migration logic."""
        # TODO: Implement migration logic
        pass
    
    def _down(self) -> None:
        """Implement the rollback logic."""
        # TODO: Implement rollback logic
        pass
    
    def check_if_needed(self) -> bool:
        """Check if migration is needed."""
        # TODO: Implement check logic
        return True
'''
        
        with open(file_path, "w") as f:
            f.write(content)
        
        return file_path
