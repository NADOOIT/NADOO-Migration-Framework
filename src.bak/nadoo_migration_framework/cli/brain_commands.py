"""CLI commands for BRAIN migrations."""

import click
from pathlib import Path
from typing import Optional

from ..frameworks.brain_migration import BrainMigration
from ..migration_manager import MigrationManager

@click.group()
def brain():
    """Commands for BRAIN migrations."""
    pass

@brain.command()
@click.argument('brain_project', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--dry-run', is_flag=True, help='Check compatibility without performing migration')
def migrate_to_brain(brain_project: str, dry_run: bool):
    """Migrate functions from NADOO to BRAIN.
    
    BRAIN_PROJECT: Path to BRAIN project directory
    """
    brain_dir = Path(brain_project).resolve()
    project_dir = Path.cwd()
    
    # Initialize migration
    migration = BrainMigration()
    migration.set_project_dir(project_dir)
    migration.set_brain_project_dir(brain_dir)
    
    # Analyze compatibility
    compatible, incompatible = migration.analyze_function_compatibility()
    
    if not compatible:
        click.echo("No compatible functions found for migration.")
        if incompatible:
            click.echo("\nIncompatible functions that need manual attention:")
            for func in incompatible:
                click.echo(f"  - {func}")
        return
    
    click.echo("Found compatible functions:")
    for func in compatible:
        click.echo(f"  - {func}")
        
    if incompatible:
        click.echo("\nIncompatible functions that need manual attention:")
        for func in incompatible:
            click.echo(f"  - {func}")
    
    if dry_run:
        click.echo("\nDry run completed. No changes made.")
        return
        
    if click.confirm("\nDo you want to proceed with the migration?"):
        success = migration.migrate_to_brain()
        if success:
            click.echo("Migration to BRAIN completed successfully!")
        else:
            click.echo("Migration failed. Please check the logs for details.")

@brain.command()
@click.argument('brain_project', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--dry-run', is_flag=True, help='Check compatibility without performing migration')
def migrate_from_brain(brain_project: str, dry_run: bool):
    """Migrate functions from BRAIN to NADOO.
    
    BRAIN_PROJECT: Path to BRAIN project directory
    """
    brain_dir = Path(brain_project).resolve()
    project_dir = Path.cwd()
    
    # Initialize migration
    migration = BrainMigration()
    migration.set_project_dir(project_dir)
    migration.set_brain_project_dir(brain_dir)
    
    # Analyze compatibility
    compatible, incompatible = migration.analyze_function_compatibility()
    
    if not compatible:
        click.echo("No compatible functions found for migration.")
        if incompatible:
            click.echo("\nIncompatible functions that need manual attention:")
            for func in incompatible:
                click.echo(f"  - {func}")
        return
    
    click.echo("Found compatible functions:")
    for func in compatible:
        click.echo(f"  - {func}")
        
    if incompatible:
        click.echo("\nIncompatible functions that need manual attention:")
        for func in incompatible:
            click.echo(f"  - {func}")
    
    if dry_run:
        click.echo("\nDry run completed. No changes made.")
        return
        
    if click.confirm("\nDo you want to proceed with the migration?"):
        success = migration.migrate_from_brain()
        if success:
            click.echo("Migration from BRAIN completed successfully!")
        else:
            click.echo("Migration failed. Please check the logs for details.")

@brain.command()
@click.argument('brain_project', type=click.Path(exists=True, file_okay=False, dir_okay=True))
def analyze(brain_project: str):
    """Analyze compatibility between NADOO and BRAIN projects.
    
    BRAIN_PROJECT: Path to BRAIN project directory
    """
    brain_dir = Path(brain_project).resolve()
    project_dir = Path.cwd()
    
    # Initialize migration
    migration = BrainMigration()
    migration.set_project_dir(project_dir)
    migration.set_brain_project_dir(brain_dir)
    
    # Analyze compatibility
    compatible, incompatible = migration.analyze_function_compatibility()
    
    click.echo("Compatibility Analysis Results:")
    click.echo("-" * 30)
    
    if compatible:
        click.echo("\nCompatible functions:")
        for func in compatible:
            click.echo(f"  ✓ {func}")
    else:
        click.echo("\nNo compatible functions found.")
        
    if incompatible:
        click.echo("\nIncompatible functions:")
        for func in incompatible:
            click.echo(f"  ✗ {func}")
            
    click.echo("\nSummary:")
    click.echo(f"  Compatible: {len(compatible)}")
    click.echo(f"  Incompatible: {len(incompatible)}")
    click.echo(f"  Total: {len(compatible) + len(incompatible)}")
