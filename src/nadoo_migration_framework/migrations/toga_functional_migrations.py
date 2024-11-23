"""Migrations for converting Toga apps to functional style."""

from pathlib import Path
from typing import Dict, List, Optional
import ast
import toml
from dataclasses import dataclass

from ..base import Migration
from ..frameworks.toga_functional_migrator import TogaFunctionalMigrator, FunctionTransformation

@dataclass
class FunctionState:
    """State of a function before/after migration."""
    original_file: str
    new_file: str
    original_code: str
    function_code: str
    version: str

class CreateFunctionDirectoryMigration(Migration):
    """Migration to create the functions directory structure."""
    
    version = "0.3.0"
    description = "Create functions directory structure"
    
    def __init__(self):
        super().__init__()
        self.migrator: Optional[TogaFunctionalMigrator] = None
        self.created_dirs: List[Path] = []
        
    def check_if_needed(self) -> bool:
        """Check if this migration is needed."""
        if not self.project_dir:
            return False
            
        self.migrator = TogaFunctionalMigrator(self.project_dir)
        return not (self.migrator.functions_dir and self.migrator.functions_dir.exists())
        
    def _up(self) -> None:
        """Create functions directory structure."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        self.migrator = TogaFunctionalMigrator(self.project_dir)
        
        # Create functions directory and __init__.py
        self.migrator.functions_dir.mkdir(exist_ok=True)
        self.created_dirs.append(self.migrator.functions_dir)
        
        init_file = self.migrator.functions_dir / "__init__.py"
        init_file.touch()
        
        # Update pyproject.toml version
        if (self.project_dir / "pyproject.toml").exists():
            with open(self.project_dir / "pyproject.toml") as f:
                data = toml.load(f)
            data["tool"]["briefcase"]["version"] = self.version
            with open(self.project_dir / "pyproject.toml", "w") as f:
                toml.dump(data, f)
                
    def _down(self) -> None:
        """Remove functions directory structure."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        # Remove created directories in reverse order
        for dir_path in reversed(self.created_dirs):
            if dir_path.exists():
                # Remove all files in directory
                for file in dir_path.glob("*"):
                    file.unlink()
                dir_path.rmdir()
                
        # Update pyproject.toml version
        if (self.project_dir / "pyproject.toml").exists():
            with open(self.project_dir / "pyproject.toml") as f:
                data = toml.load(f)
            parts = data["tool"]["briefcase"]["version"].split('.')
            parts[-1] = str(int(parts[-1]) - 1)
            data["tool"]["briefcase"]["version"] = '.'.join(parts)
            with open(self.project_dir / "pyproject.toml", "w") as f:
                toml.dump(data, f)
                
    def get_state(self) -> Dict:
        """Get the current state of the migration."""
        return {
            "version": self.version,
            "created_dirs": [str(path) for path in self.created_dirs]
        }

