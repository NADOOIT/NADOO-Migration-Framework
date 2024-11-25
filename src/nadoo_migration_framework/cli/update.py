"""Update command for NADOO Migration Framework."""

import click
import toml
from pathlib import Path
import subprocess
import sys
from typing import Literal, Optional
import os
from .token_dialog import get_token_via_dialog

VersionType = Literal["major", "minor", "patch"]

def bump_version(version: str, bump_type: VersionType) -> str:
    """Bump the version number according to semver."""
    major, minor, patch = map(int, version.split('.'))
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"

def update_pyproject_toml(bump_type: VersionType) -> bool:
    """Update version in pyproject.toml."""
    try:
        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            click.echo("Error: pyproject.toml not found", err=True)
            return False

        # Read current config
        with open(pyproject_path) as f:
            config = toml.load(f)

        current_version = config["tool"]["poetry"]["version"]
        new_version = bump_version(current_version, bump_type)

        # Update versions
        config["tool"]["poetry"]["version"] = new_version
        if "tool" in config and "nadoo" in config["tool"]:
            config["tool"]["nadoo"]["version"] = new_version

        # Write back
        with open(pyproject_path, "w") as f:
            toml.dump(config, f)

        click.echo(f"Updated version from {current_version} to {new_version}")
        return True

    except Exception as e:
        click.echo(f"Error updating pyproject.toml: {str(e)}", err=True)
        return False

def run_poetry_command(command: list[str], token: Optional[str] = None) -> bool:
    """Run a poetry command."""
    try:
        env = os.environ.copy()
        if token:
            env["POETRY_PYPI_TOKEN_PYPI"] = token

        result = subprocess.run(["poetry"] + command, check=True, capture_output=True, text=True, env=env)
        click.echo(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        click.echo(f"Error running poetry command: {e.stderr}", err=True)
        return False

def get_pypi_token() -> Optional[str]:
    """Get PyPI token from environment or Poetry config."""
    # First try environment variable
    token = os.environ.get("PYPI_TOKEN")
    if token:
        return token

    # Then try Poetry config
    try:
        result = subprocess.run(
            ["poetry", "config", "pypi-token.pypi"],
            check=True,
            capture_output=True,
            text=True
        )
        token = result.stdout.strip()
        if token:
            return token
    except:
        pass

    # Finally, try GUI dialog
    return get_token_via_dialog()

@click.command()
@click.option('--bump', type=click.Choice(['major', 'minor', 'patch']), required=True,
              help='Version bump type (major, minor, or patch)')
@click.option('--token', envvar='PYPI_TOKEN', help='PyPI API token')
def update(bump: str, token: Optional[str]):
    """Update package version and publish to PyPI."""
    click.echo("Starting update process...")

    # Get PyPI token
    token = token or get_pypi_token()
    if not token:
        click.echo("Error: PyPI token not provided", err=True)
        sys.exit(1)

    # Update version in pyproject.toml
    if not update_pyproject_toml(bump):
        sys.exit(1)

    # Build package
    click.echo("\nBuilding package...")
    if not run_poetry_command(["build"]):
        sys.exit(1)

    # Run poetry publish
    click.echo("\nPublishing to PyPI...")
    if not run_poetry_command(["publish"], token=token):
        sys.exit(1)

    click.echo("\nUpdate completed successfully!")

if __name__ == '__main__':
    update()
