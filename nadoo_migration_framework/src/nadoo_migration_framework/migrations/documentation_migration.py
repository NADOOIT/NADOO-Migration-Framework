"""Migration to standardize documentation in Python files."""

import ast
import libcst as cst
from libcst.metadata import ParentNodeProvider, MetadataWrapper
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from nadoo_migration_framework.migrations.toga_import_migrations import FileState


class DocumentationTransformer(cst.CSTTransformer):
    """Transform documentation in a Python file."""

    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    def __init__(self):
        """Initialize the transformer."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.metadata = {}

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Process function definitions."""
        try:
            # Check if function has a docstring
            if not updated_node.get_docstring():
                # Create a basic docstring
                docstring = f'"""{updated_node.name.value}."""\n'

                # Add parameter documentation for each parameter
                if updated_node.params.params:
                    docstring = f'"""{updated_node.name.value}.\n\nArgs:\n'
                    for param in updated_node.params.params:
                        param_name = param.name.value
                        annotation = (
                            param.annotation.annotation.value if param.annotation else "Any"
                        )
                        docstring += (
                            f"    {param_name} ({annotation}): Description of {param_name}.\n"
                        )
                    docstring += '"""\n'

                # Create the docstring node
                doc_node = cst.SimpleStatementLine(
                    body=[cst.Expr(value=cst.SimpleString(value=docstring))]
                )

                # Add the docstring as the first statement
                new_body = [doc_node] + (
                    updated_node.body.body
                    if isinstance(updated_node.body, cst.IndentedBlock)
                    else []
                )
                return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

        except Exception as e:
            self.logger.error(f"Error processing function {updated_node.name.value}: {str(e)}")

        return updated_node

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Process class definitions."""
        try:
            # Check if class has a docstring
            if not updated_node.get_docstring():
                # Create a basic docstring
                docstring = f'"""{updated_node.name.value} class."""\n'

                # Create the docstring node
                doc_node = cst.SimpleStatementLine(
                    body=[cst.Expr(value=cst.SimpleString(value=docstring))]
                )

                # Add the docstring as the first statement
                new_body = [doc_node] + (
                    updated_node.body.body
                    if isinstance(updated_node.body, cst.IndentedBlock)
                    else []
                )
                return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

        except Exception as e:
            self.logger.error(f"Error processing class {updated_node.name.value}: {str(e)}")

        return updated_node

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Process module docstring."""
        try:
            # Check if module has a docstring
            if not updated_node.get_docstring():
                # Create a basic module docstring
                docstring = '"""Module docstring."""\n'

                # Create the docstring node
                doc_node = cst.SimpleStatementLine(
                    body=[cst.Expr(value=cst.SimpleString(value=docstring))]
                )

                # Add the docstring as the first statement
                new_body = [doc_node] + list(updated_node.body)
                return updated_node.with_changes(body=new_body)

        except Exception as e:
            self.logger.error(f"Error processing module docstring: {str(e)}")

        return updated_node


class StandardizeDocumentationMigration:
    """Migration to standardize documentation in Python files."""

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
        """Standardize documentation in Python files."""
        try:
            # Find all Python files in the project
            python_files = list(self.project_dir.rglob("*.py"))

            for file_path in python_files:
                try:
                    # Read the file
                    code = file_path.read_text()

                    # Store original state
                    self.original_states[str(file_path)] = FileState(
                        file_path=str(file_path), original_code=code
                    )

                    # Parse the code into a CST
                    module = cst.parse_module(code)
                    wrapper = MetadataWrapper(module)
                    transformer = DocumentationTransformer()
                    transformer.metadata = wrapper.resolve(ParentNodeProvider)

                    # Transform the code
                    modified_tree = wrapper.visit(transformer)

                    # Write the transformed code back to the file
                    file_path.write_text(modified_tree.code)

                    self.logger.info(f"Successfully standardized documentation in {file_path}")

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
