"""Migration to set up CI/CD pipeline configuration."""
import os
import yaml
from pathlib import Path
from typing import Dict, Any

from ..migration_base import MigrationBase


class SetupCICDPipelineMigration(MigrationBase):
    """Migration to set up CI/CD pipeline configuration."""

    def __init__(self):
        """Initialize the migration."""
        super().__init__()
        self.migration_id = "setup_cicd_pipeline"
        self.description = "Sets up CI/CD pipeline configuration files"

    def generate_workflow_file(self, filename: str, content: Dict[str, Any]) -> None:
        """Generate a workflow file with the given content.

        Args:
            filename: Name of the workflow file.
            content: Content of the workflow file.
        """
        workflows_dir = Path(".github/workflows")
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        with open(workflows_dir / filename, "w") as f:
            yaml.safe_dump(content, f, sort_keys=False)

    def generate_ci_workflow(self) -> None:
        """Generate the CI workflow file."""
        ci_content = {
            "name": "CI",
            "on": ["push", "pull_request"],
            "jobs": {
                "test": {
                    "runs-on": "ubuntu-latest",
                    "strategy": {
                        "matrix": {
                            "python-version": ["3.8", "3.9", "3.10", "3.11"]
                        }
                    },
                    "steps": [
                        {
                            "name": "Checkout",
                            "uses": "actions/checkout@v3"
                        },
                        {
                            "name": "Python Setup",
                            "uses": "actions/setup-python@v4",
                            "with": {
                                "python-version": "${{ matrix.python-version }}"
                            }
                        },
                        {
                            "name": "Install Deps",
                            "run": "\n".join([
                                "python -m pip install --upgrade pip",
                                "pip install poetry",
                                "poetry install"
                            ])
                        },
                        {
                            "name": "Run Tests",
                            "run": "\n".join([
                                "poetry run pytest tests/ --cov=src/ --cov-report=xml"
                            ])
                        },
                        {
                            "name": "Coverage",
                            "uses": "codecov/codecov-action@v3",
                            "with": {
                                "file": "./coverage.xml",
                                "fail_ci_if_error": True
                            }
                        }
                    ]
                }
            }
        }
        self.generate_workflow_file("ci.yml", ci_content)

    def generate_cd_workflow(self) -> None:
        """Generate the CD workflow file."""
        cd_content = {
            "name": "CD",
            "on": {
                "push": {
                    "tags": ["v*"]
                }
            },
            "jobs": {
                "deploy": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "Checkout",
                            "uses": "actions/checkout@v3"
                        },
                        {
                            "name": "Python Setup",
                            "uses": "actions/setup-python@v4",
                            "with": {
                                "python-version": "3.11"
                            }
                        },
                        {
                            "name": "Build",
                            "run": "poetry build"
                        },
                        {
                            "name": "Publish",
                            "env": {
                                "POETRY_PYPI_TOKEN_PYPI": "${{ secrets.PYPI_TOKEN }}"
                            },
                            "run": "poetry publish"
                        }
                    ]
                }
            }
        }
        self.generate_workflow_file("cd.yml", cd_content)

    def generate_codeql_workflow(self) -> None:
        """Generate the CodeQL workflow file."""
        codeql_content = {
            "name": "CodeQL",
            "on": {
                "push": {
                    "branches": ["main"]
                },
                "pull_request": {
                    "branches": ["main"]
                },
                "schedule": [
                    {"cron": "30 1 * * 0"}
                ]
            },
            "jobs": {
                "analyze": {
                    "name": "Analyze",
                    "runs-on": "ubuntu-latest",
                    "permissions": {
                        "actions": "read",
                        "contents": "read",
                        "security-events": "write"
                    },
                    "strategy": {
                        "fail-fast": False,
                        "matrix": {
                            "language": ["python"]
                        }
                    },
                    "steps": [
                        {
                            "name": "Checkout",
                            "uses": "actions/checkout@v3"
                        },
                        {
                            "name": "Initialize",
                            "uses": "github/codeql-action/init@v2",
                            "with": {
                                "languages": "${{ matrix.language }}"
                            }
                        },
                        {
                            "name": "Autobuild",
                            "uses": "github/codeql-action/autobuild@v2"
                        },
                        {
                            "name": "Perform Analysis",
                            "uses": "github/codeql-action/analyze@v2",
                            "with": {
                                "category": "/language:${{matrix.language}}"
                            }
                        }
                    ]
                }
            }
        }
        self.generate_workflow_file("codeql.yml", codeql_content)

    def generate_dependabot_config(self) -> None:
        """Generate the Dependabot configuration file."""
        dependabot_content = {
            "version": 2,
            "updates": [
                {
                    "package-ecosystem": "pip",
                    "directory": "/",
                    "schedule": {
                        "interval": "weekly"
                    },
                    "allow": [
                        {"dependency-type": "direct"}
                    ],
                    "commit-message": {
                        "prefix": "deps"
                    },
                    "labels": [
                        "dependencies",
                        "security"
                    ],
                    "open-pull-requests-limit": 10
                },
                {
                    "package-ecosystem": "github-actions",
                    "directory": "/",
                    "schedule": {
                        "interval": "weekly"
                    },
                    "commit-message": {
                        "prefix": "ci"
                    },
                    "labels": [
                        "ci-cd",
                        "dependencies"
                    ],
                    "open-pull-requests-limit": 10
                }
            ]
        }
        dependabot_dir = Path(".github")
        dependabot_dir.mkdir(exist_ok=True)
        
        with open(dependabot_dir / "dependabot.yml", "w") as f:
            yaml.safe_dump(dependabot_content, f, sort_keys=False)

    def migrate(self) -> None:
        """Perform the migration."""
        self.generate_ci_workflow()
        self.generate_cd_workflow()
        self.generate_codeql_workflow()
        self.generate_dependabot_config()

    def rollback(self) -> None:
        """Rollback the migration."""
        workflows_dir = Path(".github/workflows")
        if workflows_dir.exists():
            for workflow in ["ci.yml", "cd.yml", "codeql.yml"]:
                workflow_path = workflows_dir / workflow
                if workflow_path.exists():
                    workflow_path.unlink()
            
            if not any(workflows_dir.iterdir()):
                workflows_dir.rmdir()
        
        dependabot_file = Path(".github/dependabot.yml")
        if dependabot_file.exists():
            dependabot_file.unlink()
            
        github_dir = Path(".github")
        if github_dir.exists() and not any(github_dir.iterdir()):
            github_dir.rmdir()
