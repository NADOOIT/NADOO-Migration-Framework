"""Base classes for NADOO migrations."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import os
import json
from datetime import datetime
from pathlib import Path


class Migration(ABC):
    """Base class for all migrations."""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.migration_name = self.__class__.__name__
        self._load_state()

    @abstractmethod
    def apply(self) -> bool:
        """Apply the migration. Return True if applied, False if skipped."""
        pass

    @abstractmethod
    def rollback(self) -> bool:
        """Rollback the migration. Return True if rolled back, False if skipped."""
        pass

    @property
    def dependencies(self) -> list[str]:
        """List of migration names that must be applied before this one."""
        return []

    def _load_state(self) -> None:
        """Load migration state from the project."""
        state_file = self._get_state_file()
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {'applied_migrations': [], 'current_structure': 'legacy', 'history': []}

    def _save_state(self, applied: bool = True, message: str = '') -> None:
        """Save migration state to the project."""
        state_file = self._get_state_file()

        if applied:
            if self.migration_name not in self.state['applied_migrations']:
                self.state['applied_migrations'].append(self.migration_name)
        else:
            if self.migration_name in self.state['applied_migrations']:
                self.state['applied_migrations'].remove(self.migration_name)

        self.state['history'].append(
            {
                'migration': self.migration_name,
                'action': 'applied' if applied else 'rolled back',
                'timestamp': datetime.now().isoformat(),
                'message': message,
            }
        )

        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        with open(state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def _get_state_file(self) -> str:
        """Get the path to the migration state file."""
        return os.path.join(self.project_path, '.nadoo', 'migration_state.json')

    def is_applied(self) -> bool:
        """Check if this migration has been applied."""
        return self.migration_name in self.state.get('applied_migrations', [])
