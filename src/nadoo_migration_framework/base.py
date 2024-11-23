"""Base migration class for NADOO Migration Framework."""

import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List

class Migration(ABC):
    """Base class for all migrations."""

    def __init__(self):
        """Initialize migration."""
        self.version = self._extract_version()
        self.dependencies: List[str] = []
    
    def _extract_version(self) -> str:
        """Extract version from class name."""
        class_name = self.__class__.__name__
        if class_name.startswith('Test'):
            # For test migrations, strip 'Test' prefix
            return class_name[4:]
        return class_name
    
    def _git_commit(self, message: str) -> None:
        """Create a Git commit with the given message."""
        try:
            # Stage all changes
            subprocess.run(['git', 'add', '.'], check=True)
            # Create commit (allow empty commits for pre-migration states)
            subprocess.run(['git', 'commit', '--allow-empty', '-m', message], check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create Git commit: {e}")
    
    def up(self) -> None:
        """Apply the migration."""
        try:
            # Create a commit before applying the migration
            self._git_commit(f"Pre-migration state for {self.version}")
            
            # Apply the migration
            self._up()
            
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
        try:
            # Create a commit before rolling back
            self._git_commit(f"Pre-rollback state for {self.version}")
            
            # Rollback the migration
            self._down()
            
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
    def check_if_needed(self) -> bool:
        """Check if migration is needed.
        
        Returns:
            bool: True if migration should be applied, False otherwise.
        """
        pass
    
    @abstractmethod
    def _up(self) -> None:
        """Internal method to apply the migration.
        
        This method should contain the actual migration logic.
        """
        pass
    
    @abstractmethod
    def _down(self) -> None:
        """Internal method to rollback the migration.
        
        This method should contain the actual rollback logic.
        """
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
