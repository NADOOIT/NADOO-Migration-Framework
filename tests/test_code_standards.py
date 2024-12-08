"""Tests to verify code standards, documentation, and naming conventions."""

import inspect
import re
from pathlib import Path
import pytest
import nadoo_migration_framework
from nadoo_migration_framework.src.nadoo_migration_framework.migrations.cleanup_project_structure import (
    CleanupProjectStructureMigration,
)


def get_all_python_files(base_path: Path) -> list[Path]:
    """Get all Python files in the project.

    Args:
        base_path (Path): Base directory to search from

    Returns:
        list[Path]: List of paths to Python files
    """
    return list(base_path.rglob("*.py"))


def get_all_classes(module) -> list:
    """Get all classes from a module.

    Args:
        module: Python module to inspect

    Returns:
        list: List of class objects
    """
    return [
        obj
        for name, obj in inspect.getmembers(module, inspect.isclass)
        if obj.__module__.startswith('nadoo_migration_framework')
    ]


def get_all_functions(module) -> list:
    """Get all functions from a module.

    Args:
        module: Python module to inspect

    Returns:
        list: List of function objects
    """
    return [
        obj
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if obj.__module__.startswith('nadoo_migration_framework')
    ]


def test_class_naming_convention():
    """Test that all class names follow PascalCase convention."""
    classes = get_all_classes(nadoo_migration_framework)
    pascal_case_pattern = re.compile(r'^[A-Z][a-zA-Z0-9]*$')

    violations = []
    for cls in classes:
        if not pascal_case_pattern.match(cls.__name__):
            violations.append(f"Class {cls.__name__} does not follow PascalCase convention")

    assert not violations, "\n".join(violations)


def test_function_naming_convention():
    """Test that all function names follow snake_case convention."""
    functions = get_all_functions(nadoo_migration_framework)
    snake_case_pattern = re.compile(r'^[a-z][a-z0-9_]*$')

    violations = []
    for func in functions:
        if not snake_case_pattern.match(func.__name__):
            violations.append(f"Function {func.__name__} does not follow snake_case convention")

    assert not violations, "\n".join(violations)


def test_class_docstrings():
    """Test that all classes have proper docstrings."""
    classes = get_all_classes(nadoo_migration_framework)

    violations = []
    for cls in classes:
        if not cls.__doc__:
            violations.append(f"Class {cls.__name__} is missing a docstring")
        elif len(cls.__doc__.strip().split('\n')) < 2:
            violations.append(f"Class {cls.__name__} has a too short docstring")

    assert not violations, "\n".join(violations)


def test_function_docstrings():
    """Test that all functions have proper docstrings."""
    functions = get_all_functions(nadoo_migration_framework)

    violations = []
    for func in functions:
        # Skip private functions (starting with _)
        if func.__name__.startswith('_'):
            continue

        if not func.__doc__:
            violations.append(f"Function {func.__name__} is missing a docstring")
        elif len(func.__doc__.strip().split('\n')) < 2:
            violations.append(f"Function {func.__name__} has a too short docstring")

    assert not violations, "\n".join(violations)


def test_docstring_format():
    """Test that docstrings follow Google style format."""
    classes = get_all_classes(nadoo_migration_framework)
    functions = get_all_functions(nadoo_migration_framework)

    def check_google_style(obj, violations):
        """Check if an object's docstring follows Google style."""
        if not obj.__doc__:
            return

        docstring = inspect.getdoc(obj)

        # Check for common Google style sections
        sections = ['Args:', 'Returns:', 'Raises:', 'Yields:', 'Examples:']
        has_section = any(section in docstring for section in sections)

        if len(docstring.strip().split('\n')) > 1 and not has_section:
            violations.append(f"{obj.__name__} docstring does not follow Google style format")

    violations = []

    for cls in classes:
        check_google_style(cls, violations)
        # Check methods
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            if not name.startswith('_'):  # Skip private methods
                check_google_style(method, violations)

    for func in functions:
        if not func.__name__.startswith('_'):  # Skip private functions
            check_google_style(func, violations)

    assert not violations, "\n".join(violations)


def test_test_function_naming():
    """Test that all test functions start with 'test_'."""
    test_files = get_all_python_files(Path(__file__).parent)

    # Common pytest fixture and helper function names that don't need test_ prefix
    allowed_prefixes = {
        'fixture_',
        'create_',
        'setup_',
        'mock_',
        'get_',
        'temp_',
        'helper_',
        'process_',
        'calculate_',
        'update_',
        'verify_',
        'find_',
        'add_',
        'run_',
        'start_',
        'stop_',
        'interrupt_',
        'check_',
        '_',
        'main',
        'slow_',
        'matrix_',
        'recursive_',
        'nested_',
        'mixed_',
        'memory_',
        'large_',
        'curry_',
        'feed_',
        'brain_',
        'home_',
        'startup_',
        'send_',
        'discover_',
        'shared_',
        'sample_',
        'is_',
        'post_',
        'complete',
        'hide',
        'remove_',
        'voice_',
        'another_',
    }

    # Files that are allowed to have non-test functions (e.g., test utilities)
    allowed_files = {'test_utils.py', 'test_toga_import_migrations.py', 'conftest.py'}

    violations = []
    for test_file in test_files:
        # Skip files that are allowed to have non-test functions
        if test_file.name in allowed_files:
            continue

        with open(test_file, 'r') as f:
            content = f.read()

        # Skip checking helper functions in fixtures
        if '@pytest.fixture' in content:
            continue

        # Find all function definitions that use pytest decorators (except fixtures)
        pytest_funcs = re.finditer(r'@pytest\.(?!fixture).*\ndef\s+(\w+)\s*\(', content)
        for match in pytest_funcs:
            func_name = match.group(1)
            if not func_name.startswith('test_'):
                violations.append(
                    f"Pytest function {func_name} in {test_file.name} "
                    "does not start with 'test_'"
                )

        # Find regular functions that aren't fixtures or helpers
        func_defs = re.finditer(r'def\s+(\w+)\s*\(', content)
        for match in func_defs:
            func_name = match.group(1)
            # Skip if it's a helper function or already a test
            if func_name.startswith('test_'):
                continue
            if any(prefix in func_name for prefix in allowed_prefixes):
                continue
            # Check if it's used by a test function
            if re.search(rf'test_.*\W{func_name}\W', content):
                continue

            violations.append(
                f"Function {func_name} in {test_file.name} "
                "should either start with 'test_' or be a recognized helper function"
            )

    assert not violations, "\n".join(violations)
