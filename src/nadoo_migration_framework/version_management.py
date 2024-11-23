"""Version management system for NADOO Migration Framework."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import toml

from .version_types import VersionType
from .dependency_management import DependencyManager


@dataclass
class Version:
    """Represents a version number."""
    major: int
    minor: int
    patch: int
    
    def __str__(self) -> str:
        """Convert version to string."""
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def from_str(cls, version_str: str) -> "Version":
        """Create version from string."""
        match = re.match(r"(\d+)\.(\d+)\.(\d+)", version_str)
        if not match:
            raise ValueError(f"Invalid version string: {version_str}")
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3))
        )

    def bump(self, version_type: VersionType) -> "Version":
        """Bump version according to version type."""
        if version_type == VersionType.MAJOR:
            return Version(self.major + 1, 0, 0)
        elif version_type == VersionType.MINOR:
            return Version(self.major, self.minor + 1, 0)
        else:  # PATCH
            return Version(self.major, self.minor, self.patch + 1)

    def __lt__(self, other: "Version") -> bool:
        """Compare versions."""
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: "Version") -> bool:
        """Compare versions."""
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    def __gt__(self, other: "Version") -> bool:
        """Compare versions."""
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __ge__(self, other: "Version") -> bool:
        """Compare versions."""
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        """Check if versions are equal."""
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    @classmethod
    def from_string(cls, version_str: str) -> "Version":
        """Alias for from_str for backward compatibility."""
        return cls.from_str(version_str)

    def __ne__(self, other: object) -> bool:
        """Check if versions are not equal."""
        return not self.__eq__(other)


@dataclass
class Release:
    """Represents a release of the package."""
    version: Version
    timestamp: datetime
    changes: List[str]
    description: str
    dependencies: Dict[str, str]  # name -> version
    breaking_changes: List[str]
    migration_required: bool = False
    
    def to_dict(self) -> dict:
        """Convert Release to dictionary."""
        return {
            "version": str(self.version),
            "timestamp": self.timestamp.isoformat(),
            "changes": self.changes,
            "description": self.description,
            "dependencies": self.dependencies,
            "breaking_changes": self.breaking_changes,
            "migration_required": self.migration_required
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Release":
        """Create a Release from dictionary."""
        return cls(
            version=Version.from_str(data["version"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            changes=data["changes"],
            description=data["description"],
            dependencies=data.get("dependencies", {}),
            breaking_changes=data.get("breaking_changes", []),
            migration_required=data.get("migration_required", False)
        )


class VersionManager:
    """Manages package versions and releases."""
    
    def __init__(self, project_dir: Path):
        """Initialize version manager."""
        self.project_dir = project_dir
        self.pyproject_path = project_dir / "pyproject.toml"
        self.releases_path = project_dir / "releases.toml"
        self.dependency_manager = DependencyManager(project_dir)
        
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
        return Version.from_str(data["tool"]["poetry"]["version"])
    
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
    
    def add_release(self, version_type: VersionType, changes: List[str], description: str,
                   breaking_changes: Optional[List[str]] = None,
                   dependencies: Optional[Dict[str, str]] = None,
                   migration_required: bool = False) -> Release:
        """Create a new release.
        
        Args:
            version_type: Type of version change
            changes: List of changes
            description: Release description
            breaking_changes: List of breaking changes (optional)
            dependencies: Dictionary of dependencies to update (optional)
            migration_required: Whether migration is required
        
        Returns:
            Release: The created release
        """
        current = self.get_current_version()
        new_version = current.bump(version_type)
        
        # Update dependencies if provided
        if dependencies:
            for name, version in dependencies.items():
                self.dependency_manager.update_dependency(name, min_version=version)
        
        release = Release(
            version=new_version,
            timestamp=datetime.now(),
            changes=changes,
            description=description,
            dependencies=dependencies or {},
            breaking_changes=breaking_changes or [],
            migration_required=migration_required
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
        version_obj = Version.from_str(version)
        for release in releases:
            if release.version == version_obj:
                return release
        return None
    
    def get_migration_path(self, current_version: str, target_version: str) -> List[Release]:
        """Get the path of releases needed to migrate between versions.
        
        Args:
            current_version: Current version
            target_version: Target version
            
        Returns:
            List[Release]: List of releases to apply in order
        """
        releases = self.get_releases()
        current = Version.from_str(current_version)
        target = Version.from_str(target_version)
        
        if current > target:
            # Downgrade path
            path = [r for r in releases if target <= r.version <= current]
            path.sort(key=lambda r: r.version, reverse=True)
        else:
            # Upgrade path
            path = [r for r in releases if current < r.version <= target]
            path.sort(key=lambda r: r.version)
        
        return path
    
    def check_compatibility(self, target_version: str) -> Tuple[bool, List[str]]:
        """Check if migration to target version is possible.
        
        Args:
            target_version: Target version
            
        Returns:
            Tuple[bool, List[str]]: (is_compatible, list of incompatibility reasons)
        """
        current = self.get_current_version()
        target = Version.from_str(target_version)
        path = self.get_migration_path(str(current), target_version)
        
        reasons = []
        
        # Check each release in the path
        for release in path:
            # Check dependencies
            for dep, ver in release.dependencies.items():
                is_compatible, dep_reasons = self.dependency_manager.check_compatibility(dep, ver)
                if not is_compatible:
                    reasons.extend(dep_reasons)
            
            # Note breaking changes
            if release.breaking_changes:
                reasons.append(f"Breaking changes in {release.version}: {', '.join(release.breaking_changes)}")
            
            # Note if migration is required
            if release.migration_required:
                reasons.append(f"Migration required for version {release.version}")
        
        return len(reasons) == 0, reasons
    
    def get_changelog(self, start_version: Optional[str] = None,
                     end_version: Optional[str] = None) -> str:
        """Generate changelog between versions.
        
        Args:
            start_version: Start version (optional)
            end_version: End version (optional)
            
        Returns:
            str: Generated changelog
        """
        releases = self.get_releases()
        if not releases:
            return "No releases yet."
        
        # Filter releases if versions specified
        if start_version or end_version:
            start = Version.from_str(start_version) if start_version else None
            end = Version.from_str(end_version) if end_version else None
            releases = [
                r for r in releases
                if (not start or r.version >= start) and (not end or r.version <= end)
            ]
        
        changelog = ["# Changelog\n"]
        
        for release in sorted(releases, key=lambda r: r.version, reverse=True):
            changelog.append(f"\n## {release.version} ({release.timestamp.strftime('%Y-%m-%d')})")
            changelog.append(f"\n{release.description}\n")
            
            if release.breaking_changes:
                changelog.append("\n### Breaking Changes")
                for change in release.breaking_changes:
                    changelog.append(f"- {change}")
            
            if release.changes:
                changelog.append("\n### Changes")
                for change in release.changes:
                    changelog.append(f"- {change}")
            
            if release.dependencies:
                changelog.append("\n### Dependencies")
                for dep, ver in release.dependencies.items():
                    changelog.append(f"- {dep}: {ver}")
            
            if release.migration_required:
                changelog.append("\n**Migration required for this version**")
            
            changelog.append("")
        
        return "\n".join(changelog)
