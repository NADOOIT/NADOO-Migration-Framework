"""NADOO Framework migration engine."""

import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import toml

from ..analyzers import NADOOProjectAnalyzer
from ..version_management import Version
from ..compatibility import CompatibilityChecker  # Import CompatibilityChecker


@dataclass
class MigrationStep:
    """A single migration step."""

    type: str
    description: str
    path: Optional[str] = None
    content: Optional[str] = None
    modifications: Optional[List[Dict[str, Any]]] = None
    estimated_time: int = 5  # in seconds

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "description": self.description,
            "path": self.path,
            "content": self.content,
            "modifications": self.modifications,
            "estimated_time": self.estimated_time,
        }


@dataclass
class MigrationPlan:
    """Plan for migrating a project."""

    steps: List[MigrationStep]
    backup_needed: bool = True

    @property
    def estimated_time(self) -> int:
        """Calculate total estimated time."""
        return sum(step.estimated_time for step in self.steps)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "steps": [step.to_dict() for step in self.steps],
            "backup_needed": self.backup_needed,
            "estimated_time": self.estimated_time,
        }


class MigrationEngine:
    """Handles project migrations."""

    LATEST_VERSION = "0.2.5"

    def __init__(self, project_dir: Path):
        """Initialize migration engine.

        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = project_dir
        self.backup_dir = project_dir / ".nadoo" / "backups"
        self.analyzer = NADOOProjectAnalyzer(project_dir)
        self.compatibility_checker = CompatibilityChecker(
            project_dir
        )  # Initialize compatibility checker

    def check_migrations(self) -> List[str]:
        """Check what migrations are needed.

        Returns:
            List[str]: List of needed migrations
        """
        changes = []

        # Check if it's a NADOO project
        if not self.analyzer.is_nadoo_project():
            changes.append("Initialize NADOO Framework")
            return changes

        # Get current version
        current_version = self._get_current_version()
        if current_version and Version.from_string(current_version) < Version.from_string(
            self.LATEST_VERSION
        ):
            changes.append(f"Update from {current_version} to {self.LATEST_VERSION}")

        # Check for required directories
        required_dirs = [
            "nadoo",
            "nadoo/config",
            "nadoo/migrations",
            "nadoo/templates",
            "nadoo/static",
        ]
        for dir_path in required_dirs:
            if not (self.project_dir / dir_path).exists():
                changes.append(f"Create {dir_path} directory")

        # Check for required files
        required_files = {
            "nadoo/__init__.py": "",
            "nadoo/config/settings.toml": self._get_default_settings(),
            "requirements.txt": self._get_required_dependencies(),
        }
        for file_path, content in required_files.items():
            if not (self.project_dir / file_path).exists():
                changes.append(f"Create {file_path}")

        # Check GUI structure
        gui_dirs = ["gui", "gui/templates", "gui/static"]
        for dir_path in gui_dirs:
            if not (self.project_dir / dir_path).exists():
                changes.append(f"Create {dir_path} directory")

        gui_files = ["gui/__init__.py", "gui/window.py", "gui/app.py"]
        for file_path in gui_files:
            if not (self.project_dir / file_path).exists():
                changes.append(f"Create {file_path}")

        return changes

    def create_backup(self) -> Path:
        """Create a backup of the project.

        Returns:
            Path: Path to the backup directory
        """
        # Create backup directory
        backup_path = self.backup_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path.mkdir(parents=True, exist_ok=True)

        # Copy project files
        for item in self.project_dir.iterdir():
            if item.name != ".nadoo":  # Skip .nadoo directory
                if item.is_dir():
                    shutil.copytree(item, backup_path / item.name)
                else:
                    shutil.copy2(item, backup_path / item.name)

        return backup_path

    def _get_current_version(self) -> Optional[str]:
        """Get current project version."""
        settings_path = self.project_dir / "nadoo" / "config" / "settings.toml"
        if not settings_path.exists():
            return None

        try:
            settings = toml.load(settings_path)
            return settings.get("nadoo", {}).get("version")
        except:
            return None

    def _get_default_settings(self) -> str:
        """Get default settings content."""
        return f"""[nadoo]
version = "{self.LATEST_VERSION}"
name = "NADOO Project"
type = "python"

[migrations]
enabled = true
auto_backup = true
"""

    def _get_required_dependencies(self) -> str:
        """Get required dependencies content."""
        return f"""# NADOO Framework dependencies
