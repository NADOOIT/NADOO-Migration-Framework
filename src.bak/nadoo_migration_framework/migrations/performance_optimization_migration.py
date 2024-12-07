"""Migration for automatic performance optimization using Exo."""

import ast
import libcst as cst
from libcst.metadata import ParentNodeProvider, MetadataWrapper
import logging
from pathlib import Path
import time
import statistics
from typing import Dict, List, Optional, Set, Tuple, Union
import uuid
import concurrent.futures
import json
import inspect
import tempfile
import importlib.util
import sys
import timeit
import psutil
import os
import numpy as np
from functools import lru_cache

from nadoo_migration_framework.migrations.toga_import_migrations import FileState

class ExoOptimizer:
    """Optimize function performance using Exo."""

    def __init__(self):
        """Initialize the optimizer."""
        self.logger = logging.getLogger(__name__)
        self.optimization_history = {}
        self.benchmark_results = {}

    def _get_function_source(self, func) -> str:
        """Get the source code of a function."""
        return inspect.getsource(func)

    def _get_function_complexity(self, func) -> dict:
        """Analyze function complexity."""
        source = self._get_function_source(func)
        tree = ast.parse(source)
        
        complexity = {
            'cyclomatic': 1,  # Base complexity
            'lines': len(source.split('\n')),
            'branches': 0,
            'loops': 0
        }
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Try)):
                complexity['cyclomatic'] += 1
                complexity['branches'] += 1
            if isinstance(node, (ast.For, ast.While)):
                complexity['loops'] += 1
                
        return complexity

    def _benchmark_function(self, func, num_runs=100) -> dict:
        """Benchmark a function's performance."""
        # Get signature
        sig = inspect.signature(func)
        
        # Create sample arguments based on parameter types
        sample_args = []
        sample_kwargs = {}
        
        for param in sig.parameters.values():
            if param.annotation == int:
                sample_args.append(42)
            elif param.annotation == str:
                sample_args.append("test")
            elif param.annotation == list:
                sample_args.append([1, 2, 3])
            elif param.annotation == dict:
                sample_args.append({"key": "value"})
            else:
                sample_args.append(None)

        # Measure execution time
        times = []
        memory_usage = []
        process = psutil.Process()
        
        for _ in range(num_runs):
            start_memory = process.memory_info().rss
            start_time = time.perf_counter()
            
            try:
                func(*sample_args, **sample_kwargs)
            except Exception as e:
                self.logger.error(f"Error during benchmark: {str(e)}")
                continue
                
            end_time = time.perf_counter()
            end_memory = process.memory_info().rss
            
            times.append(end_time - start_time)
            memory_usage.append(end_memory - start_memory)
            
        return {
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
            'avg_memory': statistics.mean(memory_usage),
            'num_runs': len(times)
        }

    def optimize_function(self, func_source: str) -> str:
        """Optimize a function using various techniques."""
        tree = ast.parse(func_source)
        transformer = OptimizationTransformer()
        optimized_tree = transformer.visit(tree)
        return ast.unparse(optimized_tree)

    def optimize_module(self, module_path: Path) -> Dict[str, str]:
        """Optimize all functions in a module."""
        with open(module_path, 'r') as f:
            source = f.read()

        tree = ast.parse(source)
        optimized_functions = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_source = ast.get_source_segment(source, node)
                if func_source:
                    try:
                        optimized_source = self.optimize_function(func_source)
                        if optimized_source != func_source:
                            optimized_functions[node.name] = optimized_source
                    except Exception as e:
                        self.logger.error(f"Error optimizing function {node.name}: {str(e)}")

        return optimized_functions

class OptimizationTransformer(ast.NodeTransformer):
    """AST transformer for optimizing code."""

    def __init__(self):
        self.loop_id = 0
        self.has_numpy = False

    def visit_Import(self, node):
        """Track numpy imports."""
        for name in node.names:
            if name.name == 'numpy':
                self.has_numpy = True
        return node

    def visit_ImportFrom(self, node):
        """Track numpy imports."""
        if node.module == 'numpy':
            self.has_numpy = True
        return node

    def visit_For(self, node):
        """Optimize for loops."""
        # Check if the loop can be vectorized
        if (isinstance(node.target, ast.Name) and
            isinstance(node.iter, ast.Call) and
            isinstance(node.iter.func, ast.Name) and
            node.iter.func.id == 'range'):
            
            # Add numpy import if needed
            if not self.has_numpy:
                self.has_numpy = True
                return ast.Module(
                    body=[
                        ast.Import(names=[ast.alias(name='numpy', asname='np')]),
                        self._vectorize_loop(node)
                    ],
                    type_ignores=[]
                )
            return self._vectorize_loop(node)
        
        return self.generic_visit(node)

    def _vectorize_loop(self, node):
        """Convert a for loop to vectorized numpy operations."""
        # Create a unique variable name for the array
        array_name = f'_array_{self.loop_id}'
        self.loop_id += 1

        # Create the array using numpy.arange
        array_creation = ast.Assign(
            targets=[ast.Name(id=array_name, ctx=ast.Store())],
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id='np', ctx=ast.Load()),
                    attr='arange',
                    ctx=ast.Load()
                ),
                args=node.iter.args,
                keywords=[]
            )
        )

        # Transform the loop body into vectorized operations
        vectorized_ops = self._transform_loop_body(node.body, array_name)
        
        return ast.Module(
            body=[array_creation] + vectorized_ops,
            type_ignores=[]
        )

    def _transform_loop_body(self, body, array_name):
        """Transform loop body into vectorized operations."""
        vectorized_ops = []
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                # Transform assignments into numpy operations
                if isinstance(stmt.value, ast.BinOp):
                    vectorized_ops.append(
                        ast.Assign(
                            targets=stmt.targets,
                            value=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id='np', ctx=ast.Load()),
                                    attr='sum',
                                    ctx=ast.Load()
                                ),
                                args=[
                                    ast.BinOp(
                                        left=ast.Name(id=array_name, ctx=ast.Load()),
                                        op=stmt.value.op,
                                        right=stmt.value.right
                                    )
                                ],
                                keywords=[]
                            )
                        )
                    )
        return vectorized_ops

