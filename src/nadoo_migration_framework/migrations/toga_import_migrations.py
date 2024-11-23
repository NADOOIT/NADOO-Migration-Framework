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

        # Check for unused imports in Python files
        for py_file in self.project_dir.rglob("*.py"):
            try:
                with open(py_file) as f:
                    tree = ast.parse(f.read())

                # Collect all imports
                imports = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            imports.add(name.name)
                    elif isinstance(node, ast.ImportFrom):
                        for name in node.names:
                            imports.add(name.name)

                # Collect all used names
                used_names = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name):
                        used_names.add(node.id)
                    elif isinstance(node, ast.Attribute):
                        used_names.add(node.attr)

                # Check for unused imports
                if any(imp not in used_names for imp in imports):
                    return True

            except Exception:
                continue

        return False

    def _up(self) -> None:
        """Clean up imports."""
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

                # Parse and transform
                tree = cst.parse_module(code)
                transformer = ImportTransformer()
                modified_tree = tree.visit(transformer)

                # Write back modified code
                with open(py_file, "w") as f:
                    f.write(modified_tree.code)

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

class ImportTransformer(cst.CSTVisitor):
    """Transform imports."""

    def __init__(self):
        """Initialize transformer."""
        super().__init__()
        self.used_names = set()
        self.imports_to_remove = set()
        self.module_imports = {}

    def visit_Name(self, node: cst.Name) -> None:
        """Track used names."""
        self.used_names.add(node.value)

    def visit_Attribute(self, node: cst.Attribute) -> None:
        """Track used attributes."""
        self.used_names.add(node.attr.value)

    def visit_Import(self, node: cst.Import) -> None:
        """Track imports."""
        for name in node.names:
            if name.asname:
                imported_name = name.asname.name.value
            else:
                imported_name = name.name.value.split(".")[0]
            self.module_imports[imported_name] = node

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        """Track from imports."""
        for name in node.names:
            if name.asname:
                imported_name = name.asname.name.value
            else:
                imported_name = name.name.value
            if imported_name not in self.used_names:
                self.imports_to_remove.add(imported_name)

    def leave_Module(self, original_node: cst.Module) -> cst.Module:
        """Remove unused imports."""
        new_body = []
        for node in original_node.body:
            if isinstance(node, cst.Import):
                # Keep module imports that are used
                names = []
                for name in node.names:
                    if name.asname:
                        imported_name = name.asname.name.value
                    else:
                        imported_name = name.name.value.split(".")[0]
                    if imported_name in self.used_names:
                        names.append(name)
                if names:
                    new_body.append(node.with_changes(names=names))
            elif isinstance(node, cst.ImportFrom):
                # Keep from imports that are used
                names = [name for name in node.names if name.name.value not in self.imports_to_remove]
                if names:
                    new_body.append(node.with_changes(names=names))
            else:
                new_body.append(node)
        return original_node.with_changes(body=new_body)

class FileState:
    """State of a file during migration."""

    def __init__(self, file_path: str, original_code: str):
        """Initialize file state."""
        self.file_path = file_path
        self.original_code = original_code
