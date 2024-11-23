"""Migrations for Briefcase Toga apps."""

from pathlib import Path
from typing import Dict, List, Optional
import ast
import toml
from dataclasses import dataclass

from ..base import Migration
from ..frameworks.toga_app import BriefcaseTogaMigrator, ViewTransformation

@dataclass
class ViewState:
    """State of a view before/after migration."""
    view_file: str
    logic_file: str
    view_code: str
    logic_code: str
    version: str

class SeparateViewLogicMigration(Migration):
    """Migration to separate Toga views from business logic."""
    
    version = "0.2.0"
    description = "Separate GUI views from business logic in Toga apps"
    
    def __init__(self):
        super().__init__()
        self.migrator: Optional[BriefcaseTogaMigrator] = None
        self.transformations: List[ViewTransformation] = []
        self.original_states: Dict[str, ViewState] = {}
        
    def check_if_needed(self) -> bool:
        """Check if this migration is needed."""
        if not self.project_dir:
            return False
            
        self.migrator = BriefcaseTogaMigrator(self.project_dir)
        
        # Check if any view files have business logic
        view_files = self.migrator.find_view_files()
        for file_path in view_files:
            with open(file_path) as f:
                content = f.read()
            tree = ast.parse(content)
            
            # Check for non-GUI methods in view classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id in {'Window', 'Box', 'ScrollContainer', 'SplitContainer'}:
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    if not self._is_gui_method(item):
                                        return True
        return False
        
    def _is_gui_method(self, node: ast.FunctionDef) -> bool:
        """Check if a method is GUI-related."""
        gui_prefixes = {'on_', 'handle_', 'create_', 'update_ui_', 'refresh_', 'startup', 'shutdown'}
        if any(node.name.startswith(prefix) for prefix in gui_prefixes):
            return True
            
        # Check for Toga usage
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and any(toga_name in child.id for toga_name in ['toga', 'Window', 'Box', 'Button', 'TextInput']):
                return True
        return False
        
    def _up(self) -> None:
        """Migrate view classes to separate GUI and logic."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        self.migrator = BriefcaseTogaMigrator(self.project_dir)
        
        # Store original state
        view_files = self.migrator.find_view_files()
        for file_path in view_files:
            with open(file_path) as f:
                content = f.read()
                
            # Store original state before transformation
            self.original_states[str(file_path)] = ViewState(
                view_file=str(file_path),
                logic_file=str(self.migrator.logic_dir / f"{file_path.stem.lower()}_logic.py"),
                view_code=content,
                logic_code="",
                version=self.version
            )
        
        # Apply transformations
        self.transformations = self.migrator.migrate_project()
        
        # Update pyproject.toml version
        if (self.project_dir / "pyproject.toml").exists():
            with open(self.project_dir / "pyproject.toml") as f:
                data = toml.load(f)
            data["tool"]["briefcase"]["version"] = self.version
            with open(self.project_dir / "pyproject.toml", "w") as f:
                toml.dump(data, f)
                
    def _down(self) -> None:
        """Rollback the migration."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        # Restore original states
        for state in self.original_states.values():
            # Restore view file
            with open(state.view_file, 'w') as f:
                f.write(state.view_code)
                
            # Remove logic file if it exists
            logic_path = Path(state.logic_file)
            if logic_path.exists():
                logic_path.unlink()
                
        # Update pyproject.toml version
        if (self.project_dir / "pyproject.toml").exists():
            with open(self.project_dir / "pyproject.toml") as f:
                data = toml.load(f)
            # Revert to previous version
            parts = data["tool"]["briefcase"]["version"].split('.')
            parts[-1] = str(int(parts[-1]) - 1)
            data["tool"]["briefcase"]["version"] = '.'.join(parts)
            with open(self.project_dir / "pyproject.toml", "w") as f:
                toml.dump(data, f)
                
    def get_state(self) -> Dict:
        """Get the current state of the migration."""
        return {
            "version": self.version,
            "original_states": {
                path: {
                    "view_file": state.view_file,
                    "logic_file": state.logic_file,
                    "view_code": state.view_code,
                    "logic_code": state.logic_code,
                    "version": state.version
                }
                for path, state in self.original_states.items()
            },
            "transformations": [
                {
                    "view_file": t.view_file,
                    "logic_file": t.logic_file,
                    "description": t.description
                }
                for t in self.transformations
            ]
        }
        
class UpdateViewImportsMigration(Migration):
    """Migration to update imports in Toga view files."""
    
    version = "0.2.1"
    description = "Update imports in Toga view files"
    
    def __init__(self):
        super().__init__()
        self.migrator: Optional[BriefcaseTogaMigrator] = None
        self.original_states: Dict[str, str] = {}
        
    def check_if_needed(self) -> bool:
        """Check if this migration is needed."""
        if not self.project_dir:
            return False
            
        self.migrator = BriefcaseTogaMigrator(self.project_dir)
        
        # Check if any view files have old-style imports
        view_files = self.migrator.find_view_files()
        for file_path in view_files:
            with open(file_path) as f:
                content = f.read()
            if "from views." in content or "from logic." not in content:
                return True
        return False
        
    def _up(self) -> None:
        """Update imports in view files."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        self.migrator = BriefcaseTogaMigrator(self.project_dir)
        
        # Store original state
        view_files = self.migrator.find_view_files()
        for file_path in view_files:
            with open(file_path) as f:
                self.original_states[str(file_path)] = f.read()
                
        # Update imports using common Toga app patterns
        old_to_new = {
            "views": "logic",
            "utils": "logic.utils",
            "helpers": "logic.helpers"
        }
        
        for file_path in view_files:
            self.migrator.update_imports(file_path, old_to_new)
            
        # Update pyproject.toml version
        if (self.project_dir / "pyproject.toml").exists():
            with open(self.project_dir / "pyproject.toml") as f:
                data = toml.load(f)
            data["tool"]["briefcase"]["version"] = self.version
            with open(self.project_dir / "pyproject.toml", "w") as f:
                toml.dump(data, f)
                
    def _down(self) -> None:
        """Rollback the migration."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        # Restore original states
        for file_path, content in self.original_states.items():
            with open(file_path, 'w') as f:
                f.write(content)
                
        # Update pyproject.toml version
        if (self.project_dir / "pyproject.toml").exists():
            with open(self.project_dir / "pyproject.toml") as f:
                data = toml.load(f)
            # Revert to previous version
            parts = data["tool"]["briefcase"]["version"].split('.')
            parts[-1] = str(int(parts[-1]) - 1)
            data["tool"]["briefcase"]["version"] = '.'.join(parts)
            with open(self.project_dir / "pyproject.toml", "w") as f:
                toml.dump(data, f)
                
    def get_state(self) -> Dict:
        """Get the current state of the migration."""
        return {
            "version": self.version,
            "original_states": self.original_states
        }
