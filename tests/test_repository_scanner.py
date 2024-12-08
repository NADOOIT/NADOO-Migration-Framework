"""Tests for the repository scanner."""

import os
import json
import shutil
import pytest
from pathlib import Path
from nadoo_migration_framework.migrations.repository_scanner import RepositoryScanner
from nadoo_migration_framework.functions.project_structure_migrator import ProjectStructure


def create_test_repo(
    tmp_path: Path, name: str, is_python: bool = True, is_fork: bool = False
) -> Path:
    """Create a test repository."""
    repo_path = tmp_path / name
    repo_path.mkdir()

    # Create .git directory
    git_dir = repo_path / '.git'
    git_dir.mkdir()

    if is_python:
        # Create Python project indicators
        (repo_path / 'setup.py').touch()
        with open(repo_path / 'requirements.txt', 'w') as f:
            f.write('pytest\n')

    if is_fork:
        # Create git config to simulate a fork
        config_dir = git_dir / 'config'
        with open(config_dir, 'w') as f:
            f.write(
                '''[remote "origin"]
    url = https://github.com/original/repo.git
    fetch = +refs/heads/*:refs/remotes/origin/*
[branch "main"]
    remote = origin
    merge = refs/heads/main'''
            )

    return repo_path


def test_is_git_repo(tmp_path):
    """Test git repository detection."""
    # Create a git repo
    repo_path = create_test_repo(tmp_path, 'test-repo')
    scanner = RepositoryScanner(str(tmp_path))

    assert scanner.is_git_repo(str(repo_path)) == True

    # Test non-git directory
    non_git_path = tmp_path / 'non-git'
    non_git_path.mkdir()
    assert scanner.is_git_repo(str(non_git_path)) == False


def test_is_python_project(tmp_path):
    """Test Python project detection."""
    # Create Python project
    repo_path = create_test_repo(tmp_path, 'python-repo', is_python=True)
    scanner = RepositoryScanner(str(tmp_path))

    assert scanner.is_python_project(str(repo_path)) == True

    # Test non-Python project
    non_python_path = create_test_repo(tmp_path, 'non-python', is_python=False)
    assert scanner.is_python_project(str(non_python_path)) == False


def test_scan_repositories(tmp_path):
    """Test repository scanning."""
    # Create various test repositories
    python_repo = create_test_repo(tmp_path, 'python-repo')
    python_fork = create_test_repo(tmp_path, 'python-fork', is_fork=True)
    non_python = create_test_repo(tmp_path, 'non-python', is_python=False)
    regular_dir = tmp_path / 'regular-dir'
    regular_dir.mkdir()

    scanner = RepositoryScanner(str(tmp_path))
    repos = scanner.scan_repositories()

    # Should only find the non-fork Python repository
    assert len(repos) == 1
    assert repos[0]['name'] == 'python-repo'
    assert repos[0]['path'] == str(python_repo)


def test_save_load_results(tmp_path):
    """Test saving and loading scan results."""
    # Create test repository
    repo_path = create_test_repo(tmp_path, 'test-repo')
    scanner = RepositoryScanner(str(tmp_path))

    # Save scan results
    output_file = tmp_path / 'repos.json'
    scanner.save_scan_results(str(output_file))

    # Load scan results
    loaded_repos = scanner.load_scan_results(str(output_file))

    assert len(loaded_repos) == 1
    assert loaded_repos[0]['name'] == 'test-repo'
    assert loaded_repos[0]['path'] == str(repo_path)


def test_migrate_repositories(tmp_path):
    """Test repository migration."""
    # Create test repositories
    repo1 = create_test_repo(tmp_path, 'repo1')
    repo2 = create_test_repo(tmp_path, 'repo2')

    # Create src directories with Python files
    for repo in [repo1, repo2]:
        src_dir = repo / 'src'
        src_dir.mkdir()
        with open(src_dir / 'test.py', 'w') as f:
            f.write('from src.module import function\n')

    scanner = RepositoryScanner(str(tmp_path))
    scanner.migrate_repositories(ProjectStructure.BRIEFCASE_UNDERSCORE)

    # Check that both repositories were migrated
    for repo in [repo1, repo2]:
        assert (repo / repo.name / 'src' / repo.name).exists()
        assert (repo / 'src.bak').exists()
