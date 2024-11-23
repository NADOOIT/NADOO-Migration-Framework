"""Version management system for NADOO Migration Framework."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

import toml


class VersionType(Enum):
    """Types of version changes."""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


@dataclass
class Version:
    """Represents a semantic version."""
    major: int
    minor: int
    patch: int
    
    @classmethod
    def from_string(cls, version_str: str) -> "Version":
        """Create a Version from a string."""
        match = re.match(r"(\d+)\.(\d+)\.(\d+)", version_str)
        if not match:
            raise ValueError(f"Invalid version string: {version_str}")
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3))
        )
    
    def bump(self, version_type: VersionType) -> "Version":
        """Create a new Version with the specified component bumped."""
        if version_type == VersionType.MAJOR:
            return Version(self.major + 1, 0, 0)
        elif version_type == VersionType.MINOR:
            return Version(self.major, self.minor + 1, 0)
        else:  # PATCH
            return Version(self.major, self.minor, self.patch + 1)
    
    def __str__(self) -> str:
        """Convert Version to string."""
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass
class Release:
    """Represents a release of the package."""
    version: Version
    timestamp: datetime
    changes: List[str]
    description: str
    
    def to_dict(self) -> dict:
        """Convert Release to dictionary."""
        return {
            "version": str(self.version),
            "timestamp": self.timestamp.isoformat(),
            "changes": self.changes,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Release":
        """Create a Release from dictionary."""
        return cls(
            version=Version.from_string(data["version"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            changes=data["changes"],
            description=data["description"]
        )


class VersionManager:
    """Manages package versions and releases."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.pyproject_path = project_dir / "pyproject.toml"
        self.releases_path = project_dir / "releases.toml"
        
        # Create releases.toml if it doesn't exist
        if not self.releases_path.exists():
            self._init_releases_file()
    
    def _init_releases_file(self):
        """Initialize releases.toml file."""
        initial_content = {
            "releases": []
        }
        with open(self.releases_path, "w") as f:
            toml.dump(initial_content, f)
    
    def get_current_version(self) -> Version:
        """Get current version from pyproject.toml."""
        with open(self.pyproject_path) as f:
            data = toml.load(f)
        return Version.from_string(data["tool"]["poetry"]["version"])
    
    def set_version(self, version: Version):
        """Update version in pyproject.toml."""
        with open(self.pyproject_path) as f:
            data = toml.load(f)
        
        data["tool"]["poetry"]["version"] = str(version)
        
        with open(self.pyproject_path, "w") as f:
            toml.dump(data, f)
    
    def get_releases(self) -> List[Release]:
        """Get all releases."""
        with open(self.releases_path) as f:
            data = toml.load(f)
        return [Release.from_dict(r) for r in data.get("releases", [])]
    
    def add_release(self, version_type: VersionType, changes: List[str], description: str) -> Release:
        """Create a new release."""
        current = self.get_current_version()
        new_version = current.bump(version_type)
        
        release = Release(
            version=new_version,
            timestamp=datetime.now(),
            changes=changes,
            description=description
        )
        
        # Update releases.toml
        with open(self.releases_path) as f:
            data = toml.load(f)
        
        data.setdefault("releases", []).append(release.to_dict())
        
        with open(self.releases_path, "w") as f:
            toml.dump(data, f)
        
        # Update pyproject.toml
        self.set_version(new_version)
        
        return release
    
    def get_release(self, version: str) -> Optional[Release]:
        """Get a specific release by version."""
        releases = self.get_releases()
        for release in releases:
            if str(release.version) == version:
                return release
        return None
    
    def get_changelog(self) -> str:
        """Generate changelog from releases."""
        releases = self.get_releases()
        if not releases:
            return "No releases yet."
        
        changelog = ["# Changelog\n"]
        
        for release in sorted(releases, key=lambda r: r.version, reverse=True):
            changelog.append(f"\n## {release.version} ({release.timestamp.strftime('%Y-%m-%d')})")
            changelog.append(f"\n{release.description}\n")
            for change in release.changes:
                changelog.append(f"- {change}")
            changelog.append("")
        
        return "\n".join(changelog)
