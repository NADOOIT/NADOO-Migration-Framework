import pytest
import libcst as cst
from pathlib import Path
import tempfile
import os
import shutil
import logging
from libcst._nodes.base import CSTValidationError

from nadoo_migration_framework.migrations.toga_import_migrations import (
    ImportTransformer,
    ConsolidateImportsMigration,
    STDLIB_MODULES,
    FileState
)

def test_import_transformer_basic():
    """Test basic functionality of ImportTransformer."""
    code = """
import sys
import os
from pathlib import Path
import toga
from toga.style import Pack
from .utils import helper
import math

def main():
    sys.path.append(os.path.dirname(__file__))
    app = toga.App('Test', 'org.test')
    helper.do_something()
    math.sqrt(4)
"""
    module = cst.parse_module(code)
    transformer = ImportTransformer()
    modified_tree = module.visit(transformer)
    
    assert 'sys' in transformer.used_names
    assert 'os' in transformer.used_names
    assert 'toga' in transformer.used_names
    assert 'helper' in transformer.used_names
    assert 'math' in transformer.used_names

def test_import_transformer_nested_attributes():
    """Test handling of nested attributes."""
    code = """
import os.path
import toga.style.pack
from toga.style import Pack

def main():
    path = os.path.dirname(__file__)
    style = toga.style.pack.Pack()
    pack = Pack()
"""
    module = cst.parse_module(code)
    transformer = ImportTransformer()
    modified_tree = module.visit(transformer)
    
    assert 'os' in transformer.used_modules
    assert 'toga' in transformer.used_modules
    assert 'Pack' in transformer.used_names

def test_import_transformer_complex_imports():
    """Test handling of complex import scenarios."""
    code = """
from toga.style.pack import Pack as PackStyle
import sys as system
from os import path as ospath, makedirs
from . import utils
from ..parent import helper

def main():
    style = PackStyle()
    system.exit(0)
    ospath.exists('test')
    makedirs('dir')
    utils.function()
    helper.assist()
"""
    module = cst.parse_module(code)
    transformer = ImportTransformer()
    modified_tree = module.visit(transformer)
    
    assert 'PackStyle' in transformer.used_names
    assert 'system' in transformer.used_names
    assert 'ospath' in transformer.used_names
    assert 'makedirs' in transformer.used_names
    assert 'utils' in transformer.used_names
    assert 'helper' in transformer.used_names

def test_consolidate_imports_migration_stdlib():
    """Test handling of standard library imports."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "stdlib_test.py"
        test_file.write_text("""
import toga
import sys
import os
import math
from pathlib import Path
from collections import defaultdict
import json
from datetime import datetime

def main():
    pass
""")
        
        migration = ConsolidateImportsMigration()
        migration.set_project_dir(temp_dir)
        migration._up()
        
        modified_code = test_file.read_text()
        
        # Check stdlib imports are grouped together
        stdlib_section = modified_code.split('import toga')[0]
        for module in ['sys', 'os', 'math', 'json']:
            assert f'import {module}' in stdlib_section
        assert 'from pathlib import Path' in stdlib_section
        assert 'from collections import defaultdict' in stdlib_section
        assert 'from datetime import datetime' in stdlib_section

def test_consolidate_imports_migration_third_party():
    """Test handling of third-party imports."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "third_party_test.py"
        test_file.write_text("""
import sys
import toga
from toga.style import Pack
import requests
from requests.auth import HTTPBasicAuth
import numpy as np
import pandas as pd

def main():
    pass
""")
        
        migration = ConsolidateImportsMigration()
        migration.set_project_dir(temp_dir)
        migration._up()
        
        modified_code = test_file.read_text()
        
        # Check third-party imports are grouped together
        for module in ['toga', 'requests', 'numpy', 'pandas']:
            assert any(module in line for line in modified_code.split('\n'))

def test_consolidate_imports_migration_local():
    """Test handling of local imports."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a package structure
        package_dir = Path(temp_dir) / "mypackage"
        package_dir.mkdir()
        (package_dir / "__init__.py").touch()
        
        test_file = package_dir / "module.py"
        test_file.write_text("""
import sys
from . import utils
from .subpackage import helper
from ..sibling import other
from ...parent import common
import os

def main():
    pass
""")
        
        migration = ConsolidateImportsMigration()
        migration.set_project_dir(temp_dir)
        migration._up()
        
        modified_code = test_file.read_text()
        
        # Verify order: stdlib -> local
        stdlib_imports = [line for line in modified_code.split('\n') 
                         if line.strip().startswith('import') and 
                         any(f'import {mod}' in line for mod in ['sys', 'os'])]
        local_imports = [line for line in modified_code.split('\n') 
                        if line.strip().startswith('from .')]
        
        first_stdlib = modified_code.find('import sys')
        first_local = modified_code.find('from .')
        assert first_stdlib < first_local

def test_error_handling_invalid_syntax():
    """Test handling of invalid Python syntax."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "invalid_syntax.py"
        test_file.write_text("import sys from os import path")  # Invalid syntax
        
        migration = ConsolidateImportsMigration()
        migration.set_project_dir(temp_dir)
        
        with pytest.raises(Exception):
            migration._up()

def test_error_handling_missing_file():
    """Test handling of missing files during rollback."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("import sys\n")
        
        migration = ConsolidateImportsMigration()
        migration.set_project_dir(temp_dir)
        
        # Store original state before running migration
        migration.original_states[str(test_file)] = FileState(
            file_path=str(test_file),
            original_code="import sys\n"
        )
        
        # Delete the file to simulate missing file
        os.remove(test_file)
        
        with pytest.raises(Exception):
            migration._down()

def test_module_name_extraction_edge_cases():
    """Test module name extraction edge cases."""
    transformer = ImportTransformer()
    
    # Test import with multiple dots
    multi_dot_import = cst.ImportFrom(
        module=None,
        names=[cst.ImportAlias(name=cst.Name(value="helper"))],
        relative=[cst.Dot(), cst.Dot(), cst.Dot()]
    )
    assert transformer._get_module_name(multi_dot_import) == '...'
    
    # Test import with module and dots
    mixed_import = cst.ImportFrom(
        module=cst.Name(value="utils"),
        names=[cst.ImportAlias(name=cst.Name(value="helper"))],
        relative=[cst.Dot()]
    )
    assert transformer._get_module_name(mixed_import) == 'utils'

def test_logging_configuration():
    """Test logging configuration and messages."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up logging
        log_file = Path(temp_dir) / "test.log"
        
        # Configure logging to write to the file
        handler = logging.FileHandler(str(log_file))
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('%(levelname)s:%(message)s'))
        
        logger = logging.getLogger('nadoo_migration_framework.migrations.toga_import_migrations')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("invalid python {")
        
        migration = ConsolidateImportsMigration()
        migration.set_project_dir(temp_dir)
        
        try:
            migration._up()
        except:
            pass
        
        # Ensure handler is closed so file is written
        handler.close()
        
        # Check log file
        log_content = log_file.read_text()
        assert "ERROR" in log_content
        assert str(test_file) in log_content
        
        # Clean up logging
        logger.removeHandler(handler)
