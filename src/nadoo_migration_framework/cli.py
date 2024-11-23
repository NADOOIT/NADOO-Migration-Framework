"""Command-line interface for NADOO Migration Framework."""

import click
import os
from pathlib import Path
from typing import Optional, List
import toml
import subprocess
import sys
import json

from .manager import MigrationManager
from .analyzers import NADOOProjectAnalyzer, NonNADOOProjectAnalyzer
from .functions import project_structure
from .version_management import VersionManager, VersionType
from .compatibility_checker import CompatibilityChecker

@click.group()
def cli():
    """NADOO Migration Framework CLI."""
    pass

@cli.command()
@click.argument('project_path', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.')
@click.option('--force', is_flag=True, help='Force migration even if checks fail')
def migrate(project_path: str, force: bool = False):
    """Migrate a project to the latest NADOO Framework version."""
    _run_migration(project_path, force)

def _run_migration(project_path: str, force: bool = False):
    """Implementation of the migration logic."""
    project_dir = Path(project_path).resolve()
    
    # First check if this is a NADOO project
    if project_structure.is_package_root(project_dir) or force:
        click.echo(f"Analyzing project at {project_dir}...")
        
        # Initialize appropriate analyzer
        if _is_nadoo_project(project_dir):
            analyzer = NADOOProjectAnalyzer(project_dir)
            click.echo("Detected NADOO Framework project.")
        else:
            analyzer = NonNADOOProjectAnalyzer(project_dir)
            click.echo("Detected non-NADOO project.")
            
        # Analyze project
        analysis = analyzer.analyze()
        
        # Get required migrations
        migrations = analyzer.get_required_migrations()
        
        if not migrations:
            click.echo("No migrations needed.")
            return
            
        # Initialize migration manager
        manager = MigrationManager(project_dir)
        
        # Apply migrations
        click.echo(f"\nApplying {len(migrations)} migrations:")
        for migration in migrations:
            click.echo(f"  - {migration}")
            
        if click.confirm("\nDo you want to proceed with the migration?"):
            try:
                for migration in migrations:
                    manager.apply_migration(migration)
                click.echo("\nMigration completed successfully!")
            except Exception as e:
                click.echo(f"\nError during migration: {e}", err=True)
    else:
        click.echo("Error: Not a valid Python package. Please run this command in a Python package root directory.", err=True)

@cli.command()
@click.argument('package_name')
@click.option('--dev', is_flag=True, help='Install as development dependency')
def add_package(package_name: str, dev: bool = False):
    """Add a package to the project using NADOO package management."""
    _run_add_package(package_name, dev)

def _run_add_package(package_name: str, dev: bool = False):
    """Implementation of the package addition logic."""
    project_dir = Path.cwd()
    
    if not _is_nadoo_project(project_dir):
        click.echo("Error: This command can only be run in a NADOO Framework project.", err=True)
        return
        
    click.echo(f"Adding package {package_name}...")
    pyproject_path = project_dir / 'pyproject.toml'
    
    try:
        # Read existing pyproject.toml
        with open(pyproject_path) as f:
            data = toml.load(f)
            
        # Add dependency
        if 'tool' in data and 'poetry' in data['tool']:
            poetry = data['tool']['poetry']
            if dev:
                deps = poetry.setdefault('dev-dependencies', {})
            else:
                deps = poetry.setdefault('dependencies', {})
            deps[package_name] = "^*"  # Latest version
            
        # Write updated pyproject.toml
        with open(pyproject_path, 'w') as f:
            toml.dump(data, f)
            
        click.echo(f"Added {package_name} to {'development ' if dev else ''}dependencies.")
        click.echo("Run 'poetry install' to install the package.")
        
    except Exception as e:
        click.echo(f"Error adding package: {e}", err=True)

@cli.command()
@click.argument('project_name')
@click.option('--path', type=click.Path(exists=False), help='Project path')
def init_project(project_name: str, path: Optional[str] = None):
    """Initialize a new NADOO Framework project."""
    _run_init_project(project_name, path)

@cli.command()
@click.option('--bump', type=click.Choice(['major', 'minor', 'patch']), default='patch',
              help='Version increment type')
@click.option('--token', envvar='PYPI_TOKEN', help='PyPI API token')
@click.option('--repository', default='pypi', help='PyPI repository (default: pypi)')
@click.option('--setup', is_flag=True, help='Run PyPI setup process')
def publish(bump: str, token: Optional[str], repository: str, setup: bool):
    """Publish the package to PyPI with version bump.
    
    Uses PyPI API token for authentication. First-time users will be guided through
    the setup process automatically.
    """
    _run_publish(bump, token, repository, setup)

def _run_publish(bump: str, token: Optional[str], repository: str, setup: bool):
    """Implementation of the publish logic."""
    project_dir = Path.cwd()
    pyproject_path = project_dir / 'pyproject.toml'
    
    if not pyproject_path.exists():
        click.echo("Error: No pyproject.toml found. Are you in the correct directory?", err=True)
        return
        
    try:
        # Read current version
        with open(pyproject_path) as f:
            data = toml.load(f)
            
        if 'tool' not in data or 'poetry' not in data['tool']:
            click.echo("Error: Not a Poetry project", err=True)
            return
            
        # Check if token is configured
        result = subprocess.run(['poetry', 'config', 'pypi-token.pypi'], 
                              capture_output=True, text=True)
        has_token = result.stdout.strip() != ''
        
        # Run setup if requested or if no token is configured
        if setup or not has_token:
            if not _setup_pypi_token():
                return
                
        current_version = data['tool']['poetry']['version']
        
        # Bump version
        click.echo(f"Current version: {current_version}")
        result = subprocess.run(['poetry', 'version', bump], capture_output=True, text=True)
        if result.returncode != 0:
            click.echo(f"Error bumping version: {result.stderr}", err=True)
            return
            
        new_version = result.stdout.strip().split(' ')[-1]
        click.echo(f"New version: {new_version}")
        
        # Build package
        click.echo("\nBuilding package...")
        result = subprocess.run(['poetry', 'build'], capture_output=True, text=True)
        if result.returncode != 0:
            click.echo(f"Error building package: {result.stderr}", err=True)
            return
            
        # Configure token if provided via command line or env var
        if token:
            config_cmd = ['poetry', 'config', 'pypi-token.pypi', token]
            subprocess.run(config_cmd, capture_output=True)
            
        # Publish to PyPI
        click.echo("\nPublishing to PyPI...")
        publish_cmd = ['poetry', 'publish']
        if repository != 'pypi':
            publish_cmd.extend(['--repository', repository])
            
        result = subprocess.run(publish_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            click.echo(f"Error publishing package: {result.stderr}", err=True)
            return
            
        click.echo(f"\nSuccessfully published version {new_version} to PyPI!")
        click.echo(f"You can now install it with: pip install nadoo-migration-framework=={new_version}")
        
    except Exception as e:
        click.echo(f"Error during publishing: {e}", err=True)

def _setup_pypi_token():
    """Guide user through PyPI token setup process."""
    click.echo("\nWelcome to the PyPI setup process!")
    click.echo("This is a one-time setup to configure your PyPI publishing credentials.")
    
    # Check if user wants to proceed
    if not click.confirm("\nWould you like to set up PyPI publishing now?"):
        click.echo("You can run this setup later with: nadoo publish --setup")
        return False
        
    click.echo("\nGreat! Let's get you set up with PyPI.")
    click.echo("\nStep 1: Create a PyPI Account")
    click.echo("1. Visit: https://pypi.org/account/register/")
    click.echo("2. Click 'Register' and create your account")
    click.echo("3. Verify your email address")
    
    if not click.confirm("\nHave you created and verified your PyPI account?"):
        click.echo("No problem! You can run this setup later with: nadoo publish --setup")
        return False
        
    click.echo("\nStep 2: Create an API token")
    click.echo("1. Log in to PyPI at https://pypi.org/account/login/")
    click.echo("2. Go to https://pypi.org/manage/account/token/")
    click.echo("3. Click 'Add API token'")
    click.echo("4. Set a token name (e.g., 'nadoo-migration-framework')")
    click.echo("5. Choose scope: 'Entire account (all projects)'")
    click.echo("6. Click 'Create token' and COPY the token immediately")
    click.echo("\nWARNING: The token will only be shown ONCE!")
    click.echo("Make sure to copy it before closing the page.")
    click.echo("\nNOTE: The token will be stored securely in Poetry's configuration.")
    click.echo("It will NOT be added to version control.")
    
    if not click.confirm("\nDo you have your API token copied and ready?"):
        click.echo("No problem! You can run this setup later with: nadoo publish --setup")
        return False
        
    # Get token from user
    token = click.prompt("\nPlease paste your API token", hide_input=True)
    
    if not token:
        click.echo("No token provided. You can run this setup later with: nadoo publish --setup")
        return False
        
    # Configure token in Poetry
    try:
        # Store token in Poetry's config (not in version control)
        subprocess.run(['poetry', 'config', 'pypi-token.pypi', token], 
                      capture_output=True, check=True)
        click.echo("\nSuccess! Your PyPI token has been securely stored.")
        
        # Add .pypirc to .gitignore if not already there
        gitignore_path = Path.cwd() / '.gitignore'
        if not gitignore_path.exists():
            with open(gitignore_path, 'w') as f:
                f.write("# PyPI configuration\n.pypirc\n")
        else:
            with open(gitignore_path, 'r') as f:
                content = f.read()
            if '.pypirc' not in content:
                with open(gitignore_path, 'a') as f:
                    f.write("\n# PyPI configuration\n.pypirc\n")
        
        return True
    except subprocess.CalledProcessError as e:
        click.echo(f"\nError configuring token: {e}")
        return False

def _run_init_project(project_name: str, path: Optional[str] = None):
    """Implementation of the project initialization logic."""
    if path:
        project_dir = Path(path) / project_name
    else:
        project_dir = Path.cwd() / project_name
        
    if project_dir.exists():
        click.echo(f"Error: Directory {project_dir} already exists.", err=True)
        return
        
    try:
        # Create project structure
        project_dir.mkdir(parents=True)
        (project_dir / 'src' / project_name).mkdir(parents=True)
        (project_dir / 'tests').mkdir()
        
        # Create pyproject.toml
        pyproject = {
            'build-system': {
                'requires': ['poetry-core>=1.0.0'],
                'build-backend': 'poetry.core.masonry.api'
            },
            'tool': {
                'poetry': {
                    'name': project_name,
                    'version': '0.1.0',
                    'description': '',
                    'authors': [],
                    'dependencies': {
                        'python': '^3.8',
                        'nadoo-framework': '^*'
                    },
                    'dev-dependencies': {
                        'pytest': '^7.0.0'
                    }
                }
            }
        }
        
        with open(project_dir / 'pyproject.toml', 'w') as f:
            toml.dump(pyproject, f)
            
        # Create README.md
        with open(project_dir / 'README.md', 'w') as f:
            f.write(f"# {project_name}\n\nA NADOO Framework project.\n")
            
        # Create main module
        with open(project_dir / 'src' / project_name / '__init__.py', 'w') as f:
            f.write('"""Main module for {project_name}."""\n\n__version__ = "0.1.0"\n')
            
        click.echo(f"Created new NADOO Framework project in {project_dir}")
        click.echo("\nNext steps:")
        click.echo("1. cd " + str(project_dir))
        click.echo("2. poetry install")
        click.echo("3. git init")
        
    except Exception as e:
        click.echo(f"Error creating project: {e}", err=True)
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir)
    
def _is_nadoo_project(project_dir: Path) -> bool:
    """Check if the project is a NADOO Framework project."""
    pyproject_path = project_dir / 'pyproject.toml'
    if not pyproject_path.exists():
        return False
        
    try:
        with open(pyproject_path) as f:
            data = toml.load(f)
            
        # Check for NADOO Framework dependency or configuration
        if 'tool' in data and 'poetry' in data['tool']:
            deps = data['tool']['poetry'].get('dependencies', {})
            return 'nadoo-framework' in deps
            
        if 'project' in data:
            deps = data['project'].get('dependencies', [])
            return any('nadoo-framework' in dep for dep in deps)
            
    except Exception:
        pass
        
    return False

@cli.command()
@click.option('--type', 'version_type', type=click.Choice(['major', 'minor', 'patch']), 
              default='patch', help='Version increment type')
@click.option('--description', '-d', help='Release description', required=True)
@click.option('--changes', '-c', multiple=True, help='List of changes in this release', required=True)
@click.option('--token', envvar='PYPI_TOKEN', help='PyPI API token')
@click.option('--repository', default='pypi', help='PyPI repository (default: pypi)')
@click.option('--setup', is_flag=True, help='Run PyPI setup process')
@click.option('--no-publish', is_flag=True, help='Create release without publishing to PyPI')
def release(version_type: str, description: str, changes: List[str], 
           token: Optional[str], repository: str, setup: bool, no_publish: bool):
    """Create a new release and optionally publish to PyPI.
    
    Example:
        nadoo release -d "Bug fixes and improvements" -c "Fixed issue #123" -c "Added feature XYZ"
    """
    _run_release(version_type, description, list(changes), token, repository, setup, no_publish)

def _run_release(version_type: str, description: str, changes: List[str],
                token: Optional[str], repository: str, setup: bool, no_publish: bool):
    """Implementation of the release command."""
    project_dir = Path.cwd()
    
    # Initialize version manager
    version_manager = VersionManager(project_dir)
    
    try:
        # Create new release
        release = version_manager.add_release(
            version_type=VersionType(version_type),
            changes=changes,
            description=description
        )
        
        click.echo(f"\nCreated release {release.version}")
        click.echo(f"Description: {release.description}")
        click.echo("Changes:")
        for change in release.changes:
            click.echo(f"  - {change}")
            
        # Generate and update changelog
        changelog = version_manager.get_changelog()
        with open(project_dir / "CHANGELOG.md", "w") as f:
            f.write(changelog)
            
        click.echo("\nUpdated CHANGELOG.md")
        
        if not no_publish:
            # Run publish command
            _run_publish(version_type, token, repository, setup)
            
    except Exception as e:
        click.echo(f"Error creating release: {e}", err=True)

@cli.command()
@click.option('--json', is_flag=True, help='Output results in JSON format')
@click.option('--markdown', is_flag=True, help='Output results in Markdown format')
@click.option('--project-dir', type=click.Path(exists=True, file_okay=False, dir_okay=True),
              default='.', help='Project directory to check')
def check(json: bool, markdown: bool, project_dir: str):
    """Check project compatibility with NADOO Framework."""
    checker = CompatibilityChecker(Path(project_dir))
    results = checker.check_compatibility()
    
    if json:
        click.echo(json.dumps(results.to_dict(), indent=2))
    elif markdown:
        click.echo(results.to_markdown())
    else:
        # Pretty print results
        click.echo(f"\nProject: {results.project_path}")
        click.echo(f"Type: {'NADOO' if results.is_nadoo_project else 'Non-NADOO'} Project")
        click.echo(f"Current Version: {results.current_version or 'Not using NADOO Framework'}")
        click.echo(f"Latest Version: {results.latest_version}")
        click.echo(f"Needs Migration: {'Yes' if results.needs_migration else 'No'}\n")
        
        if results.changes:
            click.echo("Required Changes:")
            for change in results.changes:
                click.echo(f"  - {change}")

if __name__ == '__main__':
    cli()
