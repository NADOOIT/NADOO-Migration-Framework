"""Migrations for managing imports in Toga apps."""

from pathlib import Path
from typing import Dict, List, Optional, Set
import ast
import toml
from dataclasses import dataclass

from ..base import Migration
from ..frameworks.toga_functional_migrator import TogaFunctionalMigrator

@dataclass
class ImportState:
    """State of imports before/after migration."""
    file_path: str
    original_code: str
    version: str

class ConsolidateImportsMigration(Migration):
    """Migration to consolidate and clean up imports after function extraction."""
    
    version = "0.3.3"
    description = "Consolidate and clean up imports"
    
    def __init__(self):
        super().__init__()
        self.migrator: Optional[TogaFunctionalMigrator] = None
        self.original_states: Dict[str, ImportState] = {}
        self.used_imports: Dict[str, Set[str]] = {}
        
    def check_if_needed(self) -> bool:
        """Check if this migration is needed."""
        if not self.project_dir:
            return False
            
        self.migrator = TogaFunctionalMigrator(self.project_dir)
        
        # Check for unused or duplicate imports
        for py_file in self.migrator.find_python_files():
            with open(py_file) as f:
                content = f.read()
            tree = ast.parse(content)
            
            imports = set()
            used_names = set()
            
            # Collect imports
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for name in node.names:
                        if name.asname:
                            imports.add(name.asname)
                        else:
                            imports.add(name.name)
                elif isinstance(node, ast.Name):
                    used_names.add(node.id)
                    
            # Check for unused imports
            if any(imp not in used_names for imp in imports):
                return True
                
        return False
        
    def _analyze_imports(self, file_path: Path) -> Set[str]:
        """Analyze which imports are actually used in a file."""
        with open(file_path) as f:
            content = f.read()
        tree = ast.parse(content)
        
        imports = {}  # name -> full import statement
        used_names = set()
        
        # Collect imports and their usage
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports[name.asname or name.name] = name.name
            elif isinstance(node, ast.ImportFrom):
                for name in node.names:
                    full_name = f"{node.module}.{name.name}" if node.module else name.name
                    imports[name.asname or name.name] = full_name
            elif isinstance(node, ast.Name):
                used_names.add(node.id)
                
        # Return only the imports that are actually used
        return {imports[name] for name in imports if name in used_names}
        
    def _up(self) -> None:
        """Consolidate and clean up imports."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        self.migrator = TogaFunctionalMigrator(self.project_dir)
        
        # Store original state and analyze imports
        for py_file in self.migrator.find_python_files():
            with open(py_file) as f:
                content = f.read()
                
            self.original_states[str(py_file)] = ImportState(
                file_path=str(py_file),
                original_code=content,
                version=self.version
            )
            
            # Analyze used imports
            self.used_imports[str(py_file)] = self._analyze_imports(py_file)
            
            # Update the file with cleaned imports
            self._update_file_imports(py_file)
            
        # Update pyproject.toml version
        if (self.project_dir / "pyproject.toml").exists():
            with open(self.project_dir / "pyproject.toml") as f:
                data = toml.load(f)
            data["tool"]["briefcase"]["version"] = self.version
            with open(self.project_dir / "pyproject.toml", "w") as f:
                toml.dump(data, f)
                
    def _update_file_imports(self, file_path: Path) -> None:
        """Update a file's imports to only include used ones."""
        used = self.used_imports[str(file_path)]
        
        # Generate new import statements
        imports = []
        from_imports = {}  # module -> [names]
        
        for imp in sorted(used):
            if '.' in imp:
                module, name = imp.rsplit('.', 1)
                if module not in from_imports:
                    from_imports[module] = []
                from_imports[module].append(name)
            else:
                imports.append(f"import {imp}")
                
        # Generate from imports
        for module, names in sorted(from_imports.items()):
            names_str = ', '.join(sorted(names))
            imports.append(f"from {module} import {names_str}")
            
        # Read the original file
        with open(file_path) as f:
            content = f.read()
            
        # Parse the file
        tree = ast.parse(content)
        
        # Remove all existing imports
        new_body = []
        for node in tree.body:
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                new_body.append(node)
                
        # Add new imports at the top
        import_nodes = ast.parse('\n'.join(imports)).body
        new_body = import_nodes + new_body
        
        # Write the updated file
        with open(file_path, 'w') as f:
            f.write(ast.unparse(ast.Module(body=new_body, type_ignores=[])))
            
    def _down(self) -> None:
        """Rollback the migration."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        # Restore original states
        for state in self.original_states.values():
            with open(state.file_path, 'w') as f:
                f.write(state.original_code)
                
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
                path: {
                    "file_path": state.file_path,
                    "original_code": state.original_code,
                    "version": state.version
                }
                for path, state in self.original_states.items()
            },
            "used_imports": {
                path: list(imports)
                for path, imports in self.used_imports.items()
            }
        }
