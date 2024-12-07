"""Base migration class for NADOO Migration Framework."""

import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from .config import Config
from .version_compatibility import VersionCompatibilityMatrix

class Migration(ABC):
    """Base class for all migrations."""

    def __init__(self):
        """Initialize migration."""
        self.version = self._extract_version()
        self.dependencies: List[str] = []
        self.project_dir: Optional[Path] = None
        self.config: Optional[Config] = None
        self.version_matrix = VersionCompatibilityMatrix()
    
    def _extract_version(self) -> str:
        """Extract version from class name."""
        class_name = self.__class__.__name__
        if class_name.startswith('Test'):
            # For test migrations, strip 'Test' prefix
            return class_name[4:]
        return class_name

    @property
    def is_launchpad_project(self) -> bool:
        """Check if this is a Launchpad-generated project."""
        return self.config.is_launchpad_project() if self.config else False

    def set_project_dir(self, project_dir: Path) -> None:
        """Set the project directory and initialize configuration.
        
        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = project_dir
        self.config = Config(project_dir)

    def check_version_compatibility(self) -> Tuple[bool, List[str]]:
        """Check version compatibility for the migration.
        
        Returns:
            Tuple[bool, List[str]]: (is_compatible, list of incompatibility reasons)
        """
        if not self.config:
            return False, ["Configuration not initialized"]

        framework_type = self.config.get_framework_type()
        if not framework_type:
            return False, ["Framework type not detected"]

        current_version = self.config.get_framework_version()
        if not current_version:
            return False, ["Current framework version not detected"]

        # Check framework compatibility
        is_compatible, reasons = self.version_matrix.check_framework_compatibility(
            framework_type, current_version, self.version
        )
        if not is_compatible:
            return False, reasons

        # If it's a Launchpad project, also check template compatibility
        if self.is_launchpad_project:
            template = self.config.get_launchpad_template()
            template_version = self.config.get_template_config().get("version")
            if template and template_version:
                is_compatible, template_reasons = self.version_matrix.check_template_compatibility(
                    template, current_version, template_version
                )
                if not is_compatible:
                    reasons.extend(template_reasons)
                    return False, reasons

        return True, []

    def get_compatible_versions(self) -> List[str]:
        """Get list of compatible versions for the current framework.
        
        Returns:
            List[str]: List of compatible versions
        """
        if not self.config:
            return []

        framework_type = self.config.get_framework_type()
        current_version = self.config.get_framework_version()
        if not framework_type or not current_version:
            return []

        return self.version_matrix.get_compatible_versions(framework_type, current_version)

    def get_required_dependencies(self) -> Dict[str, str]:
        """Get required dependencies for the target version.
        
        Returns:
            Dict[str, str]: Dictionary of required dependencies and their versions
        """
        if not self.config:
            return {}

        framework_type = self.config.get_framework_type()
        if not framework_type:
            return {}

        return self.version_matrix.get_required_dependencies(framework_type, self.version)
        
    def _update_version(self, version: str) -> None:
        """Update version in configuration.
        
        Args:
            version: New version string
        """
        if self.config:
            self.config.update_version(version)
    
    def _git_commit(self, message: str) -> None:
        """Create a Git commit with the given message.
        
        Args:
            message: Commit message
        """
        try:
            # Stage all changes
            subprocess.run(['git', 'add', '.'], check=True)
            # Create commit (allow empty commits for pre-migration states)
            subprocess.run(['git', 'commit', '--allow-empty', '-m', message], check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create Git commit: {e}")
    
    def up(self) -> None:
        """Apply the migration."""
        if not self.project_dir:
            raise ValueError("Project directory not set. Call set_project_dir() first.")

        # Check version compatibility
        is_compatible, reasons = self.check_version_compatibility()
        if not is_compatible:
            raise ValueError(f"Version incompatibility: {', '.join(reasons)}")

        try:
            # Create a commit before applying the migration
            self._git_commit(f"Pre-migration state for {self.version}")
            
            # Apply the migration
            self._up()
            
            # Update version
            self._update_version(self.version)
            
            # Create a commit after successful migration
            self._git_commit(f"Applied migration {self.version}")
        except Exception as e:
            # If anything fails, rollback to pre-migration state
            try:
                subprocess.run(['git', 'reset', '--hard', 'HEAD~1'], check=True)
                subprocess.run(['git', 'clean', '-fd'], check=True)  # Clean up untracked files
            except subprocess.CalledProcessError:
                pass  # If rollback fails, let the original error propagate
            raise e
    
    def down(self) -> None:
        """Rollback the migration."""
        if not self.project_dir:
            raise ValueError("Project directory not set. Call set_project_dir() first.")

        try:
            # Create a commit before rolling back
            self._git_commit(f"Pre-rollback state for {self.version}")
            
            # Rollback the migration
            self._down()
            
            # Update version
            version_parts = self.version.split('.')
            version_parts[-1] = str(int(version_parts[-1]) - 1)
            self._update_version('.'.join(version_parts))
            
            # Create a commit after successful rollback
            self._git_commit(f"Rolled back migration {self.version}")
        except Exception as e:
            # If anything fails, rollback to pre-rollback state
            try:
                subprocess.run(['git', 'reset', '--hard', 'HEAD~1'], check=True)
                subprocess.run(['git', 'clean', '-fd'], check=True)  # Clean up untracked files
            except subprocess.CalledProcessError:
                pass  # If rollback fails, let the original error propagate
            raise e

    @abstractmethod
    def _up(self) -> None:
        """Implement the migration logic."""
        pass

    @abstractmethod
    def _down(self) -> None:
        """Implement the rollback logic."""
        pass

    @abstractmethod
    def check_if_needed(self) -> bool:
        """Check if migration is needed."""
        pass

    def get_state(self) -> Dict[str, Any]:
        """Get migration state.
        
        Returns:
            Dict[str, Any]: Dictionary containing migration state information.
        """
        return {
            'version': self.version,
            'name': self.__class__.__name__,
            'dependencies': self.dependencies,
            'applied_at': datetime.now().isoformat()
        }
