"""Test suite for Briefcase and Toga migration."""

import os
import pytest
import toml
from pathlib import Path
from nadoo_migration_framework.version import Version, ProjectVersion
from nadoo_migration_framework.migrations.add_briefcase_toga import AddBriefcaseTogaMigration


def test_project_needs_briefcase_toga(tmp_path):
    """Test to check if project needs Briefcase and Toga migration."""
    # Create a test project structure
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    # Create minimal pyproject.toml
    pyproject = {
        'tool': {
            'poetry': {
                'name': 'test-project',
                'version': '0.1.0',
                'description': 'Test project',
                'authors': ['Test Author <test@example.com>'],
                'dependencies': {'python': '>=3.9'},
            }
        }
    }

    with open(project_dir / "pyproject.toml", 'w') as f:
        toml.dump(pyproject, f)

    # Check if Briefcase and Toga are missing
    with open(project_dir / "pyproject.toml", 'r') as f:
        config = toml.load(f)

    assert 'briefcase' not in config.get('tool', {})
    assert 'toga' not in config.get('tool', {}).get('poetry', {}).get('dependencies', {})


def test_migration_adds_briefcase_toga(tmp_path):
    """Test that migration properly adds Briefcase and Toga support."""
    # Create test project
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    # Create minimal pyproject.toml
    pyproject = {
        'tool': {
            'poetry': {
                'name': 'test-project',
                'version': '0.1.0',
                'description': 'Test project',
                'authors': ['Test Author <test@example.com>'],
                'dependencies': {'python': '>=3.9'},
            }
        }
    }

    with open(project_dir / "pyproject.toml", 'w') as f:
        toml.dump(pyproject, f)

    # Run migration
    migration = AddBriefcaseTogaMigration()
    success = migration.migrate(str(project_dir))
    assert success

    # Verify changes
    with open(project_dir / "pyproject.toml", 'r') as f:
        config = toml.load(f)

    # Check Toga dependency
    deps = config['tool']['poetry']['dependencies']
    assert 'toga' in deps
    assert deps['toga']['version'] == '>=0.4.0'
    assert deps['toga']['platform'] == 'darwin'
    assert deps['toga']['extras'] == ['cocoa']

    # Check Briefcase configuration
    briefcase = config['tool']['briefcase']
    assert briefcase['project_name'] == 'Test Project'
    assert briefcase['bundle'] == 'it.nadoo.testproject'

    # Check platform-specific configurations
    app_config = briefcase['app']['test_project']
    assert 'macOS' in app_config
    assert 'linux' in app_config
    assert 'windows' in app_config

    # Check resources directory
    resources_dir = project_dir / "src" / "test_project" / "resources"
    assert resources_dir.exists()


def test_migration_rollback(tmp_path):
    """Test that migration rollback properly removes Briefcase and Toga."""
    # Create test project
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    # Create pyproject.toml with Briefcase and Toga
    pyproject = {
        'tool': {
            'poetry': {
                'name': 'test-project',
                'version': '0.1.0',
                'description': 'Test project',
                'authors': ['Test Author <test@example.com>'],
                'dependencies': {
                    'python': '>=3.9',
                    'toga': {'version': '>=0.4.0', 'platform': 'darwin', 'extras': ['cocoa']},
                },
            },
            'briefcase': {'project_name': 'Test Project', 'bundle': 'it.nadoo.testproject'},
        }
    }

    with open(project_dir / "pyproject.toml", 'w') as f:
        toml.dump(pyproject, f)

    # Run rollback
    migration = AddBriefcaseTogaMigration()
    success = migration.rollback(str(project_dir))
    assert success

    # Verify changes
    with open(project_dir / "pyproject.toml", 'r') as f:
        config = toml.load(f)

    # Check Toga and Briefcase are removed
    assert 'toga' not in config['tool']['poetry']['dependencies']
    assert 'briefcase' not in config['tool']
