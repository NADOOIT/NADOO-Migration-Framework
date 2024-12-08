"""Migration to collect and analyze code metrics."""

import ast
import libcst as cst
from libcst.metadata import ParentNodeProvider, MetadataWrapper
import json
import logging
from pathlib import Path
import re
from typing import Dict, List, Optional, Set, Tuple, Union
import yaml

from nadoo_migration_framework.migrations.toga_import_migrations import FileState


class CodeMetricsCollector(cst.CSTTransformer):
    """Collect code metrics from Python files."""

    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    def __init__(self):
        """Initialize the collector."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.metadata = {}

        # Metrics storage
        self.complexity_metrics = {}
        self.function_metrics = {}
        self.class_metrics = {}
        self.import_metrics = {}
        self.docstring_metrics = {}
        self.naming_metrics = {}
        self.type_hint_metrics = {}

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Collect function metrics."""
        func_name = node.name.value
        self.function_metrics[func_name] = {
            'args': [p.name.value for p in node.params.params if isinstance(p, cst.Param)],
            'arg_count': len([p for p in node.params.params if isinstance(p, cst.Param)]),
            'decorators': [d.decorator.value for d in node.decorators],
            'docstring': node.get_docstring() is not None,
            'docstring_length': len(node.get_docstring() or ''),
            'has_return_type': node.returns is not None,
            'has_type_hints': any(
                p.annotation for p in node.params.params if isinstance(p, cst.Param)
            ),
            'is_async': isinstance(node, cst.AsyncFunctionDef),
            'line_count': len(node.body.body) if isinstance(node.body, cst.IndentedBlock) else 1,
        }

        # Analyze naming convention
        self.naming_metrics[func_name] = {
            'follows_snake_case': bool(re.match(r'^[a-z][a-z0-9_]*$', func_name)),
            'is_private': func_name.startswith('_'),
            'length': len(func_name),
        }

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Collect class metrics."""
        class_name = node.name.value
        self.class_metrics[class_name] = {
            'bases': [b.value for b in node.bases],
            'decorators': [d.decorator.value for d in node.decorators],
            'docstring': node.get_docstring() is not None,
            'docstring_length': len(node.get_docstring() or ''),
            'method_count': sum(
                1 for n in node.body.body if isinstance(n, (cst.FunctionDef, cst.AsyncFunctionDef))
            ),
            'attribute_count': sum(
                1
                for n in node.body.body
                if isinstance(n, cst.SimpleStatementLine)
                and any(isinstance(s, cst.Assign) for s in n.body)
            ),
            'line_count': len(node.body.body) if isinstance(node.body, cst.IndentedBlock) else 1,
        }

        # Analyze naming convention
        self.naming_metrics[class_name] = {
            'follows_pascal_case': bool(re.match(r'^[A-Z][a-zA-Z0-9]*$', class_name)),
            'length': len(class_name),
        }

    def visit_Import(self, node: cst.Import) -> None:
        """Collect import metrics."""
        for name in node.names:
            module_name = name.name.value
            if module_name not in self.import_metrics:
                self.import_metrics[module_name] = {
                    'count': 0,
                    'aliases': set(),
                    'is_relative': False,
                }
            self.import_metrics[module_name]['count'] += 1
            if name.asname:
                self.import_metrics[module_name]['aliases'].add(name.asname.name.value)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        """Collect from-import metrics."""
        if node.module:
            module_name = node.module.value
            if module_name not in self.import_metrics:
                self.import_metrics[module_name] = {
                    'count': 0,
                    'aliases': set(),
                    'is_relative': bool(node.relative),
                }
            self.import_metrics[module_name]['count'] += 1
            for name in node.names:
                if name.asname:
                    self.import_metrics[module_name]['aliases'].add(name.asname.name.value)

    def analyze_complexity(self, node: cst.CSTNode) -> None:
        """Analyze code complexity."""
        # Count branching statements
        if isinstance(node, (cst.If, cst.While, cst.For, cst.Try)):
            self.complexity_metrics['branching_count'] = (
                self.complexity_metrics.get('branching_count', 0) + 1
            )

        # Count function calls
        elif isinstance(node, cst.Call):
            self.complexity_metrics['call_count'] = self.complexity_metrics.get('call_count', 0) + 1

        # Count operators
        elif isinstance(node, (cst.BinaryOperation, cst.UnaryOperation, cst.BooleanOperation)):
            self.complexity_metrics['operator_count'] = (
                self.complexity_metrics.get('operator_count', 0) + 1
            )

    def on_visit(self, node: cst.CSTNode) -> bool:
        """Visit each node and analyze complexity."""
        self.analyze_complexity(node)
        return True


class CodeMetricsMigration:
    """Migration to collect and analyze code metrics."""

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
        """Collect code metrics."""
        try:
            # Find all Python files in the project
            python_files = list(self.project_dir.rglob("*.py"))

            for file_path in python_files:
                try:
                    # Read the file
                    code = file_path.read_text()

                    # Parse the code into a CST
                    module = cst.parse_module(code)
                    wrapper = MetadataWrapper(module)
                    collector = CodeMetricsCollector()
                    collector.metadata = wrapper.resolve(ParentNodeProvider)

                    # Collect metrics
                    wrapper.visit(collector)

                    # Store metrics
                    self.metrics_data[str(file_path)] = {
                        'complexity': collector.complexity_metrics,
                        'functions': collector.function_metrics,
                        'classes': collector.class_metrics,
                        'imports': collector.import_metrics,
                        'naming': collector.naming_metrics,
                        'file_size': len(code),
                        'line_count': len(code.splitlines()),
                    }

                    self.logger.info(f"Successfully collected metrics from {file_path}")

                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {str(e)}")
                    raise

            # Generate reports
            self._generate_metrics_report()
            self._generate_json_report()
            self._generate_yaml_report()

        except Exception as e:
            self.logger.error(f"Error during metrics collection: {str(e)}")
            raise

    def _generate_metrics_report(self) -> None:
        """Generate a human-readable metrics report."""
        report_path = self.project_dir / "code_metrics_report.txt"
        with open(report_path, "w") as f:
            f.write("Code Metrics Report\n")
            f.write("==================\n\n")

            total_files = len(self.metrics_data)
            total_functions = sum(len(m['functions']) for m in self.metrics_data.values())
            total_classes = sum(len(m['classes']) for m in self.metrics_data.values())
            total_lines = sum(m['line_count'] for m in self.metrics_data.values())

            f.write(f"Project Summary\n")
            f.write(f"--------------\n")
            f.write(f"Total Files: {total_files}\n")
            f.write(f"Total Functions: {total_functions}\n")
            f.write(f"Total Classes: {total_classes}\n")
            f.write(f"Total Lines of Code: {total_lines}\n\n")

            for file_path, metrics in self.metrics_data.items():
                f.write(f"File: {file_path}\n")
                f.write("-" * (len(file_path) + 6) + "\n")

                f.write(f"Size: {metrics['file_size']} bytes\n")
                f.write(f"Lines: {metrics['line_count']}\n\n")

                f.write("Functions:\n")
                for func_name, func_data in metrics['functions'].items():
                    f.write(f"  {func_name}:\n")
                    f.write(f"    Arguments: {', '.join(func_data['args'])}\n")
                    f.write(f"    Line Count: {func_data['line_count']}\n")
                    f.write(f"    Has Docstring: {func_data['docstring']}\n")
                    f.write(f"    Has Type Hints: {func_data['has_type_hints']}\n")
                    f.write("\n")

                f.write("Classes:\n")
                for class_name, class_data in metrics['classes'].items():
                    f.write(f"  {class_name}:\n")
                    f.write(f"    Methods: {class_data['method_count']}\n")
                    f.write(f"    Attributes: {class_data['attribute_count']}\n")
                    f.write(f"    Line Count: {class_data['line_count']}\n")
                    f.write(f"    Has Docstring: {class_data['docstring']}\n")
                    f.write("\n")

                f.write("Imports:\n")
                for module, import_data in metrics['imports'].items():
                    f.write(f"  {module}:\n")
                    f.write(f"    Count: {import_data['count']}\n")
                    f.write(f"    Aliases: {', '.join(import_data['aliases'])}\n")
                    f.write(f"    Is Relative: {import_data['is_relative']}\n")
                    f.write("\n")

                f.write("\n")

        self.logger.info(f"Metrics report written to {report_path}")

    def _generate_json_report(self) -> None:
        """Generate a JSON metrics report."""
        report_path = self.project_dir / "code_metrics.json"
        with open(report_path, "w") as f:
            # Convert sets to lists for JSON serialization
            serializable_data = {}
            for file_path, metrics in self.metrics_data.items():
                serializable_metrics = metrics.copy()
                if 'imports' in serializable_metrics:
                    for module in serializable_metrics['imports']:
                        serializable_metrics['imports'][module]['aliases'] = list(
                            serializable_metrics['imports'][module]['aliases']
                        )
                serializable_data[file_path] = serializable_metrics

            json.dump(serializable_data, f, indent=2)

        self.logger.info(f"JSON metrics report written to {report_path}")

    def _generate_yaml_report(self) -> None:
        """Generate a YAML metrics report."""
        report_path = self.project_dir / "code_metrics.yaml"
        with open(report_path, "w") as f:
            # Convert sets to lists for YAML serialization
            serializable_data = {}
            for file_path, metrics in self.metrics_data.items():
                serializable_metrics = metrics.copy()
                if 'imports' in serializable_metrics:
                    for module in serializable_metrics['imports']:
                        serializable_metrics['imports'][module]['aliases'] = list(
                            serializable_metrics['imports'][module]['aliases']
                        )
                serializable_data[file_path] = serializable_metrics

            yaml.dump(serializable_data, f, default_flow_style=False)

        self.logger.info(f"YAML metrics report written to {report_path}")

    def _down(self) -> None:
        """Rollback is not needed for metrics collection."""
        pass  # Metrics collection is read-only, no rollback needed
