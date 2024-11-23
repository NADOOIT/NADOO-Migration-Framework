"""Migrations for managing imports in Toga applications."""

from pathlib import Path
from typing import Dict, List, Optional, Set
import ast
import libcst as cst
from ..base import Migration

class ConsolidateImportsMigration(Migration):
    """Consolidate and clean up imports."""

    def __init__(self):
        """Initialize migration."""
        super().__init__()
        self.version = "0.3.3"
        self.original_states: Dict[str, FileState] = {}

    def check_if_needed(self) -> bool:
        """Check if migration is needed."""
        if not self.project_dir:
            raise ValueError("Project directory not set")

        # Check if any Python files have unused imports
        for py_file in self.project_dir.rglob("*.py"):
            if self._has_unused_imports(py_file):
                return True
        return False

    def _has_unused_imports(self, file_path: Path) -> bool:
        """Check if file has unused imports."""
        try:
            with open(file_path) as f:
                tree = ast.parse(f.read())

            # Get all imports
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.add(name.asname or name.name)
                elif isinstance(node, ast.ImportFrom):
                    for name in node.names:
                        imports.add(name.asname or name.name)

            # Get all used names
            used = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used.add(node.id)
                elif isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        used.add(node.value.id)

            # Check for unused imports
            return bool(imports - used)
        except Exception:
            return False

    def _up(self) -> None:
        """Consolidate and clean up imports."""
        if not self.project_dir:
            raise ValueError("Project directory not set")

        # Process each Python file
        for py_file in self.project_dir.rglob("*.py"):
            try:
                with open(py_file) as f:
                    code = f.read()

                # Store original state
                self.original_states[str(py_file)] = FileState(
                    file_path=str(py_file),
                    original_code=code
                )

                # Parse and transform imports
                tree = cst.parse_module(code)
                transformer = ImportTransformer()
                tree = transformer.visit(tree)  # First pass to collect used names
                tree = transformer.transform(tree)  # Second pass to remove unused imports

                # Write back cleaned up code
                with open(py_file, "w") as f:
                    f.write(tree.code)

            except Exception as e:
                print(f"Error processing {py_file}: {e}")

    def _down(self) -> None:
        """Rollback the migration."""
        if not self.project_dir:
            raise ValueError("Project directory not set")

        # Restore original states
        for state in self.original_states.values():
            with open(state.file_path, "w") as f:
                f.write(state.original_code)

class ImportTransformer(cst.CSTTransformer):
    """Transform imports in Python code."""

    def __init__(self):
        """Initialize transformer."""
        super().__init__()
        self.used_names: Set[str] = set()
        self.used_from_imports: Dict[str, Set[str]] = {}
        self.imported_names: Dict[str, str] = {}

    def visit_Name(self, node: cst.Name) -> None:
        """Track used names."""
        self.used_names.add(node.value)

    def visit_Attribute(self, node: cst.Attribute) -> None:
        """Track used attributes."""
        if isinstance(node.value, cst.Name):
            self.used_names.add(node.value.value)

    def transform(self, tree: cst.Module) -> cst.Module:
        """Transform the tree to remove unused imports."""
        class ImportRemover(cst.CSTTransformer):
            def __init__(self, used_names: Set[str]):
                super().__init__()
                self.used_names = used_names

            def leave_Import(self, original_node: cst.Import, updated_node: cst.Import) -> cst.Import:
                """Remove unused imports."""
                new_names = []
                for name in updated_node.names:
                    if name.asname:
                        alias = name.asname.name.value
                    else:
                        alias = name.name.value.split(".")[0]  # Handle module imports like 'import toga'
                    if alias in self.used_names:
                        new_names.append(name)

                if not new_names:
                    return cst.RemoveFromParent()
                return updated_node.with_changes(names=new_names)

            def leave_ImportFrom(self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom) -> cst.ImportFrom:
                """Remove unused from imports."""
                new_names = []
                for name in updated_node.names:
                    if name.asname:
                        alias = name.asname.name.value
                    else:
                        alias = name.name.value
                    if alias in self.used_names:
                        new_names.append(name)

                if not new_names:
                    return cst.RemoveFromParent()
                return updated_node.with_changes(names=new_names)

        return tree.visit(ImportRemover(self.used_names))

class FileState:
    """State of a file during migration."""

    def __init__(self, file_path: str, original_code: str):
        """Initialize file state."""
        self.file_path = file_path
        self.original_code = original_code