class PerformanceOptimizationMigration:
    """Migration to automatically optimize slow functions."""

    def __init__(self, performance_threshold: float = 0.1):
        """Initialize the migration."""
        self.project_dir = None
        self.original_states = {}
        self.logger = logging.getLogger(__name__)
        self.optimizer = ExoOptimizer()
        self.performance_threshold = performance_threshold  # in seconds

    def set_project_dir(self, project_dir: Union[str, Path]):
        """Set the project directory."""
        self.project_dir = Path(project_dir)

    def check_if_needed(self) -> bool:
        """Check if migration is needed."""
        if not self.project_dir:
            raise ValueError("Project directory not set")

        for py_file in self.project_dir.rglob("*.py"):
            try:
                if self._analyze_module(py_file):
                    return True
            except Exception as e:
                self.logger.error(f"Error analyzing {py_file}: {str(e)}")

        return False

    def _analyze_module(self, module_path: Path) -> bool:
        """Analyze a module for slow functions."""
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(
                module_path.stem, str(module_path)
            )
            if not spec or not spec.loader:
                return False
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Check each function in the module
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj):
                    try:
                        benchmark = self.optimizer._benchmark_function(obj)
                        if benchmark['avg_time'] > self.performance_threshold:
                            return True
                    except Exception as e:
                        self.logger.error(f"Error benchmarking {name}: {str(e)}")

        except Exception as e:
            self.logger.error(f"Error analyzing module {module_path}: {str(e)}")

        return False

    def _optimize_module(self, module_path: Path):
        """Optimize slow functions in a module."""
        # Store original state
        with open(module_path, 'r') as f:
            original_content = f.read()
        self.original_states[module_path] = original_content

        # Optimize functions
        optimized_functions = self.optimizer.optimize_module(module_path)

        if optimized_functions:
            # Apply optimizations
            tree = ast.parse(original_content)
            transformer = OptimizedFunctionTransformer()
            
            for func_name, optimized_source in optimized_functions.items():
                try:
                    optimized_tree = ast.parse(optimized_source)
                    for node in ast.walk(optimized_tree):
                        if isinstance(node, ast.FunctionDef) and node.name == func_name:
                            transformer.replace_function(tree, func_name, node)
                            break
                except Exception as e:
                    self.logger.error(f"Error replacing function {func_name}: {str(e)}")

            # Write optimized code back to file
            try:
                with open(module_path, 'w') as f:
                    f.write(ast.unparse(tree))
            except Exception as e:
                self.logger.error(f"Error writing optimized code to {module_path}: {str(e)}")
                # Restore original content
                with open(module_path, 'w') as f:
                    f.write(original_content)

    def _up(self):
        """Apply performance optimizations."""
        if not self.project_dir:
            raise ValueError("Project directory not set")

        for py_file in self.project_dir.rglob("*.py"):
            try:
                if self._analyze_module(py_file):
                    self._optimize_module(py_file)
            except Exception as e:
                self.logger.error(f"Error processing {py_file}: {str(e)}")

    def _down(self):
        """Rollback the migration."""
        for path, content in self.original_states.items():
            try:
                with open(path, 'w') as f:
                    f.write(content)
            except Exception as e:
                self.logger.error(f"Error rolling back {path}: {str(e)}")

class OptimizedFunctionTransformer:
    """AST transformer for replacing functions with optimized versions."""

    def replace_function(self, tree: ast.AST, func_name: str, new_func: ast.FunctionDef):
        """Replace a function in the AST with an optimized version."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                # Copy over the new function's attributes
                node.body = new_func.body
                node.args = new_func.args
                node.decorator_list = new_func.decorator_list
                node.returns = new_func.returns
                break
