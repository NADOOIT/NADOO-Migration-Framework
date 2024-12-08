"""Migration to transform apps into NADOO Brain-compatible applications."""

import ast
import libcst as cst
from libcst.metadata import ParentNodeProvider, MetadataWrapper
import logging
from pathlib import Path
import time
from typing import Dict, List, Optional, Set, Tuple, Union
import uuid
import json
import inspect
import os

from nadoo_migration_framework.migrations.toga_import_migrations import FileState


class NADOOBrainTransformer(cst.CSTTransformer):
    """Transform Python apps into NADOO Brain-compatible format."""

    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    def __init__(self):
        """Initialize the transformer."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.metadata = {}
        self.app_name = ""
        self.brain_imports_added = False
        self.process_manager_added = False

    def _create_brain_imports(self) -> List[cst.BaseSmallStatement]:
        """Create NADOO Brain imports."""
        return [
            cst.ImportFrom(
                module=cst.Name("nadoo.brain"),
                names=[
                    cst.ImportAlias(name=cst.Name("Brain")),
                    cst.ImportAlias(name=cst.Name("ProcessManager")),
                    cst.ImportAlias(name=cst.Name("FeedManager")),
                ],
            ),
            cst.ImportFrom(
                module=cst.Name("nadoo.brain.feed"),
                names=[cst.ImportAlias(name=cst.Name("Feed"))],
            ),
        ]

    def _create_process_manager(self) -> List[cst.BaseSmallStatement]:
        """Create ProcessManager setup."""
        return [
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name("process_manager"))],
                value=cst.Call(
                    func=cst.Name("ProcessManager"),
                    args=[],
                ),
            ),
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name("feed_manager"))],
                value=cst.Call(
                    func=cst.Name("FeedManager"),
                    args=[],
                ),
            ),
        ]

    def _create_brain_setup(self) -> List[cst.BaseSmallStatement]:
        """Create Brain setup code."""
        return [
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name("brain"))],
                value=cst.Call(
                    func=cst.Name("Brain"),
                    args=[
                        cst.Arg(value=cst.SimpleString(f'"{self.app_name}"')),
                        cst.Arg(value=cst.Name("process_manager")),
                        cst.Arg(value=cst.Name("feed_manager")),
                    ],
                ),
            ),
        ]

    def _create_feed_methods(self) -> List[cst.FunctionDef]:
        """Create feed-related methods."""
        return [
            cst.FunctionDef(
                name=cst.Name("create_feed"),
                params=cst.Parameters(
                    [
                        cst.Param(name=cst.Name("self")),
                        cst.Param(name=cst.Name("name")),
                        cst.Param(name=cst.Name("data")),
                    ]
                ),
                body=cst.IndentedBlock(
                    [
                        cst.Return(
                            value=cst.Call(
                                func=cst.Attribute(
                                    value=cst.Name("self"),
                                    attr=cst.Name("feed_manager"),
                                ),
                                args=[
                                    cst.Arg(value=cst.Name("name")),
                                    cst.Arg(value=cst.Name("data")),
                                ],
                            ),
                        ),
                    ]
                ),
                returns=cst.Annotation(annotation=cst.Name("Feed")),
            ),
            cst.FunctionDef(
                name=cst.Name("send_to_feed"),
                params=cst.Parameters(
                    [
                        cst.Param(name=cst.Name("self")),
                        cst.Param(name=cst.Name("feed_name")),
                        cst.Param(name=cst.Name("data")),
                    ]
                ),
                body=cst.IndentedBlock(
                    [
                        cst.Expr(
                            value=cst.Call(
                                func=cst.Attribute(
                                    value=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name("feed_manager"),
                                    ),
                                    attr=cst.Name("send"),
                                ),
                                args=[
                                    cst.Arg(value=cst.Name("feed_name")),
                                    cst.Arg(value=cst.Name("data")),
                                ],
                            ),
                        ),
                    ]
                ),
            ),
        ]

    def transform_app_class(self, node: cst.ClassDef) -> cst.ClassDef:
        """Transform a Toga app class into a NADOO Brain app."""
        # Add Brain as a parent class
        bases = list(node.bases)
        if not any(base.value.value == "Brain" for base in bases):
            bases.append(cst.Arg(value=cst.Name("Brain")))

        # Add new methods
        body = list(node.body.body)
        body.extend(self._create_feed_methods())

        # Transform __init__ method
        for i, stmt in enumerate(body):
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                # Get the original function body
                init_body = list(stmt.body.body)

                # Add Brain initialization
                init_body.insert(
                    0,
                    cst.Expr(
                        value=cst.Call(
                            func=cst.Attribute(
                                value=cst.Name("super"),
                                attr=cst.Name("__init__"),
                            ),
                            args=[
                                cst.Arg(value=cst.SimpleString(f'"{self.app_name}"')),
                                cst.Arg(value=cst.Name("process_manager")),
                                cst.Arg(value=cst.Name("feed_manager")),
                            ],
                        ),
                    ),
                )

                # Update the function
                body[i] = stmt.with_changes(body=cst.IndentedBlock(init_body))

        return node.with_changes(bases=bases, body=cst.IndentedBlock(body))

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Process module when leaving."""
        try:
            new_body = []

            # Add Brain imports if not already present
            if not self.brain_imports_added:
                new_body.extend(self._create_brain_imports())
                new_body.append(cst.EmptyLine())
                self.brain_imports_added = True

            # Add ProcessManager setup if not already present
            if not self.process_manager_added:
                new_body.extend(self._create_process_manager())
                new_body.append(cst.EmptyLine())
                self.process_manager_added = True

            # Process the rest of the module
            for node in updated_node.body:
                if isinstance(node, cst.ClassDef):
                    # Transform app class
                    new_body.append(self.transform_app_class(node))
                else:
                    new_body.append(node)

            return updated_node.with_changes(body=new_body)

        except Exception as e:
            self.logger.error(f"Error transforming module: {str(e)}")
            return updated_node