class ExtractCurriedFunctionsMigration(Migration):
    """Migration to extract curried functions to their own modules."""
    
    version = "0.3.1"
    description = "Extract curried functions to their own modules"
    
    def __init__(self):
        super().__init__()
        self.migrator: Optional[TogaFunctionalMigrator] = None
        self.transformations: List[FunctionTransformation] = []
        self.original_states: Dict[str, Dict[str, FunctionState]] = {}
        
    def check_if_needed(self) -> bool:
        """Check if this migration is needed."""
        if not self.project_dir:
            return False
            
        self.migrator = TogaFunctionalMigrator(self.project_dir)
        
        # Check for curried functions
        for py_file in self.migrator.find_python_files():
            with open(py_file) as f:
                content = f.read()
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Return) and isinstance(child.value, ast.Lambda):
                            return True
        return False
        
    def _up(self) -> None:
        """Extract curried functions to their own modules."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        self.migrator = TogaFunctionalMigrator(self.project_dir)
        
        # Store original state and find curried functions
        for py_file in self.migrator.find_python_files():
            with open(py_file) as f:
                content = f.read()
                
            tree = ast.parse(content)
            functions = {}
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    is_curried = False
                    for child in ast.walk(node):
                        if isinstance(child, ast.Return) and isinstance(child.value, ast.Lambda):
                            is_curried = True
                            break
                            
                    if is_curried:
                        functions[node.name] = FunctionState(
                            original_file=str(py_file),
                            new_file=str(self.migrator.functions_dir / f"{node.name.lower()}.py"),
                            original_code=content,
                            function_code="",
                            version=self.version
                        )
                        
            if functions:
                self.original_states[str(py_file)] = functions
                
        # Apply transformations only for curried functions
        self.transformations = [
            t for t in self.migrator.migrate_project()
            if t.is_curried
        ]
        
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
        for file_path, functions in self.original_states.items():
            # Restore original file
            with open(file_path, 'w') as f:
                f.write(next(iter(functions.values())).original_code)
                
            # Remove function files
            for func_state in functions.values():
                func_path = Path(func_state.new_file)
                if func_path.exists():
                    func_path.unlink()
                    
        # Update pyproject.toml version
        if (self.project_dir / "pyproject.toml").exists():
            with open(self.project_dir / "pyproject.toml") as f:
                data = toml.load(f)
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
                file_path: {
                    func_name: {
                        "original_file": state.original_file,
                        "new_file": state.new_file,
                        "original_code": state.original_code,
                        "function_code": state.function_code,
                        "version": state.version
                    }
                    for func_name, state in functions.items()
                }
                for file_path, functions in self.original_states.items()
            },
            "transformations": [
                {
                    "original_file": t.original_file,
                    "new_file": t.new_file,
                    "function_name": t.function_name,
                    "is_curried": t.is_curried,
                    "description": t.description
                }
                for t in self.transformations
            ]
        }

class ExtractRegularFunctionsMigration(Migration):
    """Migration to extract regular (non-curried) functions to their own modules."""
    
    version = "0.3.2"
    description = "Extract regular functions to their own modules"
    
    def __init__(self):
        super().__init__()
        self.migrator: Optional[TogaFunctionalMigrator] = None
        self.transformations: List[FunctionTransformation] = []
        self.original_states: Dict[str, Dict[str, FunctionState]] = {}
        
    def check_if_needed(self) -> bool:
        """Check if this migration is needed."""
        if not self.project_dir:
            return False
            
        self.migrator = TogaFunctionalMigrator(self.project_dir)
        
        # Check for regular functions
        for py_file in self.migrator.find_python_files():
            with open(py_file) as f:
                content = f.read()
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    is_curried = False
                    for child in ast.walk(node):
                        if isinstance(child, ast.Return) and isinstance(child.value, ast.Lambda):
                            is_curried = True
                            break
                    if not is_curried:
                        return True
        return False
        
    def _up(self) -> None:
        """Extract regular functions to their own modules."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        self.migrator = TogaFunctionalMigrator(self.project_dir)
        
        # Store original state and find regular functions
        for py_file in self.migrator.find_python_files():
            with open(py_file) as f:
                content = f.read()
                
            tree = ast.parse(content)
            functions = {}
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    is_curried = False
                    for child in ast.walk(node):
                        if isinstance(child, ast.Return) and isinstance(child.value, ast.Lambda):
                            is_curried = True
                            break
                            
                    if not is_curried:
                        functions[node.name] = FunctionState(
                            original_file=str(py_file),
                            new_file=str(self.migrator.functions_dir / f"{node.name.lower()}.py"),
                            original_code=content,
                            function_code="",
                            version=self.version
                        )
                        
            if functions:
                self.original_states[str(py_file)] = functions
                
        # Apply transformations only for regular functions
        self.transformations = [
            t for t in self.migrator.migrate_project()
            if not t.is_curried
        ]
        
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
        for file_path, functions in self.original_states.items():
            # Restore original file
            with open(file_path, 'w') as f:
                f.write(next(iter(functions.values())).original_code)
                
            # Remove function files
            for func_state in functions.values():
                func_path = Path(func_state.new_file)
                if func_path.exists():
                    func_path.unlink()
                    
        # Update pyproject.toml version
        if (self.project_dir / "pyproject.toml").exists():
            with open(self.project_dir / "pyproject.toml") as f:
                data = toml.load(f)
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
                file_path: {
                    func_name: {
                        "original_file": state.original_file,
                        "new_file": state.new_file,
                        "original_code": state.original_code,
                        "function_code": state.function_code,
                        "version": state.version
                    }
                    for func_name, state in functions.items()
                }
                for file_path, functions in self.original_states.items()
            },
            "transformations": [
                {
                    "original_file": t.original_file,
                    "new_file": t.new_file,
                    "function_name": t.function_name,
                    "is_curried": t.is_curried,
                    "description": t.description
                }
                for t in self.transformations
            ]
        }
