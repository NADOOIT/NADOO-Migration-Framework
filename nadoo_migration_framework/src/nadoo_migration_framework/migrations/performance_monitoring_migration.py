"""Migration to add performance monitoring to Python files."""

import ast
import libcst as cst
from libcst.metadata import ParentNodeProvider, MetadataWrapper
import logging
from pathlib import Path
import time
from typing import Dict, List, Optional, Set, Tuple, Union
import uuid

from nadoo_migration_framework.migrations.toga_import_migrations import FileState


class PerformanceMonitor(cst.CSTTransformer):
    """Add performance monitoring to Python files."""

    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    def __init__(self):
        """Initialize the monitor."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.metadata = {}
        self.monitored_functions = set()
        self.monitored_classes = set()

    def _create_monitoring_imports(self) -> List[cst.BaseSmallStatement]:
        """Create monitoring import statements."""
        return [
            cst.ImportFrom(
                module=cst.Name("functools"),
                names=[cst.ImportAlias(name=cst.Name("wraps"))],
            ),
            cst.ImportFrom(
                module=cst.Name("time"),
                names=[cst.ImportAlias(name=cst.Name("time"))],
            ),
            cst.ImportFrom(
                module=cst.Name("logging"),
                names=[cst.ImportAlias(name=cst.Name("getLogger"))],
            ),
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name("logger"))],
                value=cst.Call(
                    func=cst.Name("getLogger"),
                    args=[cst.Arg(value=cst.Name("__name__"))],
                ),
            ),
        ]

    def _create_monitoring_decorator(self) -> List[cst.BaseSmallStatement]:
        """Create performance monitoring decorator."""
        return [
            cst.FunctionDef(
                name=cst.Name("monitor_performance"),
                params=cst.Parameters([]),
                body=cst.IndentedBlock(
                    [
                        cst.FunctionDef(
                            name=cst.Name("decorator"),
                            params=cst.Parameters(
                                [
                                    cst.Param(name=cst.Name("func")),
                                ]
                            ),
                            body=cst.IndentedBlock(
                                [
                                    cst.FunctionDef(
                                        name=cst.Name("wrapper"),
                                        params=cst.Parameters(
                                            [
                                                cst.Param(name=cst.Name("*args")),
                                                cst.Param(name=cst.Name("**kwargs")),
                                            ]
                                        ),
                                        body=cst.IndentedBlock(
                                            [
                                                # Start monitoring
                                                cst.Assign(
                                                    targets=[
                                                        cst.AssignTarget(
                                                            target=cst.Name("start_time")
                                                        )
                                                    ],
                                                    value=cst.Call(func=cst.Name("time"), args=[]),
                                                ),
                                                cst.Assign(
                                                    targets=[
                                                        cst.AssignTarget(
                                                            target=cst.Name("start_memory")
                                                        )
                                                    ],
                                                    value=cst.Call(
                                                        func=cst.Attribute(
                                                            value=cst.Name("psutil"),
                                                            attr=cst.Name("Process"),
                                                        ),
                                                        args=[
                                                            cst.Arg(
                                                                value=cst.Call(
                                                                    func=cst.Name("os"),
                                                                    attr=cst.Name("getpid"),
                                                                    args=[],
                                                                ),
                                                            ),
                                                        ],
                                                    ),
                                                ),
                                                # Execute function
                                                cst.Try(
                                                    body=cst.IndentedBlock(
                                                        [
                                                            cst.Assign(
                                                                targets=[
                                                                    cst.AssignTarget(
                                                                        target=cst.Name("result")
                                                                    )
                                                                ],
                                                                value=cst.Call(
                                                                    func=cst.Name("func"),
                                                                    args=[
                                                                        cst.Arg(
                                                                            value=cst.Name("args"),
                                                                            star="*",
                                                                        ),
                                                                        cst.Arg(
                                                                            value=cst.Name(
                                                                                "kwargs"
                                                                            ),
                                                                            star="**",
                                                                        ),
                                                                    ],
                                                                ),
                                                            ),
                                                        ]
                                                    ),
                                                    handlers=[
                                                        cst.ExceptHandler(
                                                            type=cst.Name("Exception"),
                                                            name=cst.Name("e"),
                                                            body=cst.IndentedBlock(
                                                                [
                                                                    cst.Expr(
                                                                        value=cst.Call(
                                                                            func=cst.Attribute(
                                                                                value=cst.Name(
                                                                                    "logger"
                                                                                ),
                                                                                attr=cst.Name(
                                                                                    "error"
                                                                                ),
                                                                            ),
                                                                            args=[
                                                                                cst.Arg(
                                                                                    value=cst.FormattedString(
                                                                                        parts=[
                                                                                            cst.FormattedStringText(
                                                                                                "Error in "
                                                                                            ),
                                                                                            cst.FormattedStringExpression(
                                                                                                expression=cst.Attribute(
                                                                                                    value=cst.Name(
                                                                                                        "func"
                                                                                                    ),
                                                                                                    attr=cst.Name(
                                                                                                        "__name__"
                                                                                                    ),
                                                                                                ),
                                                                                            ),
                                                                                            cst.FormattedStringText(
                                                                                                ": "
                                                                                            ),
                                                                                            cst.FormattedStringExpression(
                                                                                                expression=cst.Name(
                                                                                                    "e"
                                                                                                ),
                                                                                            ),
                                                                                        ],
                                                                                    ),
                                                                                ),
                                                                            ],
                                                                        ),
                                                                    ),
                                                                    cst.Raise(),
                                                                ]
                                                            ),
                                                        ),
                                                    ],
                                                    finalbody=cst.IndentedBlock(
                                                        [
                                                            # Log performance metrics
                                                            cst.Expr(
                                                                value=cst.Call(
                                                                    func=cst.Attribute(
                                                                        value=cst.Name("logger"),
                                                                        attr=cst.Name("info"),
                                                                    ),
                                                                    args=[
                                                                        cst.Arg(
                                                                            value=cst.FormattedString(
                                                                                parts=[
                                                                                    cst.FormattedStringText(
                                                                                        "Performance metrics for "
                                                                                    ),
                                                                                    cst.FormattedStringExpression(
                                                                                        expression=cst.Attribute(
                                                                                            value=cst.Name(
                                                                                                "func"
                                                                                            ),
                                                                                            attr=cst.Name(
                                                                                                "__name__"
                                                                                            ),
                                                                                        ),
                                                                                    ),
                                                                                    cst.FormattedStringText(
                                                                                        ":\\n"
                                                                                    ),
                                                                                    cst.FormattedStringText(
                                                                                        "  Time: "
                                                                                    ),
                                                                                    cst.FormattedStringExpression(
                                                                                        expression=cst.BinaryOperation(
                                                                                            left=cst.Call(
                                                                                                func=cst.Name(
                                                                                                    "time"
                                                                                                ),
                                                                                                args=[],
                                                                                            ),
                                                                                            operator=cst.Minus(),
                                                                                            right=cst.Name(
                                                                                                "start_time"
                                                                                            ),
                                                                                        ),
                                                                                    ),
                                                                                    cst.FormattedStringText(
                                                                                        " seconds\\n"
                                                                                    ),
                                                                                    cst.FormattedStringText(
                                                                                        "  Memory: "
                                                                                    ),
                                                                                    cst.FormattedStringExpression(
                                                                                        expression=cst.Call(
                                                                                            func=cst.Attribute(
                                                                                                value=cst.Name(
                                                                                                    "start_memory"
                                                                                                ),
                                                                                                attr=cst.Name(
                                                                                                    "memory_info"
                                                                                                ),
                                                                                            ),
                                                                                            args=[],
                                                                                        ),
                                                                                    ),
                                                                                ],
                                                                            ),
                                                                        ),
                                                                    ],
                                                                ),
                                                            ),
                                                        ]
                                                    ),
                                                ),
                                                # Return result
                                                cst.Return(value=cst.Name("result")),
                                            ]
                                        ),
                                        decorators=[
                                            cst.Decorator(
                                                decorator=cst.Call(
                                                    func=cst.Name("wraps"),
                                                    args=[cst.Arg(value=cst.Name("func"))],
                                                ),
                                            ),
                                        ],
                                    ),
                                    cst.Return(value=cst.Name("wrapper")),
                                ]
                            ),
                        ),
                        cst.Return(value=cst.Name("decorator")),
                    ]
                ),
            ),
        ]

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Add monitoring to functions."""
        # Skip if already monitored or if it's a special method
        if (
            updated_node.name.value in self.monitored_functions
            or updated_node.name.value.startswith('__')
        ):
            return updated_node

        # Add to monitored set
        self.monitored_functions.add(updated_node.name.value)

        # Add monitoring decorator
        decorators = list(updated_node.decorators)
        decorators.append(
            cst.Decorator(
                decorator=cst.Call(
                    func=cst.Name("monitor_performance"),
                    args=[],
                ),
            ),
        )

        return updated_node.with_changes(decorators=decorators)

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Process module when leaving."""
        try:
            new_body = []

            # Add monitoring imports and setup
            new_body.extend(self._create_monitoring_imports())
            new_body.append(cst.EmptyLine())

            # Add monitoring decorator
            new_body.extend(self._create_monitoring_decorator())
            new_body.append(cst.EmptyLine())

            # Process the rest of the module
            for node in updated_node.body:
                new_body.append(node)

            return updated_node.with_changes(body=new_body)

        except Exception as e:
            self.logger.error(f"Error adding performance monitoring: {str(e)}")
            return updated_node


class PerformanceMonitoringMigration:
    """Migration to add performance monitoring."""

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
        """Add performance monitoring to Python files."""
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
                    monitor = PerformanceMonitor()
                    monitor.metadata = wrapper.resolve(ParentNodeProvider)

                    # Transform the code
                    modified_tree = wrapper.visit(monitor)

                    # Write the transformed code back to the file
                    file_path.write_text(modified_tree.code)

                    self.logger.info(f"Successfully added performance monitoring to {file_path}")

                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {str(e)}")
                    raise

        except Exception as e:
            self.logger.error(f"Error during performance monitoring addition: {str(e)}")
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
