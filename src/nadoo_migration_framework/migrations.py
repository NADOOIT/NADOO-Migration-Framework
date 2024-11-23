"""NADOO Framework migration system."""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any

import toml

from .analyzers import NADOOProjectAnalyzer, NonNADOOProjectAnalyzer
from .version_management import Version


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
        self.project_dir = project_dir
        self.backup_dir = project_dir / ".nadoo" / "backups"
        
    def create_backup(self) -> Path:
        """Create a backup of the project."""
        from datetime import datetime
        
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
        """Create a migration plan for the project."""
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
                except Exception:
                    pass
        
        # Plan new project setup
        steps.extend([
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
        ])
        
        # Add structure migrations
        steps.extend(self._plan_structure_migration())
        
        return MigrationPlan(steps=steps, backup_needed=True, estimated_time=60)
    
    def execute_plan(self, plan: MigrationPlan) -> bool:
        """Execute a migration plan."""
        if plan.backup_needed:
            backup_path = self.create_backup()
            print(f"Created backup at {backup_path}")
        
        try:
            for step in plan.steps:
                self._execute_step(step)
            return True
        except Exception as e:
            print(f"Error during migration: {e}")
            if plan.backup_needed:
                print(f"Restore from backup at {backup_path}")
            return False
    
    def _execute_step(self, step: Dict[str, Any]):
        """Execute a single migration step."""
        step_type = step["type"]
        
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
    
    def _generate_config(self) -> str:
        """Generate NADOO configuration file content."""
        return """# NADOO Framework Configuration
version = "0.1.2"

[project]
name = "nadoo-migration-framework"
description = "NADOO Migration Framework"

[migration]
backup = true
auto_commit = true
"""
    
    def _generate_pyproject_updates(self) -> List[Dict[str, Any]]:
        """Generate updates for pyproject.toml."""
        return [
            {
                "type": "append",
                "content": '\n[tool.nadoo]\nversion = "0.1.2"\n'
            }
        ]
    
    def _plan_structure_migration(self) -> List[Dict[str, Any]]:
        """Plan migration of project structure."""
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
        """Plan version update if needed."""
        steps = []
        current_version = Version.from_string(pyproject_data["tool"]["poetry"]["version"])
        latest_version = Version(0, 1, 2)  # TODO: Get from PyPI
        
        if current_version < latest_version:
            steps.append({
                "type": "modify_file",
                "path": "pyproject.toml",
                "modifications": [{
                    "type": "replace",
                    "old": f'version = "{current_version}"',
                    "new": f'version = "{latest_version}"'
                }],
                "description": f"Update version from {current_version} to {latest_version}"
            })
        
        return steps
