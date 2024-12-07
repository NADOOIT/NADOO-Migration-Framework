"""Configuration management for NADOO Migration Framework."""

import toml
from pathlib import Path
from typing import Dict, Any, Optional

class Config:
    """Configuration management for migrations."""

    def __init__(self, project_dir: Path):
        """Initialize configuration.
        
        Args:
            project_dir: Path to project directory
        """
        self.project_dir = project_dir
        self._pyproject_config = self._load_pyproject_config()
        self._launchpad_config = self._load_launchpad_config()

    def _load_pyproject_config(self) -> Dict[str, Any]:
        """Load pyproject.toml configuration.
        
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        pyproject_path = self.project_dir / "pyproject.toml"
        if not pyproject_path.exists():
            return {}
        
        try:
            return toml.load(pyproject_path)
        except toml.TomlDecodeError:
            return {}

    def _load_launchpad_config(self) -> Dict[str, Any]:
        """Load .launchpad configuration.
        
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        launchpad_path = self.project_dir / ".launchpad"
        if not launchpad_path.exists():
            return {}
        
        try:
            return toml.load(launchpad_path)
        except toml.TomlDecodeError:
            return {}

    def is_launchpad_project(self) -> bool:
        """Check if this is a Launchpad-generated project.
        
        Returns:
            bool: True if this is a Launchpad project
        """
        return bool(self._launchpad_config)

    def get_framework_type(self) -> Optional[str]:
        """Get the framework type from configuration.
        
        Returns:
            Optional[str]: Framework type or None if not found
        """
        # Try Launchpad config first
        if self._launchpad_config:
            framework = self._launchpad_config.get("framework", {}).get("name")
            if framework:
                return framework.lower()

        # Fall back to pyproject.toml
        dependencies = self._pyproject_config.get("project", {}).get("dependencies", [])
        for dep in dependencies:
            if any(fw in dep.lower() for fw in ["toga", "kivy", "tkinter"]):
                return dep.split("[")[0].lower()

        return None

    def get_framework_version(self) -> Optional[str]:
        """Get the framework version from configuration.
        
        Returns:
            Optional[str]: Framework version or None if not found
        """
        # Try Launchpad config first
        if self._launchpad_config:
            version = self._launchpad_config.get("framework", {}).get("version")
            if version:
                return version

        # Fall back to pyproject.toml
        framework = self.get_framework_type()
        if not framework:
            return None

        dependencies = self._pyproject_config.get("project", {}).get("dependencies", [])
        for dep in dependencies:
            if framework in dep.lower():
                # Extract version from dependency string
                parts = dep.split(">=")
                if len(parts) > 1:
                    return parts[1].split(",")[0].strip()
                parts = dep.split("==")
                if len(parts) > 1:
                    return parts[1].split(",")[0].strip()

        return None

    def get_launchpad_template(self) -> Optional[str]:
        """Get the Launchpad template name.
        
        Returns:
            Optional[str]: Template name or None if not found
        """
        if not self._launchpad_config:
            return None
        
        return self._launchpad_config.get("template", {}).get("name")

    def get_template_config(self) -> Dict[str, Any]:
        """Get the template configuration.
        
        Returns:
            Dict[str, Any]: Template configuration
        """
        if not self._launchpad_config:
            return {}
        
        return self._launchpad_config.get("template", {})

    def update_version(self, version: str) -> None:
        """Update framework version in configuration.
        
        Args:
            version: New version string
        """
        framework = self.get_framework_type()
        if not framework:
            return

        # Update Launchpad config if present
        if self._launchpad_config:
            if "framework" not in self._launchpad_config:
                self._launchpad_config["framework"] = {}
            self._launchpad_config["framework"]["version"] = version
            launchpad_path = self.project_dir / ".launchpad"
            with open(launchpad_path, "w") as f:
                toml.dump(self._launchpad_config, f)

        # Update pyproject.toml
        if self._pyproject_config:
            dependencies = self._pyproject_config.get("project", {}).get("dependencies", [])
            for i, dep in enumerate(dependencies):
                if framework in dep.lower():
                    # Replace version in dependency string
                    parts = dep.split(">=")
                    if len(parts) > 1:
                        dependencies[i] = f"{parts[0]}>={version}"
                    else:
                        parts = dep.split("==")
                        if len(parts) > 1:
                            dependencies[i] = f"{parts[0]}=={version}"
            
            pyproject_path = self.project_dir / "pyproject.toml"
            with open(pyproject_path, "w") as f:
                toml.dump(self._pyproject_config, f)

    def get_project_name(self) -> Optional[str]:
        """Get the project name from configuration.
        
        Returns:
            Optional[str]: Project name or None if not found
        """
        # Try Launchpad config first
        if self._launchpad_config:
            name = self._launchpad_config.get("project", {}).get("name")
            if name:
                return name

        # Fall back to pyproject.toml
        return self._pyproject_config.get("project", {}).get("name")

    def get_migration_config(self) -> Dict[str, Any]:
        """Get migration-specific configuration."""
        try:
            return self._pyproject_config["tool"]["nadoo-migration"]
        except KeyError:
            return {}

    def is_launchpad_project(self) -> bool:
        """Check if this is a Launchpad-generated project."""
        return (self.project_dir / ".launchpad").exists()