nadoo-framework>={self.LATEST_VERSION}
toga>=0.4.0
toga-cocoa>=0.4.0; sys_platform == "darwin"
toga-gtk>=0.4.0; sys_platform == "linux"
toga-winforms>=0.4.0; sys_platform == "win32"
"""

    def plan_migration(self) -> MigrationPlan:
        """Create a migration plan for the project.

        Returns:
            MigrationPlan: The planned migration steps
        """
        steps = []

        # Check if it's already a NADOO project
        current_version = self._get_current_version()
        if current_version:
            if Version.from_string(current_version) < Version.from_string(self.LATEST_VERSION):
                steps.extend(self._plan_version_update(current_version))
        else:
            # Plan new project setup
            steps.extend(self._plan_initial_setup())

        # Add structure migrations
        steps.extend(self._plan_structure_migration())

        return MigrationPlan(steps=steps)

    def execute_plan(self, plan: MigrationPlan) -> bool:
        """Execute a migration plan.

        Args:
            plan: The migration plan to execute

        Returns:
            bool: True if migration was successful
        """
        backup_path = None
        if plan.backup_needed:
            backup_path = self.create_backup()
            print(f"Created backup at {backup_path}")

        try:
            for step in plan.steps:
                self._execute_step(step)
            return True
        except Exception as e:
            print(f"Error during migration: {str(e)}")
            if backup_path:
                print(f"Restore from backup at {backup_path}")
            return False

    def _execute_step(self, step: MigrationStep) -> None:
        """Execute a single migration step.

        Args:
            step: The migration step to execute
        """
        print(f"- {step.description}...")

        try:
            if step.type == "create_directory":
                os.makedirs(self.project_dir / step.path, exist_ok=True)

            elif step.type == "create_file":
                path = self.project_dir / step.path
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w") as f:
                    f.write(step.content)

            elif step.type == "modify_file":
                path = self.project_dir / step.path
                if path.exists():
                    with open(path) as f:
                        content = f.read()

                    for mod in step.modifications:
                        if mod["type"] == "replace":
                            content = content.replace(mod["old"], mod["new"])
                        elif mod["type"] == "append":
                            content += "\n" + mod["content"]

                    with open(path, "w") as f:
                        f.write(content)
                else:
                    with open(path, "w") as f:
                        if step.content:
                            f.write(step.content)

            elif step.type == "update_version":
                settings_path = self.project_dir / "nadoo" / "config" / "settings.toml"
                if settings_path.exists():
                    settings = toml.load(settings_path)
                    settings["nadoo"]["version"] = step.content
                    with open(settings_path, "w") as f:
                        toml.dump(settings, f)

        except Exception as e:
            raise RuntimeError(f"Failed to execute step '{step.description}': {str(e)}")

    def _plan_initial_setup(self) -> List[MigrationStep]:
        """Plan initial project setup steps.

        Returns:
            List[MigrationStep]: List of migration steps
        """
        return [
            MigrationStep(
                type="create_directory",
                path=".nadoo",
                description="Create NADOO configuration directory",
            ),
            MigrationStep(
                type="create_directory",
                path=".nadoo/backups",
                description="Create backup directory",
            ),
            MigrationStep(
                type="create_file",
                path=".nadoo/config.toml",
                content=self._generate_config(),
                description="Create NADOO configuration file",
            ),
            MigrationStep(
                type="modify_file",
                path="pyproject.toml",
                modifications=self._generate_pyproject_updates(),
                description="Update project configuration",
            ),
        ]

    def _generate_config(self) -> str:
        """Generate NADOO configuration file content.

        Returns:
            str: Configuration file content
        """
        return f"""# NADOO Framework Configuration
version = "{self.LATEST_VERSION}"

[project]
name = "nadoo-migration-framework"
description = "NADOO Migration Framework"

[migration]
backup = true
auto_commit = true
"""

    def _generate_pyproject_updates(self) -> List[Dict[str, Any]]:
        """Generate updates for pyproject.toml.

        Returns:
            List[Dict[str, Any]]: List of file modifications
        """
        return [
            {"type": "append", "content": f'\n[tool.nadoo]\nversion = "{self.LATEST_VERSION}"\n'}
        ]

    def _plan_structure_migration(self) -> List[MigrationStep]:
        """Plan migration of project structure.

        Returns:
            List[MigrationStep]: List of migration steps
        """
        steps = []

        # Ensure src directory exists
        if not (self.project_dir / "src").exists():
            steps.append(
                MigrationStep(
                    type="create_directory", path="src", description="Create src directory"
                )
            )

        # Ensure tests directory exists
        if not (self.project_dir / "tests").exists():
            steps.append(
                MigrationStep(
                    type="create_directory", path="tests", description="Create tests directory"
                )
            )

        return steps

    def _plan_version_update(self, current_version: str) -> List[MigrationStep]:
        """Plan version update steps.

        Args:
            current_version: Current project version

        Returns:
            List[MigrationStep]: List of migration steps
        """
        steps = []

        # Update version in settings.toml
        steps.append(
            MigrationStep(
                type="update_version",
                content=self.LATEST_VERSION,
                description=f"Update version from {current_version} to {self.LATEST_VERSION}",
            )
        )

        # Update dependencies
        steps.append(
            MigrationStep(
                type="modify_file",
                path="requirements.txt",
                content=self._get_required_dependencies(),
                description="Update dependencies",
            )
        )

        return steps
