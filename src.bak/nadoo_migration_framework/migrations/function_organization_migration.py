"""Migration to organize functions within Python files."""

import ast
import libcst as cst
from libcst.metadata import ParentNodeProvider, MetadataWrapper
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from nadoo_migration_framework.migrations.toga_import_migrations import FileState

class FunctionOrganizer(cst.CSTTransformer):
    """Transform function organization in a Python file."""

    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    def __init__(self):
        """Initialize the transformer."""
        super().__init__()
        self.functions = []
        self.classes = []
        self.logger = logging.getLogger(__name__)
        self.metadata = {}

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Track function definitions."""
        # Skip methods inside classes
        if not any(isinstance(parent, cst.ClassDef) for parent in self.get_parents(node)):
            self.functions.append(node)

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Track class definitions."""
        self.classes.append(node)

    def get_parents(self, node: cst.CSTNode) -> List[cst.CSTNode]:
        """Get all parent nodes of a given node."""
        parents = []
        current = node
        while True:
            try:
                parent = self.get_metadata(ParentNodeProvider, current)
                if parent is None:
                    break
                parents.append(parent)
                current = parent
            except KeyError:
                break
        return parents

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Process functions when leaving the module."""
        try:
            # Sort functions by name
            sorted_functions = sorted(self.functions, key=lambda x: x.name.value)
            
            # Sort classes by name
            sorted_classes = sorted(self.classes, key=lambda x: x.name.value)

            # Create new body with organized functions
            new_body = []

            # Add imports first (preserve existing imports)
            for node in updated_node.body:
                if isinstance(node, (cst.Import, cst.ImportFrom)):
                    new_body.append(node)

            # Add an empty line after imports if there are any
            if new_body:
                new_body.append(cst.EmptyLine())

            # Add classes
            for class_def in sorted_classes:
                new_body.append(class_def)
                new_body.append(cst.EmptyLine())

            # Add functions
            for func in sorted_functions:
                new_body.append(func)
                new_body.append(cst.EmptyLine())

            # Add remaining code that isn't a function or class
            for node in updated_node.body:
                if not isinstance(node, (cst.FunctionDef, cst.ClassDef, cst.Import, cst.ImportFrom)):
                    new_body.append(node)

            return updated_node.with_changes(body=new_body)
        except Exception as e:
            self.logger.error(f"Error organizing functions: {str(e)}")
            return updated_node

class OrganizeFunctionsMigration:
    """Migration to organize functions in Python files."""

    def __init__(self):
        """Initialize the migration."""
        self.project_dir = None
        self.original_states = {}
        self.logger = logging.getLogger(__name__)

    def set_project_dir(self, project_dir: Union[str, Path]) -> None:
        """Set the project directory."""
        self.project_dir = Path(project_dir)

    def check_if_needed(self) -> bool:
        """Check if migration is needed."""
        if not self.project_dir:
            raise ValueError("Project directory not set")

        return True

    def _up(self) -> None:
        """Organize functions in Python files."""
        try:
            # Find all Python files in the project
            python_files = list(self.project_dir.rglob("*.py"))

            for file_path in python_files:
                try:
                    # Read the file
                    code = file_path.read_text()

                    # Store original state
                    self.original_states[str(file_path)] = FileState(
                        file_path=str(file_path),
                        original_code=code
                    )

                    # Parse the code into a CST
                    module = cst.parse_module(code)
                    wrapper = MetadataWrapper(module)
                    transformer = FunctionOrganizer()
                    transformer.metadata = wrapper.resolve(ParentNodeProvider)

                    # Transform the code
                    modified_tree = wrapper.visit(transformer)

                    # Write the transformed code back to the file
                    file_path.write_text(modified_tree.code)

                    self.logger.info(f"Successfully organized functions in {file_path}")

                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {str(e)}")
                    raise
        except Exception as e:
            self.logger.error(f"Error during migration: {str(e)}")
            raise

    def _down(self) -> None:
        """Rollback the migration."""
        if not self.project_dir:
            raise ValueError("Project directory not set")

        try:
            for file_state in self.original_states.values():
                try:
                    file_path = Path(file_state.file_path)
                    if not file_path.exists():
                        raise FileNotFoundError(f"File not found: {file_path}")
                    
                    with open(file_path, "w") as f:
                        f.write(file_state.original_code)
                    self.logger.info(f"Successfully rolled back {file_path}")
                except Exception as e:
                    self.logger.error(f"Error rolling back {file_state.file_path}: {str(e)}")
                    raise
        except Exception as e:
            self.logger.error(f"Error during rollback: {str(e)}")
            raise
