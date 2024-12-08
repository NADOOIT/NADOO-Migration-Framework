"""Migration to analyze and optimize dependencies using BRAN."""

import ast
import libcst as cst
from libcst.metadata import ParentNodeProvider, MetadataWrapper
import logging
import networkx as nx
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from nadoo_migration_framework.migrations.toga_import_migrations import FileState


class DependencyAnalyzer(cst.CSTTransformer):
    """Analyze dependencies in a Python file."""

    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    def __init__(self):
        """Initialize the analyzer."""
        super().__init__()
        self.imports = {}  # module -> {imported_names}
        self.used_names = set()
        self.dependencies = nx.DiGraph()
        self.logger = logging.getLogger(__name__)
        self.metadata = {}
        self.current_module = None

    def set_current_module(self, module_path: str) -> None:
        """Set the current module being analyzed."""
        self.current_module = module_path

    def visit_Import(self, node: cst.Import) -> None:
        """Track import statements."""
        for name in node.names:
            module_name = name.name.value
            asname = name.asname.name.value if name.asname else module_name
            if module_name not in self.imports:
                self.imports[module_name] = set()
            self.imports[module_name].add(asname)

            # Add dependency to graph
            if self.current_module:
                self.dependencies.add_edge(self.current_module, module_name)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        """Track from ... import statements."""
        if node.module:
            module_name = node.module.value
            for name in node.names:
                imported_name = name.name.value
                asname = name.asname.name.value if name.asname else imported_name
                if module_name not in self.imports:
                    self.imports[module_name] = set()
                self.imports[module_name].add(asname)

                # Add dependency to graph
                if self.current_module:
                    self.dependencies.add_edge(self.current_module, module_name)

    def visit_Name(self, node: cst.Name) -> None:
        """Track used names."""
        if not self._is_in_import_context(node):
            self.used_names.add(node.value)

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

    def get_unused_imports(self) -> Dict[str, Set[str]]:
        """Get unused imports."""
        unused = {}
        for module, names in self.imports.items():
            unused_names = names - self.used_names
            if unused_names:
                unused[module] = unused_names
        return unused

    def get_dependency_graph(self) -> nx.DiGraph:
        """Get the dependency graph."""
        return self.dependencies


class DependencyAnalysisMigration:
    """Migration to analyze and optimize dependencies."""

    def __init__(self):
        """Initialize the migration."""
        self.project_dir = None
        self.original_states = {}
        self.logger = logging.getLogger(__name__)
        self.dependency_graph = nx.DiGraph()

    def set_project_dir(self, project_dir: Union[str, Path]) -> None:
        """Set the project directory."""
        self.project_dir = Path(project_dir)

    def check_if_needed(self) -> bool:
        """Check if migration is needed."""
        if not self.project_dir:
            raise ValueError("Project directory not set")

        return True

    def _analyze_dependencies(self) -> None:
        """Analyze dependencies in all Python files."""
        python_files = list(self.project_dir.rglob("*.py"))

        for file_path in python_files:
            try:
                # Read the file
                code = file_path.read_text()

                # Parse the code into a CST
                module = cst.parse_module(code)
                wrapper = MetadataWrapper(module)
                analyzer = DependencyAnalyzer()
                analyzer.metadata = wrapper.resolve(ParentNodeProvider)
                analyzer.set_current_module(str(file_path))

                # Analyze dependencies
                wrapper.visit(analyzer)

                # Update global dependency graph
                self.dependency_graph.add_edges_from(analyzer.get_dependency_graph().edges())

                # Log unused imports
                unused = analyzer.get_unused_imports()
                if unused:
                    self.logger.warning(f"Unused imports in {file_path}:")
                    for module, names in unused.items():
                        self.logger.warning(f"  {module}: {', '.join(names)}")

            except Exception as e:
                self.logger.error(f"Error analyzing {file_path}: {str(e)}")

    def _detect_cycles(self) -> List[List[str]]:
        """Detect dependency cycles."""
        try:
            return list(nx.simple_cycles(self.dependency_graph))
        except Exception as e:
            self.logger.error(f"Error detecting cycles: {str(e)}")
            return []

    def _up(self) -> None:
        """Analyze and optimize dependencies."""
        try:
            # Analyze dependencies
            self._analyze_dependencies()

            # Detect cycles
            cycles = self._detect_cycles()
            if cycles:
                self.logger.warning("Dependency cycles detected:")
                for cycle in cycles:
                    self.logger.warning(f"  {' -> '.join(cycle)} -> {cycle[0]}")

            # Generate dependency report
            report_path = self.project_dir / "dependency_report.txt"
            with open(report_path, "w") as f:
                f.write("Dependency Analysis Report\n")
                f.write("=========================\n\n")

                f.write("Module Dependencies:\n")
                for node in self.dependency_graph.nodes():
                    deps = list(self.dependency_graph.successors(node))
                    if deps:
                        f.write(f"{node} depends on:\n")
                        for dep in deps:
                            f.write(f"  - {dep}\n")

                if cycles:
                    f.write("\nDependency Cycles:\n")
                    for cycle in cycles:
                        f.write(f"  {' -> '.join(cycle)} -> {cycle[0]}\n")

            self.logger.info(f"Dependency analysis report written to {report_path}")

        except Exception as e:
            self.logger.error(f"Error during dependency analysis: {str(e)}")
            raise

    def _down(self) -> None:
        """Rollback is not needed for analysis."""
        pass  # Analysis is read-only, no rollback needed
