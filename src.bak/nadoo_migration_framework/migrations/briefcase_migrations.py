"""Migrations for updating Briefcase configuration."""

import toml
from pathlib import Path
from nadoo_migration_framework.base import Migration


class UpdateBriefcaseLicenseMigration(Migration):
    """Update Briefcase license configuration to PEP 621 format."""

    def __init__(self):
        """Initialize migration."""
        super().__init__()
        self.version = "0.3.3"
        self.description = "Update Briefcase license configuration to PEP 621 format"
        self.original_config = None
        self._config = None

    def check_version_compatibility(self) -> tuple[bool, list[str]]:
        """Check if the current version is compatible with this migration."""
        if not self.project_dir:
            return False, ["Project directory not set"]

        pyproject_file = self.project_dir / "pyproject.toml"
        if not pyproject_file.exists():
            return False, ["pyproject.toml not found"]

        try:
            with open(pyproject_file) as f:
                self._config = toml.load(f)
            return True, []
        except Exception as e:
            return False, [str(e)]

    def check_if_needed(self) -> bool:
        """Check if migration is needed."""
        if not self.project_dir:
            raise ValueError("Project directory not set")

        if self._config is None:
            compatible, _ = self.check_version_compatibility()
            if not compatible:
                return False

        # Check if project table exists
        if "project" not in self._config:
            return False

        # Check if license is defined in old format
        project = self._config["project"]
        if "license" in project and isinstance(project["license"], str):
            return True

        return False

    def _up(self) -> None:
        """Implement the migration logic."""
        pyproject_file = self.project_dir / "pyproject.toml"
        
        # Read current config
        with open(pyproject_file) as f:
            config = toml.load(f)
        
        # Store original config for rollback
        self.original_config = {
            key: value.copy() if isinstance(value, dict) else value
            for key, value in config.items()
        }
        
        # Update license configuration
        project = config["project"]
        if "license" in project and isinstance(project["license"], str):
            old_license = project["license"]
            del project["license"]
            
            # Create LICENSE file if it doesn't exist
            license_file = self.project_dir / "LICENSE"
            if not license_file.exists():
                with open(license_file, "w") as f:
                    f.write(f"{old_license}\n")
            
            # Update to PEP 621 format
            project["license"] = {"file": "LICENSE"}
            
            # Write updated config
            with open(pyproject_file, "w") as f:
                toml.dump(config, f)

    def _down(self) -> None:
        """Implement the rollback logic."""
        if not self.original_config:
            return

        pyproject_file = self.project_dir / "pyproject.toml"
        with open(pyproject_file, "w") as f:
            toml.dump(self.original_config, f)
            
        # Remove LICENSE file if it was created by this migration
        license_file = self.project_dir / "LICENSE"
        if license_file.exists():
            license_file.unlink()
