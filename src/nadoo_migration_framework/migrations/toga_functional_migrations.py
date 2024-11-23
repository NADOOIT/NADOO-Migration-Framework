"""Migrations for transforming Toga applications into a functional architecture."""

from pathlib import Path
from typing import Dict, List, Optional, Set
import ast
import toml
from dataclasses import dataclass
from nadoo_migration_framework.base import Migration

class CreateFunctionDirectoryMigration(Migration):
    """Create the functions directory structure."""

    def __init__(self):
        """Initialize migration."""
        super().__init__()
        self.version = "0.3.0"
        self.created_dirs: List[Path] = []

    def check_if_needed(self) -> bool:
        """Check if migration is needed."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        functions_dir = self.project_dir / "src" / "functions"
        return not functions_dir.exists()

    def _up(self) -> None:
        """Create functions directory structure."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        # Create functions directory
        functions_dir = self.project_dir / "src" / "functions"
        functions_dir.mkdir(parents=True, exist_ok=True)
        self.created_dirs.append(functions_dir)
        
        # Create __init__.py
        init_file = functions_dir / "__init__.py"
        init_file.touch()

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

class ExtractCurriedFunctionsMigration(Migration):
    """Extract curried functions to separate modules."""

    def __init__(self):
        """Initialize migration."""
        super().__init__()
        self.version = "0.3.1"
        self.original_states: Dict[str, Dict[str, FunctionState]] = {}

    def check_if_needed(self) -> bool:
        """Check if migration is needed."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        # Check if any Python files contain curried functions
        for py_file in self.project_dir.rglob("*.py"):
            if self._has_curried_functions(py_file):
                return True
        return False

    def _has_curried_functions(self, file_path: Path) -> bool:
        """Check if file contains curried functions."""
        try:
            with open(file_path) as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if function returns a lambda
                    for child in ast.walk(node):
                        if isinstance(child, ast.Lambda):
                            return True
        except Exception:
            pass
        return False

    def _up(self) -> None:
        """Extract curried functions to separate modules."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
            
        functions_dir = self.project_dir / "src" / "functions"
        if not functions_dir.exists():
            raise ValueError("Functions directory not found")
            
        # Process each Python file
        for py_file in self.project_dir.rglob("*.py"):
            if py_file.parent == functions_dir:
                continue
                
            try:
                with open(py_file) as f:
                    code = f.read()
                    tree = ast.parse(code)
                    
                # Find curried functions
                functions = {}
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Check if function returns a lambda
                        for child in ast.walk(node):
                            if isinstance(child, ast.Lambda):
                                functions[node.name] = FunctionState(
                                    name=node.name,
                                    original_code=code,
                                    new_file=str(functions_dir / f"{node.name}.py")
                                )
                                break
                
                if functions:
                    self.original_states[str(py_file)] = functions
                    
                    # Extract each function
                    for func_name, state in functions.items():
                        # Create new module for function
                        with open(state.new_file, "w") as f:
                            f.write(f"""from typing import TypeVar, Callable

T = TypeVar('T')
U = TypeVar('U')

def {func_name}(x: T) -> Callable[[U], T]:
    \"\"\"Curried function that takes x and returns a function that takes y.
    
    Args:
        x: First argument
        
    Returns:
        Function that takes second argument y and returns result
    \"\"\"
    return lambda y: x + y  # TODO: Replace with actual implementation
""")
                        
                        # Remove function from original file
                        with open(py_file) as f:
                            code = f.read()
                        
                        # TODO: Use libcst to properly remove function
                        lines = code.split("\n")
                        new_lines = []
                        skip = False
                        for line in lines:
                            if f"def {func_name}" in line:
                                skip = True
                            elif skip and line and not line[0].isspace():
                                skip = False
                            if not skip:
                                new_lines.append(line)
                        
                        with open(py_file, "w") as f:
                            f.write("\n".join(new_lines))
                        
            except Exception as e:
                print(f"Error processing {py_file}: {e}")

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

