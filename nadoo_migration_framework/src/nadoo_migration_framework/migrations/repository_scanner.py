"""Repository scanner for GitHub repositories."""

import os
import json
import subprocess
from typing import List, Dict, Optional
from pathlib import Path
import logging
from ..migration_manager import MigrationManager
from ..functions.project_structure_migrator import ProjectStructure


class RepositoryScanner:
    """Scanner for GitHub repositories."""

    def __init__(self, github_path: str):
        self.github_path = os.path.abspath(github_path)
        self.logger = logging.getLogger(__name__)

    def is_git_repo(self, path: str) -> bool:
        """Check if a directory is a git repository."""
        git_dir = os.path.join(path, '.git')
        return os.path.exists(git_dir) and os.path.isdir(git_dir)

    def is_fork(self, path: str) -> bool:
        """Check if a repository is a fork."""
        try:
            # Run git config command to get remote origin URL
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                cwd=path,
                capture_output=True,
                text=True,
                check=True,
            )
            remote_url = result.stdout.strip()

            # Get repository info using git commands
            result = subprocess.run(
                ['git', 'remote', 'show', 'origin'],
                cwd=path,
                capture_output=True,
                text=True,
                check=True,
            )
            repo_info = result.stdout

            # Check if it's marked as a fork
            return (
                "Fetch URL:" in repo_info
                and "Push  URL:" in repo_info
                and "HEAD branch:" in repo_info
            )

        except subprocess.CalledProcessError:
            return False

    def is_python_project(self, path: str) -> bool:
        """Check if a repository is a Python project."""
        # Check for common Python project indicators
        indicators = ['setup.py', 'pyproject.toml', 'requirements.txt', 'Pipfile', 'poetry.lock']

        return any(os.path.exists(os.path.join(path, ind)) for ind in indicators)

    def scan_repositories(self) -> List[Dict[str, str]]:
        """Scan for non-fork Python repositories."""
        repos = []

        for item in os.listdir(self.github_path):
            repo_path = os.path.join(self.github_path, item)

            if not os.path.isdir(repo_path):
                continue

            if not self.is_git_repo(repo_path):
                continue

            if self.is_fork(repo_path):
                self.logger.info(f"Skipping fork: {item}")
                continue

            if not self.is_python_project(repo_path):
                self.logger.info(f"Skipping non-Python project: {item}")
                continue

            repos.append({'name': item, 'path': repo_path})
            self.logger.info(f"Found Python repository: {item}")

        return repos

    def migrate_repositories(
        self, target_structure: ProjectStructure = ProjectStructure.BRIEFCASE_UNDERSCORE
    ) -> None:
        """Migrate all eligible repositories."""
        repos = self.scan_repositories()

        for repo in repos:
            try:
                self.logger.info(f"\nMigrating repository: {repo['name']}")
                manager = MigrationManager(repo['path'])
                manager.show_migrations()
                manager.apply_migrations(target_structure)

            except Exception as e:
                self.logger.error(f"Error migrating {repo['name']}: {str(e)}")
                continue

    def save_scan_results(self, output_file: str = 'repositories.json') -> None:
        """Save scan results to a JSON file."""
        repos = self.scan_repositories()

        with open(output_file, 'w') as f:
            json.dump(repos, f, indent=2)

        self.logger.info(f"Scan results saved to {output_file}")

    def load_scan_results(self, input_file: str = 'repositories.json') -> List[Dict[str, str]]:
        """Load scan results from a JSON file."""
        if not os.path.exists(input_file):
            return []

        with open(input_file, 'r') as f:
            return json.load(f)
