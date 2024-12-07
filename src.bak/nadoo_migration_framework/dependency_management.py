"""Dependency management system for NADOO Migration Framework."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from packaging import version
import toml
from pathlib import Path

from .version_types import VersionType

@dataclass
class DependencyRequirement:
    """Represents a dependency requirement."""
    name: str
    min_version: str
    max_version: str
    optional: bool = False
    excluded_versions: Set[str] = None
    
    def __post_init__(self):
        """Initialize after creation."""
        if self.excluded_versions is None:
            self.excluded_versions = set()
    
    def is_compatible(self, version_str: str) -> bool:
        """Check if a version is compatible.
        
        Args:
            version_str: Version to check
            
        Returns:
            bool: True if version is compatible
        """
        if version_str in self.excluded_versions:
            return False
            
        try:
            ver = version.parse(version_str)
            min_ver = version.parse(self.min_version)
            max_ver = version.parse(self.max_version)
            return min_ver <= ver <= max_ver
        except version.InvalidVersion:
            return False

class DependencyManager:
    """Manages project dependencies."""
    
    def __init__(self, project_dir: Path):
        """Initialize dependency manager.
        
        Args:
            project_dir: Project directory path
        """
        self.project_dir = project_dir
        self.pyproject_path = project_dir / "pyproject.toml"
        self.requirements_path = project_dir / "requirements.txt"
        self._load_dependencies()
    
    def _load_dependencies(self):
        """Load current dependencies from project files."""
        self.dependencies: Dict[str, DependencyRequirement] = {}
        
        # Load from pyproject.toml
        if self.pyproject_path.exists():
            with open(self.pyproject_path) as f:
                data = toml.load(f)
                deps = data.get("project", {}).get("dependencies", [])
                for dep in deps:
                    name = dep.split("[")[0].split(">=")[0].split("==")[0].strip()
                    version_spec = dep.split(name)[-1].strip()
                    if ">=" in version_spec:
                        min_ver = version_spec.split(">=")[1].split(",")[0].strip()
                        max_ver = "*"
                    elif "==" in version_spec:
                        min_ver = max_ver = version_spec.split("==")[1].strip()
                    else:
                        continue
                    
                    self.dependencies[name] = DependencyRequirement(
                        name=name,
                        min_version=min_ver,
                        max_version=max_ver
                    )
        
        # Load from requirements.txt
        if self.requirements_path.exists():
            with open(self.requirements_path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    
                    if ">=" in line:
                        name = line.split(">=")[0].strip()
                        min_ver = line.split(">=")[1].split(",")[0].strip()
                        max_ver = "*"
                    elif "==" in line:
                        name = line.split("==")[0].strip()
                        min_ver = max_ver = line.split("==")[1].strip()
                    else:
                        continue
                    
                    if name not in self.dependencies:
                        self.dependencies[name] = DependencyRequirement(
                            name=name,
                            min_version=min_ver,
                            max_version=max_ver
                        )
    
    def add_dependency(self, name: str, min_version: str, max_version: Optional[str] = None,
                      optional: bool = False) -> None:
        """Add a new dependency.
        
        Args:
            name: Dependency name
            min_version: Minimum version
            max_version: Maximum version (optional)
            optional: Whether the dependency is optional
        """
        self.dependencies[name] = DependencyRequirement(
            name=name,
            min_version=min_version,
            max_version=max_version or "*",
            optional=optional
        )
        self._save_dependencies()
    
    def remove_dependency(self, name: str) -> None:
        """Remove a dependency.
        
        Args:
            name: Dependency name
        """
        if name in self.dependencies:
            del self.dependencies[name]
            self._save_dependencies()
    
    def update_dependency(self, name: str, min_version: Optional[str] = None,
                         max_version: Optional[str] = None) -> None:
        """Update a dependency's version requirements.
        
        Args:
            name: Dependency name
            min_version: New minimum version (optional)
            max_version: New maximum version (optional)
        """
        if name in self.dependencies:
            dep = self.dependencies[name]
            if min_version:
                dep.min_version = min_version
            if max_version:
                dep.max_version = max_version
            self._save_dependencies()
    
    def _save_dependencies(self):
        """Save dependencies to project files."""
        # Update pyproject.toml
        if self.pyproject_path.exists():
            with open(self.pyproject_path) as f:
                data = toml.load(f)
            
            deps = []
            for dep in self.dependencies.values():
                if dep.max_version == "*":
                    deps.append(f"{dep.name}>={dep.min_version}")
                else:
                    deps.append(f"{dep.name}>={dep.min_version},<={dep.max_version}")
            
            if "project" not in data:
                data["project"] = {}
            data["project"]["dependencies"] = deps
            
            with open(self.pyproject_path, "w") as f:
                toml.dump(data, f)
        
        # Update requirements.txt
        with open(self.requirements_path, "w") as f:
            for dep in self.dependencies.values():
                if dep.max_version == "*":
                    f.write(f"{dep.name}>={dep.min_version}\n")
                else:
                    f.write(f"{dep.name}>={dep.min_version},<={dep.max_version}\n")
    
    def check_compatibility(self, dependency: str, version: str) -> Tuple[bool, List[str]]:
        """Check if a dependency version is compatible.
        
        Args:
            dependency: Dependency name
            version: Version to check
            
        Returns:
            Tuple[bool, List[str]]: (is_compatible, list of incompatibility reasons)
        """
        if dependency not in self.dependencies:
            return False, [f"Unknown dependency: {dependency}"]
        
        dep = self.dependencies[dependency]
        reasons = []
        
        if not dep.is_compatible(version):
            reasons.append(
                f"Version {version} is not compatible. Must be between {dep.min_version} and {dep.max_version}"
            )
        
        if version in dep.excluded_versions:
            reasons.append(f"Version {version} is explicitly excluded")
        
        return len(reasons) == 0, reasons
    
    def get_compatible_versions(self, dependency: str) -> List[str]:
        """Get list of compatible versions for a dependency.
        
        Args:
            dependency: Dependency name
            
        Returns:
            List[str]: List of compatible versions
        """
        if dependency not in self.dependencies:
            return []
        
        dep = self.dependencies[dependency]
        # This is a simplified version - in practice, you'd want to query PyPI
        # or another package index to get actual available versions
        return [dep.min_version]
