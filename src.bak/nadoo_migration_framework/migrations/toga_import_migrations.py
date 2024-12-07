import ast
import libcst as cst
from libcst.metadata import ParentNodeProvider, MetadataWrapper
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

# Standard library modules that should be in the first import group
STDLIB_MODULES = {
    "abc", "argparse", "array", "ast", "asyncio", "base64", "binascii",
    "builtins", "cgi", "collections", "concurrent", "contextlib", "copy",
    "csv", "datetime", "decimal", "difflib", "email", "enum", "errno",
    "fcntl", "filecmp", "fnmatch", "fractions", "functools", "gc",
    "getopt", "getpass", "glob", "hashlib", "heapq", "hmac", "html",
    "http", "importlib", "inspect", "io", "ipaddress", "itertools", "json",
    "keyword", "linecache", "locale", "logging", "math", "mimetypes",
    "mmap", "multiprocessing", "netrc", "numbers", "operator", "os",
    "pathlib", "pickle", "platform", "pprint", "pwd", "queue", "random",
    "re", "reprlib", "select", "shutil", "signal", "socket", "sqlite3",
    "ssl", "stat", "string", "struct", "subprocess", "sys", "tempfile",
    "textwrap", "threading", "time", "timeit", "token", "tokenize",
    "traceback", "types", "typing", "unicodedata", "unittest", "urllib",
    "uuid", "warnings", "weakref", "xml", "xmlrpc", "zipfile", "zlib"
}

class FileState:
    """Class to store file state for rollback."""

    def __init__(self, file_path: str, original_code: str):
        """Initialize file state."""
        self.file_path = file_path
        self.original_code = original_code

class ImportTransformer(cst.CSTTransformer):
    """Transform imports in a Python file."""

    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    def __init__(self):
        """Initialize the transformer."""
        super().__init__()
        self.used_names = set()
        self.used_modules = set()
        self.all_imports = []
        self.logger = logging.getLogger(__name__)
        self.metadata = {}

    def visit_Import(self, node: cst.Import) -> None:
        """Track import statements."""
        self.all_imports.append(node)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        """Track from ... import statements."""
        self.all_imports.append(node)

    def visit_Name(self, node: cst.Name) -> None:
        """Track used names."""
        # Skip names in import statements
        if not self._is_in_import_context(node):
            self.used_names.add(node.value)

    def visit_Attribute(self, node: cst.Attribute) -> None:
        """Track used module names."""
        # Skip attributes in import statements
        if not self._is_in_import_context(node):
            if isinstance(node.value, cst.Name):
                self.used_modules.add(node.value.value)
                self.used_names.add(node.value.value)
            elif isinstance(node.value, cst.Attribute):
                self._visit_nested_attribute(node.value)

    def _is_in_import_context(self, node: cst.CSTNode) -> bool:
        """Check if a node is part of an import statement."""
        try:
            current = node
            while current:
                if isinstance(current, (cst.Import, cst.ImportFrom)):
                    return True
                parent = self.get_metadata(ParentNodeProvider, current)
                if parent is None:
                    break
                current = parent
        except KeyError:
            pass
        return False

    def _visit_nested_attribute(self, node: cst.Attribute) -> None:
        """Recursively track used module names in nested attributes."""
        if isinstance(node.value, cst.Name):
            self.used_modules.add(node.value.value)
            self.used_names.add(node.value.value)
        elif isinstance(node.value, cst.Attribute):
            self._visit_nested_attribute(node.value)

    def _get_module_name(self, node: Union[cst.Import, cst.ImportFrom]) -> str:
        """Get the module name from an import node."""
        try:
            if isinstance(node, cst.Import):
                if node.names:
                    return node.names[0].name.value.split('.')[0]
            elif isinstance(node, cst.ImportFrom):
                if node.module:
                    return node.module.value.split('.')[0]
                return '.' * len(node.relative)
            return ''
        except Exception as e:
            self.logger.error(f"Error getting module name: {e}")
            return ''

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Process imports when leaving the module."""
        try:
            # Group imports by type
            stdlib_imports = []
            third_party_imports = []
            local_imports = []

            for imp in self.all_imports:
                module_name = self._get_module_name(imp)
                if module_name.startswith('.'):
                    local_imports.append(imp)
                elif module_name in STDLIB_MODULES:
                    stdlib_imports.append(imp)
                else:
                    third_party_imports.append(imp)

            # Create new body with organized imports
            new_body = []

            # Add stdlib imports
            if stdlib_imports:
                new_body.extend(stdlib_imports)
                new_body.append(cst.EmptyLine())

            # Add third-party imports
            if third_party_imports:
                new_body.extend(third_party_imports)
                new_body.append(cst.EmptyLine())

            # Add local imports
            if local_imports:
                new_body.extend(local_imports)
                new_body.append(cst.EmptyLine())

            # Add remaining code
            for node in updated_node.body:
                if not isinstance(node, (cst.Import, cst.ImportFrom)):
                    new_body.append(node)

            return updated_node.with_changes(body=new_body)
        except Exception as e:
            self.logger.error(f"Error processing imports: {str(e)}")
            return updated_node

class ConsolidateImportsMigration:
    """Migration to consolidate imports in Python files."""

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
        """Consolidate imports in Python files."""
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
                    transformer = ImportTransformer()
                    transformer.metadata = wrapper.resolve(ParentNodeProvider)

                    # Transform the code
                    modified_tree = wrapper.visit(transformer)

                    # Write the transformed code back to the file
                    file_path.write_text(modified_tree.code)

                    self.logger.info(f"Successfully processed {file_path}")

                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {str(e)}")
                    raise  # Re-raise the exception to trigger error handling test
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
