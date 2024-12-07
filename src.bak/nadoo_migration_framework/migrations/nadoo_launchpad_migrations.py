"""NADOO-Launchpad specific migrations."""

from pathlib import Path
from typing import Dict, List, Optional
import ast
import toml
from dataclasses import dataclass

from ..base import Migration
from ..frameworks.nadoo_launchpad import NADOOLaunchpadMigrator, ElementTransformation

@dataclass
class ElementState:
    """State of an Element before/after migration."""
    element_file: str
    logic_file: str
    element_code: str
    logic_code: str
    version: str

class SeparateElementLogicMigration(Migration):
    """Migration to separate GUI elements from business logic."""
    
    version = "0.2.0"
    description = "Separate GUI elements from business logic in NADOO-Launchpad"
    
    def __init__(self):
        super().__init__()
        self.migrator: Optional[NADOOLaunchpadMigrator] = None
        self.transformations: List[ElementTransformation] = []
        self.original_states: Dict[str, ElementState] = {}
        
    def check_if_needed(self) -> bool:
        """Check if this migration is needed."""
        if not self.migrator:
            return False
            
        # Check if any Element files have business logic
        element_files = self.migrator.find_element_files()
        for file_path in element_files:
            with open(file_path) as f:
                content = f.read()
            tree = ast.parse(content)
            
            # Check for non-GUI methods in Element classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.endswith('Element'):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if not self._is_gui_method(item):
                                return True
        return False
        
    def _is_gui_method(self, node: ast.FunctionDef) -> bool:
        """Check if a method is GUI-related."""
        gui_prefixes = {'on_', 'handle_', 'create_', 'update_ui_', 'refresh_'}
        if any(node.name.startswith(prefix) for prefix in gui_prefixes):
            return True
            
        # Check for Toga usage
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and 'toga' in child.id:
                return True
        return False
        
    def _up(self) -> None:
        """Migrate Element classes to separate GUI and logic."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        self.migrator = NADOOLaunchpadMigrator(self.project_dir)
        
        # Store original state
        element_files = self.migrator.find_element_files()
        for file_path in element_files:
            with open(file_path) as f:
                content = f.read()
                
            # Store original state before transformation
            self.original_states[str(file_path)] = ElementState(
                element_file=str(file_path),
                logic_file=str(self.migrator.functions_dir / f"{file_path.stem.lower()}_logic.py"),
                element_code=content,
                logic_code="",
                version=self.version
            )
        
        # Apply transformations
        self.transformations = self.migrator.migrate_project()
        
        # Update pyproject.toml version
        if (self.project_dir / "pyproject.toml").exists():
            with open(self.project_dir / "pyproject.toml") as f:
                data = toml.load(f)
            data["tool"]["poetry"]["version"] = self.version
            with open(self.project_dir / "pyproject.toml", "w") as f:
                toml.dump(data, f)
                
    def _down(self) -> None:
        """Rollback the migration."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        # Restore original states
        for state in self.original_states.values():
            # Restore Element file
            with open(state.element_file, 'w') as f:
                f.write(state.element_code)
                
            # Remove logic file if it exists
            logic_path = Path(state.logic_file)
            if logic_path.exists():
                logic_path.unlink()
                
        # Update pyproject.toml version
        if (self.project_dir / "pyproject.toml").exists():
            with open(self.project_dir / "pyproject.toml") as f:
                data = toml.load(f)
            # Revert to previous version
            parts = data["tool"]["poetry"]["version"].split('.')
            parts[-1] = str(int(parts[-1]) - 1)
            data["tool"]["poetry"]["version"] = '.'.join(parts)
            with open(self.project_dir / "pyproject.toml", "w") as f:
                toml.dump(data, f)
                
    def get_state(self) -> Dict:
        """Get the current state of the migration."""
        return {
            "version": self.version,
            "original_states": {
                path: {
                    "element_file": state.element_file,
                    "logic_file": state.logic_file,
                    "element_code": state.element_code,
                    "logic_code": state.logic_code,
                    "version": state.version
                }
                for path, state in self.original_states.items()
            },
            "transformations": [
                {
                    "element_file": t.element_file,
                    "logic_file": t.logic_file,
                    "description": t.description
                }
                for t in self.transformations
            ]
        }
        
class UpdateElementImportsMigration(Migration):
    """Migration to update imports in Element files using Watchdog patterns."""
    
    version = "0.2.1"
    description = "Update imports in NADOO-Launchpad Element files"
    
    def __init__(self):
        super().__init__()
        self.migrator: Optional[NADOOLaunchpadMigrator] = None
        self.original_states: Dict[str, str] = {}
        
    def check_if_needed(self) -> bool:
        """Check if this migration is needed."""
        if not self.migrator:
            return False
            
        # Check if any Element files have old-style imports
        element_files = self.migrator.find_element_files()
        for file_path in element_files:
            with open(file_path) as f:
                content = f.read()
            if "from classes." in content or "from functions." not in content:
                return True
        return False
        
    def _up(self) -> None:
        """Update imports in Element files."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        self.migrator = NADOOLaunchpadMigrator(self.project_dir)
        
        # Store original state
        element_files = self.migrator.find_element_files()
        for file_path in element_files:
            with open(file_path) as f:
                self.original_states[str(file_path)] = f.read()
                
        # Update imports using Watchdog patterns
        old_to_new = {
            "classes": "functions",
            "utils": "functions.utils",
            "helpers": "functions.helpers"
        }
        
        for file_path in element_files:
            self.migrator.update_imports(file_path, old_to_new)
            
        # Update pyproject.toml version
        if (self.project_dir / "pyproject.toml").exists():
            with open(self.project_dir / "pyproject.toml") as f:
                data = toml.load(f)
            data["tool"]["poetry"]["version"] = self.version
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
            parts = data["tool"]["poetry"]["version"].split('.')
            parts[-1] = str(int(parts[-1]) - 1)
            data["tool"]["poetry"]["version"] = '.'.join(parts)
            with open(self.project_dir / "pyproject.toml", "w") as f:
                toml.dump(data, f)
                
    def get_state(self) -> Dict:
        """Get the current state of the migration."""
        return {
            "version": self.version,
            "original_states": self.original_states
        }
