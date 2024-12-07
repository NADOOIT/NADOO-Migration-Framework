"""Test suite for verifying code coverage before and after migration."""

import os
import sys
import pytest
import coverage
import subprocess
from pathlib import Path
from nadoo_migration_framework.migrations.cleanup_project_structure import CleanupProjectStructureMigration

def run_coverage(project_path: Path, source_dir: str) -> float:
    """Run coverage on the project and return the coverage percentage."""
    # Create a temporary conftest.py to set up test environment
    conftest_content = '''
import os
import sys
import pytest

@pytest.fixture(autouse=True)
def add_src_to_path():
    """Add src directory to Python path."""
    project_root = os.path.dirname(os.path.dirname(__file__))
    src_path = os.path.join(project_root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    yield
    if src_path in sys.path:
        sys.path.remove(src_path)
'''
    (project_path / 'tests' / 'conftest.py').write_text(conftest_content)
    
    # Run pytest with coverage in a subprocess
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_path / 'src')
    
    # Run coverage
    subprocess.run([
        'coverage', 'run',
        '--source', str(project_path / source_dir),
        '-m', 'pytest',
        str(project_path / 'tests'),
        '--quiet'
    ], env=env, cwd=str(project_path))
    
    # Generate coverage report
    result = subprocess.run(
        ['coverage', 'report'],
        env=env,
        cwd=str(project_path),
        capture_output=True,
        text=True
    )
    
    # Parse coverage percentage from output
    for line in result.stdout.split('\n'):
        if line.strip().startswith('TOTAL'):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    return float(parts[3].rstrip('%'))
                except ValueError:
                    return 0.0
    return 0.0

def create_test_project(base_path: Path):
    """Create a test project with 100% testable code coverage."""
    # Create project structure
    (base_path / 'src' / 'functions').mkdir(parents=True)
    (base_path / 'tests').mkdir()
    
    # Create __init__.py files for proper Python packages
    (base_path / 'src' / '__init__.py').touch()
    (base_path / 'src' / 'functions' / '__init__.py').touch()
    (base_path / 'tests' / '__init__.py').touch()
    
    # Create a simple function with full test coverage
    function_code = '''
def calculate_factorial(n: int) -> int:
    """Calculate factorial of n."""
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0:
        return 1
    return n * calculate_factorial(n - 1)

def is_prime(n: int) -> bool:
    """Check if a number is prime."""
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True
'''
    
    (base_path / 'src' / 'functions' / 'math_utils.py').write_text(function_code)
    
    # Create corresponding test
    test_code = '''
import pytest
from functions.math_utils import calculate_factorial, is_prime

def test_factorial_positive():
    assert calculate_factorial(5) == 120
    assert calculate_factorial(0) == 1
    assert calculate_factorial(1) == 1

def test_factorial_negative():
    with pytest.raises(ValueError):
        calculate_factorial(-1)

def test_is_prime():
    assert is_prime(2) == True
    assert is_prime(3) == True
    assert is_prime(4) == False
    assert is_prime(17) == True
    assert is_prime(1) == False
    assert is_prime(0) == False
    assert is_prime(-1) == False
'''
    
    (base_path / 'tests' / 'test_math_utils.py').write_text(test_code)
    
    # Create pyproject.toml
    pyproject_content = '''[tool.poetry]
name = "test-coverage-project"
version = "0.1.0"
description = "Test project for coverage analysis"

[tool.poetry.dependencies]
python = "^3.8"
pytest = "^7.0.0"
coverage = "^7.0.0"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
'''
    
    (base_path / 'pyproject.toml').write_text(pyproject_content)

def update_test_imports(project_path: Path) -> None:
    """Update test imports after migration."""
    project_name = project_path.name.replace('-', '_')
    test_file = project_path / 'tests' / 'test_math_utils.py'
    
    # Read current content
    content = test_file.read_text()
    
    # Update import statement
    content = content.replace(
        'from functions.math_utils',
        f'from {project_name}.functions.math_utils'
    )
    
    # Write updated content
    test_file.write_text(content)
    
    # Create __init__.py in tests directory if it doesn't exist
    test_init = project_path / 'tests' / '__init__.py'
    if not test_init.exists():
        test_init.touch()

def test_migration_preserves_coverage(tmp_path):
    """Test that code coverage remains 100% after migration."""
    # Create test project
    create_test_project(tmp_path)
    
    # Run coverage before migration
    pre_migration_coverage = run_coverage(tmp_path, 'src/functions')
    assert pre_migration_coverage == 100.0, "Pre-migration code coverage is not 100%"
    
    # Run migration
    migration = CleanupProjectStructureMigration()
    success = migration.migrate(str(tmp_path))
    assert success, "Migration failed"
    
    # Update test imports
    update_test_imports(tmp_path)
    
    # Run coverage after migration
    project_name = tmp_path.name.replace('-', '_')
    post_migration_coverage = run_coverage(tmp_path, f'src/{project_name}/functions')
    assert post_migration_coverage == 100.0, "Post-migration code coverage is not 100%"
    
    # Verify that all tests still pass using subprocess
    env = os.environ.copy()
    env['PYTHONPATH'] = str(tmp_path / 'src')
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', '--quiet', 'tests'],
        cwd=str(tmp_path),
        env=env,
        capture_output=True
    )
    assert result.returncode == 0, "Tests failed after migration"

def test_migration_preserves_functionality(tmp_path):
    """Test that all functionality works exactly the same after migration."""
    create_test_project(tmp_path)
    
    # Import and test functions before migration
    sys.path.insert(0, str(tmp_path / 'src'))
    from functions.math_utils import calculate_factorial, is_prime
    
    pre_migration_results = {
        'factorial_5': calculate_factorial(5),
        'factorial_0': calculate_factorial(0),
        'prime_17': is_prime(17),
        'prime_4': is_prime(4)
    }
    
    sys.path.pop(0)
    
    # Run migration
    migration = CleanupProjectStructureMigration()
    success = migration.migrate(str(tmp_path))
    assert success
    
    # Update test imports
    update_test_imports(tmp_path)
    
    # Import and test functions after migration
    project_name = tmp_path.name.replace('-', '_')
    sys.path.insert(0, str(tmp_path / 'src'))
    module = __import__(f"{project_name}.functions.math_utils", fromlist=['calculate_factorial', 'is_prime'])
    
    post_migration_results = {
        'factorial_5': module.calculate_factorial(5),
        'factorial_0': module.calculate_factorial(0),
        'prime_17': module.is_prime(17),
        'prime_4': module.is_prime(4)
    }
    
    sys.path.pop(0)
    
    # Compare results
    assert pre_migration_results == post_migration_results, "Function results changed after migration"
    
    # Verify error handling is preserved
    sys.path.insert(0, str(tmp_path / 'src'))
    module = __import__(f"{project_name}.functions.math_utils", fromlist=['calculate_factorial'])
    with pytest.raises(ValueError):
        module.calculate_factorial(-1)
    sys.path.pop(0)
