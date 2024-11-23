"""Framework-specific migration handlers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

class FrameworkMigrator(ABC):
    """Base class for framework-specific migrators."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
    
    @abstractmethod
    def detect(self) -> bool:
        """Detect if this framework is used in the project."""
        pass
    
    @abstractmethod
    def get_migration_steps(self) -> List[Dict]:
        """Get migration steps for this framework."""
        pass
    
    @abstractmethod
    def get_requirements(self) -> List[str]:
        """Get required packages for this framework."""
        pass