class ExtractRegularFunctionsMigration(Migration):
    """Extract regular functions to separate files."""

    def __init__(self):
        """Initialize migration."""
        super().__init__()
        self.version = "0.3.2"
        self.original_states: Dict[str, FileState] = {}
        self.created_files: List[str] = []

    def check_if_needed(self) -> bool:
        """Check if migration is needed."""
        if not self.project_dir:
            raise ValueError("Project directory not set")

        # Check if functions directory exists
        functions_dir = self.project_dir / "src" / "functions"
        if not functions_dir.exists():
            return False

        # Check for regular functions in Python files
        for py_file in self.project_dir.rglob("*.py"):
            if py_file.parent == functions_dir:
                continue
            if self._has_regular_functions(py_file):
                return True
        return False

    def _has_regular_functions(self, file_path: Path) -> bool:
        """Check if file has regular functions."""
        try:
            with open(file_path) as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Skip if it's a method
                    is_method = False
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.ClassDef) and node in parent.body:
                            is_method = True
                            break
                    if is_method:
                        continue

                    # Skip if it's a curried function
                    is_curried = False
                    for child in node.body:
                        if isinstance(child, ast.Return) and isinstance(child.value, ast.Lambda):
                            is_curried = True
                            break
                    if not is_curried:
                        return True
            return False
        except Exception:
            return False

    def _up(self) -> None:
        """Extract regular functions to separate files."""
        if not self.project_dir:
            raise ValueError("Project directory not set")

        functions_dir = self.project_dir / "src" / "functions"
        if not functions_dir.exists():
            raise ValueError("Functions directory does not exist")

        # Process each Python file
        for py_file in self.project_dir.rglob("*.py"):
            if py_file.parent == functions_dir:
                continue

            try:
                with open(py_file) as f:
                    code = f.read()

                # Store original state
                self.original_states[str(py_file)] = FileState(
                    file_path=str(py_file),
                    original_code=code
                )

                # Parse and transform
                tree = cst.parse_module(code)
                transformer = RegularFunctionTransformer(functions_dir)
                modified_tree = tree.visit(transformer)

                # Write back modified code
                with open(py_file, "w") as f:
                    f.write(modified_tree.code)

                # Track created files
                self.created_files.extend([str(functions_dir / f"{name}.py") for name in transformer.functions_to_remove])

            except Exception as e:
                print(f"Error processing {py_file}: {e}")

    def _down(self) -> None:
        """Rollback the migration."""
        if not self.project_dir:
            raise ValueError("Project directory not set")

        # Remove created files
        for file_path in self.created_files:
            try:
                Path(file_path).unlink()
            except Exception as e:
                print(f"Error removing {file_path}: {e}")

        # Restore original states
        for state in self.original_states.values():
            with open(state.file_path, "w") as f:
                f.write(state.original_code)

class RegularFunctionTransformer(cst.CSTVisitor):
    """Transform regular functions."""

    def __init__(self, functions_dir: Path):
        """Initialize transformer."""
        super().__init__()
        self.functions_dir = functions_dir
        self.in_class = False
        self.imports = []
        self.functions_to_remove = []

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Track when we're inside a class."""
        self.in_class = True

    def leave_ClassDef(self, original_node: cst.ClassDef) -> cst.ClassDef:
        """Track when we leave a class."""
        self.in_class = False
        return original_node

    def visit_Import(self, node: cst.Import) -> None:
        """Track imports."""
        self.imports.append(node)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        """Track from imports."""
        self.imports.append(node)

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> cst.FunctionDef:
        """Extract regular functions."""
        if self.in_class:
            return original_node

        # Skip if it's a curried function
        has_lambda_return = False
        for node in original_node.body.body:
            if isinstance(node, cst.Return) and isinstance(node.value, cst.Lambda):
                has_lambda_return = True
                break

        if has_lambda_return:
            return original_node

        # Create new file for function
        func_file = self.functions_dir / f"{original_node.name.value}.py"
        
        # Generate imports
        imports_str = ""
        for imp in self.imports:
            imports_str += cst.Module([imp]).code

        # Write function to new file
        with open(func_file, "w") as f:
            if imports_str:
                f.write(imports_str + "\n")
            f.write(cst.Module([original_node]).code)

        # Mark function for removal
        self.functions_to_remove.append(original_node.name.value)

        # Replace function with import
        return cst.ImportFrom(
            module=cst.Name("functions"),
            names=[cst.ImportAlias(name=cst.Name(original_node.name.value))],
            relative=[]
        )

class FunctionState:
    """State of a function during migration."""

    def __init__(self, name: str, original_code: str, new_file: str):
        """Initialize function state."""
        self.name = name
        self.original_code = original_code
        self.new_file = new_file

class FileState:
    """State of a file during migration."""

    def __init__(self, file_path: str, original_code: str):
        """Initialize file state."""
        self.file_path = file_path
        self.original_code = original_code
