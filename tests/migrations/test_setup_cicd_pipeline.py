"""Tests for the CI/CD pipeline setup migration."""
import os
import yaml
from pathlib import Path
import pytest
from typing import Generator

from nadoo_migration_framework.migrations.setup_cicd_pipeline import SetupCICDPipelineMigration


@pytest.fixture
def migration() -> SetupCICDPipelineMigration:
    """Fixture for the migration class.
    
    Returns:
        SetupCICDPipelineMigration: The migration class instance.
    """
    return SetupCICDPipelineMigration()


@pytest.fixture
def cleanup() -> Generator[None, None, None]:
    """Cleanup fixture to remove generated files after tests.
    
    Yields:
        None
    """
    yield
    github_dir = Path(".github")
    if github_dir.exists():
        workflows_dir = github_dir / "workflows"
        if workflows_dir.exists():
            for file in workflows_dir.glob("*.yml"):
                file.unlink()
            workflows_dir.rmdir()
        
        dependabot_file = github_dir / "dependabot.yml"
        if dependabot_file.exists():
            dependabot_file.unlink()
        
        if not any(github_dir.iterdir()):
            github_dir.rmdir()


def test_migration_initialization(migration: SetupCICDPipelineMigration) -> None:
    """Test migration initialization.
    
    Args:
        migration: The migration instance.
    """
    assert migration.migration_id == "setup_cicd_pipeline"
    assert migration.description == "Sets up CI/CD pipeline configuration files"


def test_generate_workflow_file(migration: SetupCICDPipelineMigration, cleanup: None) -> None:
    """Test workflow file generation.
    
    Args:
        migration: The migration instance.
        cleanup: Cleanup fixture.
    """
    test_content = {
        "name": "Test",
        "on": "push",
        "jobs": {"test": {"runs-on": "ubuntu-latest"}}
    }
    migration.generate_workflow_file("test.yml", test_content)
    
    workflow_path = Path(".github/workflows/test.yml")
    assert workflow_path.exists()
    
    with open(workflow_path) as f:
        content = yaml.safe_load(f)
    assert content == test_content


def test_generate_ci_workflow(migration: SetupCICDPipelineMigration, cleanup: None) -> None:
    """Test CI workflow generation.
    
    Args:
        migration: The migration instance.
        cleanup: Cleanup fixture.
    """
    migration.generate_ci_workflow()
    
    workflow_path = Path(".github/workflows/ci.yml")
    assert workflow_path.exists()
    
    with open(workflow_path) as f:
        content = yaml.safe_load(f)
    
    assert content["name"] == "CI"
    assert "push" in content["on"]
    assert "pull_request" in content["on"]
    assert "test" in content["jobs"]
    
    test_job = content["jobs"]["test"]
    assert test_job["runs-on"] == "ubuntu-latest"
    assert all(version in test_job["strategy"]["matrix"]["python-version"]
              for version in ["3.8", "3.9", "3.10", "3.11"])
    
    steps = test_job["steps"]
    step_names = [step["name"] for step in steps]
    assert "Checkout" in step_names
    assert "Python Setup" in step_names
    assert "Install Deps" in step_names
    assert "Run Tests" in step_names
    assert "Coverage" in step_names


def test_generate_cd_workflow(migration: SetupCICDPipelineMigration, cleanup: None) -> None:
    """Test CD workflow generation.
    
    Args:
        migration: The migration instance.
        cleanup: Cleanup fixture.
    """
    migration.generate_cd_workflow()
    
    workflow_path = Path(".github/workflows/cd.yml")
    assert workflow_path.exists()
    
    with open(workflow_path) as f:
        content = yaml.safe_load(f)
    
    assert content["name"] == "CD"
    assert content["on"]["push"]["tags"] == ["v*"]
    assert "deploy" in content["jobs"]
    
    deploy_job = content["jobs"]["deploy"]
    assert deploy_job["runs-on"] == "ubuntu-latest"
    
    steps = deploy_job["steps"]
    step_names = [step["name"] for step in steps]
    assert "Checkout" in step_names
    assert "Python Setup" in step_names
    assert "Build" in step_names
    assert "Publish" in step_names


def test_generate_codeql_workflow(migration: SetupCICDPipelineMigration, cleanup: None) -> None:
    """Test CodeQL workflow generation.
    
    Args:
        migration: The migration instance.
        cleanup: Cleanup fixture.
    """
    migration.generate_codeql_workflow()
    
    workflow_path = Path(".github/workflows/codeql.yml")
    assert workflow_path.exists()
    
    with open(workflow_path) as f:
        content = yaml.safe_load(f)
    
    assert content["name"] == "CodeQL"
    assert content["on"]["push"]["branches"] == ["main"]
    assert content["on"]["pull_request"]["branches"] == ["main"]
    assert content["on"]["schedule"][0]["cron"] == "30 1 * * 0"
    assert "analyze" in content["jobs"]
    
    analyze_job = content["jobs"]["analyze"]
    assert analyze_job["runs-on"] == "ubuntu-latest"
    assert analyze_job["permissions"]["security-events"] == "write"
    
    steps = analyze_job["steps"]
    step_names = [step["name"] for step in steps]
    assert "Checkout" in step_names
    assert "Initialize" in step_names
    assert "Autobuild" in step_names
    assert "Perform Analysis" in step_names


def test_generate_dependabot_config(migration: SetupCICDPipelineMigration, cleanup: None) -> None:
    """Test Dependabot configuration generation.
    
    Args:
        migration: The migration instance.
        cleanup: Cleanup fixture.
    """
    migration.generate_dependabot_config()
    
    config_path = Path(".github/dependabot.yml")
    assert config_path.exists()
    
    with open(config_path) as f:
        content = yaml.safe_load(f)
    
    assert content["version"] == 2
    assert len(content["updates"]) == 2
    
    pip_update = next(u for u in content["updates"] if u["package-ecosystem"] == "pip")
    assert pip_update["directory"] == "/"
    assert pip_update["schedule"]["interval"] == "weekly"
    assert "dependencies" in pip_update["labels"]
    assert "security" in pip_update["labels"]
    
    actions_update = next(u for u in content["updates"] if u["package-ecosystem"] == "github-actions")
    assert actions_update["directory"] == "/"
    assert actions_update["schedule"]["interval"] == "weekly"
    assert "ci-cd" in actions_update["labels"]
    assert "dependencies" in actions_update["labels"]


def test_migrate_and_rollback(migration: SetupCICDPipelineMigration) -> None:
    """Test full migration and rollback.
    
    Args:
        migration: The migration instance.
    """
    # Test migration
    migration.migrate()
    
    assert Path(".github/workflows/ci.yml").exists()
    assert Path(".github/workflows/cd.yml").exists()
    assert Path(".github/workflows/codeql.yml").exists()
    assert Path(".github/dependabot.yml").exists()
    
    # Test rollback
    migration.rollback()
    
    assert not Path(".github/workflows/ci.yml").exists()
    assert not Path(".github/workflows/cd.yml").exists()
    assert not Path(".github/workflows/codeql.yml").exists()
    assert not Path(".github/dependabot.yml").exists()
    assert not Path(".github/workflows").exists()
    assert not Path(".github").exists()
