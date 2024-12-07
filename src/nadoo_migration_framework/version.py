"""Version information for NADOO Migration Framework."""

from dataclasses import dataclass
from typing import Optional, List
import re

@dataclass
class Version:
    """Version information."""
    major: int
    minor: int
    patch: int
    
    @classmethod
    def from_string(cls, version_str: str) -> 'Version':
        """Create version from string (e.g., '0.1.0')."""
        match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_str)
        if not match:
            raise ValueError(f"Invalid version string: {version_str}")
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3))
        )
    
    def __str__(self) -> str:
        """Convert version to string."""
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def __lt__(self, other: 'Version') -> bool:
        """Compare versions."""
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

CURRENT_VERSION = Version(0, 1, 0)

@dataclass
class ProjectVersion:
    """Project version information."""
    project_name: str
    current_version: Optional[Version] = None
    available_migrations: List[str] = None
    
    @property
    def needs_migration(self) -> bool:
        """Check if project needs migration."""
        return (
            self.current_version is None or 
            self.current_version < CURRENT_VERSION
        )
    
    @property
    def status(self) -> str:
        """Get project status."""
        if self.current_version is None:
            return "Not migrated"
        elif self.current_version < CURRENT_VERSION:
            return f"Outdated (v{self.current_version})"
        else:
            return f"Up to date (v{self.current_version})"
