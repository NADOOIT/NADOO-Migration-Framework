"""Tests for Toga migrations."""

import ast
from pathlib import Path
import pytest

from nadoo_migration_framework.migrations.toga_functional_migrations import (
    CreateFunctionDirectoryMigration,
    ExtractCurriedFunctionsMigration,
    ExtractRegularFunctionsMigration
)
from nadoo_migration_framework.migrations.toga_import_migrations import (
    ConsolidateImportsMigration
)

@pytest.fixture
def temp_toga_project(tmp_path):
    """Create a temporary Toga project."""
    # Create src directory
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    
    # Create test files
    view_file = src_dir / "view.py"
    with open(view_file, "w") as f:
        f.write("""import toga
from toga.style import Pack
from toga.style import TOP  # unused
from typing import List, Dict  # Dict unused

def curry_function(x):
    \"\"\"Return a function that adds x to its argument.\"\"\"
    return lambda y: x + y

def calculate_result(x, y):
    \"\"\"Calculate result from x and y.\"\"\"
    return x + y

class MainWindow(toga.MainWindow):
    def __init__(self):
        super().__init__()
        self.style = Pack()
        self.items: List = []
        
    def add_item(self, item):
        \"\"\"Add an item to the list.\"\"\"
        self.items.append(item)
""")
    
    return tmp_path

def test_create_function_directory(temp_toga_project):
    """Test creating the functions directory."""
    migration = CreateFunctionDirectoryMigration()
    migration.project_dir = temp_toga_project
    
    # Check if migration is needed
    assert migration.check_if_needed()
    
    # Apply migration
    migration.up()
    
    # Verify directory was created
    functions_dir = temp_toga_project / "src" / "functions"
    assert functions_dir.exists()
    assert (functions_dir / "__init__.py").exists()
    
    # Test rollback
    migration.down()
    assert not functions_dir.exists()

def test_extract_curried_functions(temp_toga_project):
    """Test extracting curried functions."""
    # First create functions directory
    dir_migration = CreateFunctionDirectoryMigration()
    dir_migration.project_dir = temp_toga_project
    dir_migration.up()
    
    # Now extract curried functions
    migration = ExtractCurriedFunctionsMigration()
    migration.project_dir = temp_toga_project
    
    # Check if migration is needed
    assert migration.check_if_needed()
    
    # Apply migration
    migration.up()
    
    # Verify curried function was extracted
    functions_dir = temp_toga_project / "src" / "functions"
    curry_file = functions_dir / "curry_function.py"
    assert curry_file.exists()
    
    # Check file contents
    with open(curry_file) as f:
        content = f.read()
        assert "def curry_function(x: T) -> Callable[[U], T]:" in content
        assert "return lambda y: x + y" in content
        assert "TypeVar" in content  # Should have type hints
    
    # Test rollback
    migration.down()
    assert not curry_file.exists()

def test_extract_regular_functions(temp_toga_project):
    """Test extracting regular functions."""
    # First create functions directory
    dir_migration = CreateFunctionDirectoryMigration()
    dir_migration.project_dir = temp_toga_project
    dir_migration.up()
    
    # Now extract regular functions
    migration = ExtractRegularFunctionsMigration()
    migration.project_dir = temp_toga_project
    
    # Check if migration is needed
    assert migration.check_if_needed()
    
    # Apply migration
    migration.up()
    
    # Verify regular function was extracted
    functions_dir = temp_toga_project / "src" / "functions"
    calc_file = functions_dir / "calculate_result.py"
    assert calc_file.exists()
    
    # Check file contents
    with open(calc_file) as f:
        content = f.read()
        assert "def calculate_result(x, y):" in content
        assert "return x + y" in content
    
    # Test rollback
    migration.down()
    assert not calc_file.exists()

def test_consolidate_imports(temp_toga_project):
    """Test consolidating imports."""
    # Create a file with unused imports
    view_file = temp_toga_project / "src" / "view.py"
    with open(view_file, "w") as f:
        f.write("""import toga
import sys  # unused
from toga.style import Pack
from toga.style import TOP  # unused
from typing import List, Dict  # Dict unused

class MainWindow(toga.MainWindow):
    def __init__(self):
        super().__init__()
        self.style = Pack()
        self.items: List = []
""")
    
    migration = ConsolidateImportsMigration()
    migration.project_dir = temp_toga_project
    
    # Check if migration is needed
    assert migration.check_if_needed()
    
    # Apply migration
    migration.up()
    
    # Verify imports were cleaned up
    with open(view_file) as f:
        content = f.read()
        assert "import sys" not in content
        assert "TOP" not in content
        assert "Dict" not in content
        assert "import toga" in content
        assert "from toga.style import Pack" in content
        assert "from typing import List" in content
    
    # Test rollback
    migration.down()
    with open(view_file) as f:
        content = f.read()
        assert "import sys" in content
        assert "TOP" in content
        assert "Dict" in content

def test_migration_sequence(temp_toga_project):
    """Test running all migrations in sequence."""
    migrations = [
        CreateFunctionDirectoryMigration(),
        ExtractCurriedFunctionsMigration(),
        ExtractRegularFunctionsMigration(),
        ConsolidateImportsMigration()
    ]
    
    # Apply migrations in sequence
    for migration in migrations:
        migration.project_dir = temp_toga_project
        if migration.check_if_needed():
            migration.up()
    
    # Verify final state
    functions_dir = temp_toga_project / "src" / "functions"
    assert functions_dir.exists()
    assert (functions_dir / "__init__.py").exists()
    assert (functions_dir / "curry_function.py").exists()
    assert (functions_dir / "calculate_result.py").exists()
    
    # Original view file should only have MainWindow class
    with open(temp_toga_project / "src" / "view.py") as f:
        content = f.read()
        tree = ast.parse(content)
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        assert len(classes) == 1
        assert len(functions) == 0
    
    # Rollback migrations in reverse order
    for migration in reversed(migrations):
        migration.down()
    
    # Verify everything is back to original state
    assert not functions_dir.exists()
    with open(temp_toga_project / "src" / "view.py") as f:
        content = f.read()
        tree = ast.parse(content)
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        assert len(classes) == 1
        assert len(functions) == 2  # curry_function and calculate_result