class NADOOBrainMigration:
    """Migration to transform apps into NADOO Brain-compatible format."""

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

    def _transform_app_file(self, file_path: Path, app_name: str) -> None:
        """Transform a Python file into a NADOO Brain app."""
        try:
            # Read the file
            code = file_path.read_text()

            # Store original state
            self.original_states[str(file_path)] = FileState(
                file_path=str(file_path), original_code=code
            )

            # Parse and transform the code
            module = cst.parse_module(code)
            wrapper = MetadataWrapper(module)
            transformer = NADOOBrainTransformer()
            transformer.app_name = app_name
            transformer.metadata = wrapper.resolve(ParentNodeProvider)

            # Transform the code
            modified_tree = wrapper.visit(transformer)

            # Write transformed code back to file
            file_path.write_text(modified_tree.code)

            self.logger.info(f"Successfully transformed {file_path}")

        except Exception as e:
            self.logger.error(f"Error transforming {file_path}: {str(e)}")
            raise

    def _create_brain_config(self, app_name: str) -> None:
        """Create NADOO Brain configuration file."""
        config = {
            "app_name": app_name,
            "brain": {
                "process_manager": {"max_processes": 10, "timeout": 300},
                "feed_manager": {"max_feeds": 100, "cleanup_interval": 3600},
            },
        }

        config_path = self.project_dir / "brain_config.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)

    def _up(self) -> None:
        """Transform the project into a NADOO Brain app."""
        try:
            # Get app name from directory name
            app_name = self.project_dir.name.replace("-", "_").lower()

            # Find main app file
            python_files = list(self.project_dir.rglob("*.py"))
            app_file = None
            for file in python_files:
                with open(file, "r") as f:
                    content = f.read()
                    if "class" in content and ("App" in content or "Application" in content):
                        app_file = file
                        break

            if not app_file:
                raise ValueError("Could not find main app file")

            # Transform app file
            self._transform_app_file(app_file, app_name)

            # Create Brain configuration
            self._create_brain_config(app_name)

            self.logger.info(f"Successfully transformed project into NADOO Brain app: {app_name}")

        except Exception as e:
            self.logger.error(f"Error during transformation: {str(e)}")
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

                    # Remove Brain configuration if it exists
                    config_path = self.project_dir / "brain_config.json"
                    if config_path.exists():
                        config_path.unlink()

                except Exception as e:
                    self.logger.error(f"Error rolling back {file_state.file_path}: {str(e)}")
                    raise
        except Exception as e:
            self.logger.error(f"Error during rollback: {str(e)}")
            raise
