"""NADOO Framework migration engine."""

import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import toml

from ..analyzers import NADOOProjectAnalyzer
from ..version_management import Version


@dataclass
class MigrationPlan:
    """Plan for migrating a project."""
    steps: List[Dict[str, Any]]
    backup_needed: bool = True
    estimated_time: int = 0  # in seconds
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "steps": self.steps,
            "backup_needed": self.backup_needed,
            "estimated_time": self.estimated_time
        }


class MigrationEngine:
    """Handles project migrations."""
    
    def __init__(self, project_dir: Path):
        """Initialize migration engine.
        
        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = project_dir
        self.backup_dir = project_dir / ".nadoo" / "backups"
        
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
            if item.name != ".nadoo" and item.name != "__pycache__":
                if item.is_dir():
                    shutil.copytree(item, backup_path / item.name)
                else:
                    shutil.copy2(item, backup_path / item.name)
                    
        return backup_path
    
    def plan_migration(self) -> MigrationPlan:
        """Create a migration plan for the project.
        
        Returns:
            MigrationPlan: The planned migration steps
        """
        steps = []
        
        # Check if it's already a NADOO project
        if (self.project_dir / "pyproject.toml").exists():
            with open(self.project_dir / "pyproject.toml") as f:
                try:
                    data = toml.load(f)
                    if "tool" in data and "poetry" in data["tool"]:
                        if "nadoo-migration-framework" in data["tool"]["poetry"].get("dependencies", {}):
                            analyzer = NADOOProjectAnalyzer(self.project_dir)
                            # Plan version update if needed
                            steps.extend(self._plan_version_update(data))
                            return MigrationPlan(steps=steps, backup_needed=True, estimated_time=30)
                except Exception as e:
                    print(f"Warning: Error reading pyproject.toml: {e}")
        
        # Plan new project setup
        steps.extend(self._plan_initial_setup())
        
        # Add structure migrations
        steps.extend(self._plan_structure_migration())
        
        return MigrationPlan(steps=steps, backup_needed=True, estimated_time=60)
    
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
    
    def _execute_step(self, step: Dict[str, Any]) -> None:
        """Execute a single migration step.
        
        Args:
            step: The migration step to execute
        """
        step_type = step["type"]
        description = step.get("description", "Executing migration step")
        print(f"- {description}...")
        
        try:
            if step_type == "create_directory":
                os.makedirs(self.project_dir / step["path"], exist_ok=True)
                
            elif step_type == "create_file":
                path = self.project_dir / step["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w") as f:
                    f.write(step["content"])
                    
            elif step_type == "modify_file":
                path = self.project_dir / step["path"]
                if path.exists():
                    with open(path) as f:
                        content = f.read()
                    
                    for mod in step["modifications"]:
                        if mod["type"] == "replace":
                            content = content.replace(mod["old"], mod["new"])
                        elif mod["type"] == "append":
                            content += "\n" + mod["content"]
                            
                    with open(path, "w") as f:
                        f.write(content)
                else:
                    with open(path, "w") as f:
                        if "content" in step:
                            f.write(step["content"])
        except Exception as e:
            raise RuntimeError(f"Failed to execute step '{description}': {str(e)}")
    
    def _plan_initial_setup(self) -> List[Dict[str, Any]]:
        """Plan initial project setup steps.
        
        Returns:
            List[Dict[str, Any]]: List of migration steps
        """
        return [
            {
                "type": "create_directory",
                "path": ".nadoo",
                "description": "Create NADOO configuration directory"
            },
            {
                "type": "create_directory",
                "path": ".nadoo/backups",
                "description": "Create backup directory"
            },
            {
                "type": "create_file",
                "path": ".nadoo/config.toml",
                "content": self._generate_config(),
                "description": "Create NADOO configuration file"
            },
            {
                "type": "modify_file",
                "path": "pyproject.toml",
                "modifications": self._generate_pyproject_updates(),
                "description": "Update project configuration"
            }
        ]
    
    def _generate_config(self) -> str:
        """Generate NADOO configuration file content.
        
        Returns:
            str: Configuration file content
        """
        return """# NADOO Framework Configuration
version = "0.2.1"

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
            {
                "type": "append",
                "content": '\n[tool.nadoo]\nversion = "0.2.1"\n'
            }
        ]
    
    def _plan_structure_migration(self) -> List[Dict[str, Any]]:
        """Plan migration of project structure.
        
        Returns:
            List[Dict[str, Any]]: List of migration steps
        """
        steps = []
        
        # Ensure src directory exists
        if not (self.project_dir / "src").exists():
            steps.append({
                "type": "create_directory",
                "path": "src",
                "description": "Create src directory"
            })
        
        # Ensure tests directory exists
        if not (self.project_dir / "tests").exists():
            steps.append({
                "type": "create_directory",
                "path": "tests",
                "description": "Create tests directory"
            })
        
        return steps
    
    def _plan_version_update(self, pyproject_data: dict) -> List[Dict[str, Any]]:
        """Plan version update if needed.
        
        Args:
            pyproject_data: Current pyproject.toml data
            
        Returns:
            List[Dict[str, Any]]: List of migration steps
        """
        steps = []
        current_version = Version.from_string(pyproject_data["tool"]["poetry"]["version"])
        latest_version = Version.from_string("0.2.1")
        
        if current_version < latest_version:
            steps.append({
                "type": "modify_file",
                "path": "pyproject.toml",
                "modifications": [
                    {
                        "type": "replace",
                        "old": f'version = "{current_version}"',
                        "new": f'version = "{latest_version}"'
                    }
                ],
                "description": f"Update version from {current_version} to {latest_version}"
            })
        
        return steps
