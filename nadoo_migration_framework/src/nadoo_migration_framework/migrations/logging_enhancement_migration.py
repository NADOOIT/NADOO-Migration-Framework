"""Migration to enhance logging and code instrumentation."""

import ast
import libcst as cst
from libcst.metadata import ParentNodeProvider, MetadataWrapper
import logging
import inspect
from pathlib import Path
import time
from typing import Dict, List, Optional, Set, Tuple, Union
import uuid

from nadoo_migration_framework.migrations.toga_import_migrations import FileState


class LoggingEnhancer(cst.CSTTransformer):
    """Transform code to add enhanced logging."""

    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    def __init__(self):
        """Initialize the transformer."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.metadata = {}
        self.function_metrics = {}
        self.class_metrics = {}

    def _create_logging_setup(self) -> List[cst.BaseSmallStatement]:
        """Create logging setup statements."""
        return [
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

    def _create_timing_decorator(self) -> List[cst.BaseSmallStatement]:
        """Create timing decorator function."""
        return [
            cst.FunctionDef(
                name=cst.Name("log_execution_time"),
                params=cst.Parameters([cst.Param(name=cst.Name("func"))]),
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
                                    cst.Assign(
                                        targets=[cst.AssignTarget(target=cst.Name("start_time"))],
                                        value=cst.Call(
                                            func=cst.Name("time"),
                                            args=[],
                                        ),
                                    ),
                                    cst.Try(
                                        body=cst.IndentedBlock(
                                            [
                                                cst.Assign(
                                                    targets=[
                                                        cst.AssignTarget(target=cst.Name("result"))
                                                    ],
                                                    value=cst.Call(
                                                        func=cst.Name("func"),
                                                        args=[
                                                            cst.Arg(
                                                                value=cst.Name("args"), star="*"
                                                            ),
                                                            cst.Arg(
                                                                value=cst.Name("kwargs"), star="**"
                                                            ),
                                                        ],
                                                    ),
                                                ),
                                                cst.Return(value=cst.Name("result")),
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
                                                                    value=cst.Name("logger"),
                                                                    attr=cst.Name("error"),
                                                                ),
                                                                args=[
                                                                    cst.Arg(
                                                                        value=cst.FormattedString(
                                                                            parts=[
                                                                                cst.FormattedStringText(
                                                                                    'Error in '
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
                                                                                    ': '
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
                                                cst.Expr(
                                                    value=cst.Call(
                                                        func=cst.Attribute(
                                                            value=cst.Name("logger"),
                                                            attr=cst.Name("debug"),
                                                        ),
                                                        args=[
                                                            cst.Arg(
                                                                value=cst.FormattedString(
                                                                    parts=[
                                                                        cst.FormattedStringText(
                                                                            'Function '
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
                                                                            ' took '
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
                                                                            ' seconds'
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
                                ]
                            ),
                        ),
                        cst.Return(value=cst.Name("wrapper")),
                    ]
                ),
                decorators=[],
            ),
        ]

    def _add_function_logging(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Add logging to a function."""
        # Create unique ID for this function
        func_id = str(uuid.uuid4())[:8]
        self.function_metrics[func_id] = {
            'name': node.name.value,
            'args': [p.name.value for p in node.params.params if isinstance(p, cst.Param)],
            'decorators': [d.decorator.value for d in node.decorators],
            'docstring': node.get_docstring(),
        }

        # Add logging statements at the start and end of the function
        new_body = [
            cst.Expr(
                value=cst.Call(
                    func=cst.Attribute(value=cst.Name("logger"), attr=cst.Name("debug")),
                    args=[
                        cst.Arg(
                            value=cst.FormattedString(
                                parts=[
                                    cst.FormattedStringText(f'[{func_id}] Entering '),
                                    cst.FormattedStringExpression(expression=cst.Name("__name__")),
                                    cst.FormattedStringText('.'),
                                    cst.FormattedStringExpression(
                                        expression=cst.Name(node.name.value)
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        ]

        # Add original function body
        if isinstance(node.body, cst.IndentedBlock):
            new_body.extend(node.body.body)

        # Add exit logging
        new_body.append(
            cst.Expr(
                value=cst.Call(
                    func=cst.Attribute(value=cst.Name("logger"), attr=cst.Name("debug")),
                    args=[
                        cst.Arg(
                            value=cst.FormattedString(
                                parts=[
                                    cst.FormattedStringText(f'[{func_id}] Exiting '),
                                    cst.FormattedStringExpression(expression=cst.Name("__name__")),
                                    cst.FormattedStringText('.'),
                                    cst.FormattedStringExpression(
                                        expression=cst.Name(node.name.value)
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        )

        # Add timing decorator
        decorators = list(node.decorators)
        decorators.append(
            cst.Decorator(
                decorator=cst.Name("log_execution_time"),
            )
        )

        return node.with_changes(
            body=cst.IndentedBlock(body=new_body),
            decorators=decorators,
        )

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Process module when leaving."""
        try:
            new_body = []

            # Add imports and logging setup
            new_body.extend(self._create_logging_setup())
            new_body.append(cst.EmptyLine())

            # Add timing decorator
            new_body.extend(self._create_timing_decorator())
            new_body.append(cst.EmptyLine())

            # Process the rest of the module
            for node in updated_node.body:
                if isinstance(node, cst.FunctionDef):
                    new_body.append(self._add_function_logging(node))
                else:
                    new_body.append(node)

            return updated_node.with_changes(body=new_body)

        except Exception as e:
            self.logger.error(f"Error enhancing logging: {str(e)}")
            return updated_node


class LoggingEnhancementMigration:
    """Migration to enhance logging and code instrumentation."""

    def __init__(self):
        """Initialize the migration."""
        self.project_dir = None
        self.original_states = {}
        self.logger = logging.getLogger(__name__)
        self.metrics_data = {}

    def set_project_dir(self, project_dir: Union[str, Path]) -> None:
        """Set the project directory."""
        self.project_dir = Path(project_dir)

    def check_if_needed(self) -> bool:
        """Check if migration is needed."""
        if not self.project_dir:
            raise ValueError("Project directory not set")

        return True

    def _up(self) -> None:
        """Enhance logging in Python files."""
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
                    transformer = LoggingEnhancer()
                    transformer.metadata = wrapper.resolve(ParentNodeProvider)

                    # Transform the code
                    modified_tree = wrapper.visit(transformer)

                    # Store metrics
                    self.metrics_data[str(file_path)] = {
                        'functions': transformer.function_metrics,
                        'classes': transformer.class_metrics,
                    }

                    # Write the transformed code back to the file
                    file_path.write_text(modified_tree.code)

                    self.logger.info(f"Successfully enhanced logging in {file_path}")

                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {str(e)}")
                    raise

            # Generate metrics report
            self._generate_metrics_report()

        except Exception as e:
            self.logger.error(f"Error during logging enhancement: {str(e)}")
            raise

    def _generate_metrics_report(self) -> None:
        """Generate a report of code metrics."""
        report_path = self.project_dir / "code_metrics_report.txt"
        with open(report_path, "w") as f:
            f.write("Code Metrics Report\n")
            f.write("==================\n\n")

            for file_path, metrics in self.metrics_data.items():
                f.write(f"File: {file_path}\n")
                f.write("-" * (len(file_path) + 6) + "\n\n")

                f.write("Functions:\n")
                for func_id, func_data in metrics['functions'].items():
                    f.write(f"  [{func_id}] {func_data['name']}\n")
                    f.write(f"    Arguments: {', '.join(func_data['args'])}\n")
                    f.write(f"    Decorators: {', '.join(func_data['decorators'])}\n")
                    if func_data['docstring']:
                        f.write(f"    Docstring: {func_data['docstring']}\n")
                    f.write("\n")

                f.write("\n")

        self.logger.info(f"Code metrics report written to {report_path}")

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
