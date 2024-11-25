"""Tests for BRAIN migrations."""

import os
import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from nadoo_migration_framework.frameworks.brain_migration import BrainMigration
from nadoo_migration_framework.migrations.brain_test_migration import BrainTestMigration

@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def brain_project_dir():
    """Create a temporary BRAIN project directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        brain_dir = Path(temp_dir)
        # Create some dummy BRAIN project files
        (brain_dir / 'brain_config.toml').write_text("""
[brain]
version = "1.0.0"
name = "test-brain-project"

[functions]
calculate_total = "brain.math.calculate_total"
process_data = "brain.data.process_data"
""")
        yield brain_dir

@pytest.fixture
def test_migration(temp_project_dir, brain_project_dir):
    """Create a test migration instance."""
    migration = BrainTestMigration()
    migration.set_project_dir(temp_project_dir)
    migration.set_brain_project_dir(brain_project_dir)
    return migration

def test_brain_migration_initialization():
    """Test BrainMigration initialization."""
    migration = BrainMigration()
    assert migration is not None
    assert hasattr(migration, 'project_dir')
    assert hasattr(migration, 'brain_project_dir')

def test_test_migration_initialization(test_migration):
    """Test BrainTestMigration initialization."""
    assert test_migration is not None
    assert len(test_migration.test_functions) == 3
    assert 'calculate_total' in test_migration.test_functions
    assert 'process_data' in test_migration.test_functions
    assert 'complex_operation' in test_migration.test_functions

def test_analyze_function_compatibility(test_migration):
    """Test function compatibility analysis."""
    compatible, incompatible = test_migration.analyze_function_compatibility()
    
    # Should find two compatible functions
    assert len(compatible) == 2
    assert 'calculate_total' in [f['name'] for f in compatible]
    assert 'process_data' in [f['name'] for f in compatible]
    
    # Should find one incompatible function
    assert len(incompatible) == 1
    assert 'complex_operation' in [f['name'] for f in incompatible]

def test_migrate_to_brain(test_migration, capsys):
    """Test migration to BRAIN."""
    # First analyze compatibility
    compatible, incompatible = test_migration.analyze_function_compatibility()
    
    # Migrate compatible functions
    success = test_migration.migrate_to_brain()
    assert success
    
    # Check output
    captured = capsys.readouterr()
    assert "Simulating migration of calculate_total to BRAIN" in captured.out
    assert "Simulating migration of process_data to BRAIN" in captured.out
    assert "Simulating BRAIN config update" in captured.out

def test_migrate_from_brain(test_migration, capsys):
    """Test migration from BRAIN."""
    # First analyze compatibility
    compatible, incompatible = test_migration.analyze_function_compatibility()
    
    # Migrate compatible functions
    success = test_migration.migrate_from_brain()
    assert success
    
    # Check output
    captured = capsys.readouterr()
    assert "Simulating migration of calculate_total from BRAIN" in captured.out
    assert "Simulating migration of process_data from BRAIN" in captured.out
    assert "Simulating NADOO config update" in captured.out

def test_brain_config_update(test_migration, capsys):
    """Test BRAIN config update."""
    test_migration._update_brain_config()
    
    captured = capsys.readouterr()
    assert "Simulating BRAIN config update" in captured.out
    assert "Updating function mappings" in captured.out
    assert "Registering migrated functions" in captured.out
    assert "Updating dependencies" in captured.out

def test_nadoo_config_update(test_migration, capsys):
    """Test NADOO config update."""
    test_migration._update_nadoo_config()
    
    captured = capsys.readouterr()
    assert "Simulating NADOO config update" in captured.out
    assert "Updating function mappings" in captured.out
    assert "Registering migrated functions" in captured.out
    assert "Updating dependencies" in captured.out

@patch('nadoo_migration_framework.cli.brain_commands.BrainMigration', BrainTestMigration)
def test_cli_brain_commands():
    """Test CLI brain commands."""
    from nadoo_migration_framework.cli.brain_commands import brain
    from click.testing import CliRunner
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        # Create a test BRAIN project
        os.makedirs('brain_project')
        
        # Create a test function to migrate
        os.makedirs('brain_project/brain')
        with open('brain_project/brain/__init__.py', 'w') as f:
            f.write("")
        with open('brain_project/brain/test_functions.py', 'w') as f:
            f.write("""
def calculate_total(items: List[float]) -> float:
    return sum(items)

def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v.upper() if isinstance(v, str) else v for k, v in data.items()}
""")
        
        # Create a NADOO project with compatible functions
        os.makedirs('nadoo')
        with open('nadoo/__init__.py', 'w') as f:
            f.write("")
        with open('nadoo/functions.py', 'w') as f:
            f.write("""
def calculate_total(items: List[float]) -> float:
    return sum(items)

def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v.upper() if isinstance(v, str) else v for k, v in data.items()}
""")
        
        # Test analyze command
        result = runner.invoke(brain, ['analyze', 'brain_project'])
        assert result.exit_code == 0
        assert "Compatibility Analysis Results" in result.output
        
        # Test migrate-to-brain command with dry run
        result = runner.invoke(brain, ['migrate-to-brain', 'brain_project', '--dry-run'])
        assert result.exit_code == 0
        assert "Found compatible functions" in result.output
        assert "calculate_total" in result.output
        assert "process_data" in result.output
        assert "Dry run completed" in result.output
        
        # Test migrate-from-brain command with dry run
        result = runner.invoke(brain, ['migrate-from-brain', 'brain_project', '--dry-run'])
        assert result.exit_code == 0
        assert "Found compatible functions" in result.output
        assert "calculate_total" in result.output
        assert "process_data" in result.output
        assert "Dry run completed" in result.output

def test_incompatible_function_handling(test_migration):
    """Test handling of incompatible functions."""
    # Get all functions including incompatible ones
    all_functions = test_migration._analyze_project_functions(test_migration.project_dir)
    
    # Find the incompatible function
    incompatible_func = next(f for f in all_functions if f['name'] == 'complex_operation')
    
    # Check compatibility
    is_compatible = test_migration._is_compatible_with_brain(incompatible_func, [])
    assert not is_compatible
    
    # Ensure it's marked as incompatible in test_functions
    assert not test_migration.test_functions['complex_operation']['compatible']
    assert 'numpy' in test_migration.test_functions['complex_operation']['dependencies']
