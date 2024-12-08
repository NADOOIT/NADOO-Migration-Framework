"""Tests to verify CI/CD configuration and requirements."""

import os
import yaml
from pathlib import Path


def test_github_workflows_exist():
    """Test that required GitHub workflow files exist."""
    workflows_dir = Path(__file__).parent.parent / '.github' / 'workflows'
    assert workflows_dir.exists(), "GitHub workflows directory does not exist"

    required_workflows = {
        'ci.yml': [
            'name: CI',
            'on: [push, pull_request]',
            'jobs:',
            'test:',
            'pytest',
            'python-version: ["3.8", "3.9", "3.10", "3.11"]',
        ],
        'cd.yml': ['name: CD', 'on:', 'push:', 'tags:', 'jobs:', 'deploy:', 'pypi'],
        'codeql.yml': ['name: "CodeQL"', 'security', 'analyze', 'python'],
    }

    for workflow, required_content in required_workflows.items():
        workflow_path = workflows_dir / workflow
        assert workflow_path.exists(), f"Required workflow file {workflow} does not exist"

        content = workflow_path.read_text()
        for required_text in required_content:
            assert (
                required_text.lower() in content.lower()
            ), f"Required content '{required_text}' not found in {workflow}"


def test_github_workflow_ci_structure():
    """Test that CI workflow has required jobs and steps."""
    ci_path = Path(__file__).parent.parent / '.github' / 'workflows' / 'ci.yml'
    assert ci_path.exists(), "CI workflow file does not exist"

    with open(ci_path) as f:
        ci_config = yaml.safe_load(f)

    assert 'jobs' in ci_config, "No jobs defined in CI workflow"
    assert 'test' in ci_config['jobs'], "No test job defined in CI workflow"

    test_job = ci_config['jobs']['test']
    required_steps = ['checkout', 'python-setup', 'install-deps', 'run-tests', 'coverage']

    steps = [step.get('name', '').lower().replace(' ', '-') for step in test_job.get('steps', [])]

    for required_step in required_steps:
        assert any(
            required_step in step for step in steps
        ), f"Required step '{required_step}' not found in CI workflow"


def test_github_workflow_cd_structure():
    """Test that CD workflow has required jobs and steps."""
    cd_path = Path(__file__).parent.parent / '.github' / 'workflows' / 'cd.yml'
    assert cd_path.exists(), "CD workflow file does not exist"

    with open(cd_path) as f:
        cd_config = yaml.safe_load(f)

    assert 'jobs' in cd_config, "No jobs defined in CD workflow"
    assert 'deploy' in cd_config['jobs'], "No deploy job defined in CD workflow"

    deploy_job = cd_config['jobs']['deploy']
    required_steps = ['checkout', 'python-setup', 'build', 'publish']

    steps = [step.get('name', '').lower().replace(' ', '-') for step in deploy_job.get('steps', [])]

    for required_step in required_steps:
        assert any(
            required_step in step for step in steps
        ), f"Required step '{required_step}' not found in CD workflow"


def test_github_workflow_codeql_structure():
    """Test that CodeQL workflow has required jobs and steps."""
    codeql_path = Path(__file__).parent.parent / '.github' / 'workflows' / 'codeql.yml'
    assert codeql_path.exists(), "CodeQL workflow file does not exist"

    with open(codeql_path) as f:
        codeql_config = yaml.safe_load(f)

    assert 'jobs' in codeql_config, "No jobs defined in CodeQL workflow"
    assert 'analyze' in codeql_config['jobs'], "No analyze job defined in CodeQL workflow"

    analyze_job = codeql_config['jobs']['analyze']
    required_steps = ['checkout', 'initialize', 'autobuild', 'perform-analysis']

    steps = [
        step.get('name', '').lower().replace(' ', '-') for step in analyze_job.get('steps', [])
    ]

    for required_step in required_steps:
        assert any(
            required_step in step for step in steps
        ), f"Required step '{required_step}' not found in CodeQL workflow"


def test_dependabot_config():
    """Test that Dependabot configuration exists and is properly structured."""
    dependabot_path = Path(__file__).parent.parent / '.github' / 'dependabot.yml'
    assert dependabot_path.exists(), "Dependabot configuration file does not exist"

    with open(dependabot_path) as f:
        dependabot_config = yaml.safe_load(f)

    assert 'version' in dependabot_config, "No version specified in Dependabot config"
    assert 'updates' in dependabot_config, "No updates specified in Dependabot config"

    updates = dependabot_config['updates']
    required_ecosystems = {'pip', 'github-actions'}

    ecosystems = {update.get('package-ecosystem') for update in updates}
    assert required_ecosystems.issubset(
        ecosystems
    ), f"Missing required ecosystems in Dependabot config: {required_ecosystems - ecosystems}"
