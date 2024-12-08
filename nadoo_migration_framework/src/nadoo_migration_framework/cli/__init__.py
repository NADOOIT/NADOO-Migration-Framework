"""Command-line interface for NADOO Migration Framework."""

import click
import os
from pathlib import Path
from typing import Optional, List, Dict
import toml
import subprocess
import sys
import json
from ..manager import MigrationManager
from ..analyzers import NADOOProjectAnalyzer, NonNADOOProjectAnalyzer
from ..functions import project_structure
from ..version_management import VersionManager, VersionType
from ..compatibility import CompatibilityChecker, CompatibilityCheck, CompatibilityIssue
from ..migrations import MigrationEngine
from ..gui.app import run_migration_gui
from .update import update
from .brain_commands import brain
from ..fixes import FixManager, FixResult
from ..voice_commands import VoiceCommandManager


@click.group()
def cli():
    """NADOO Migration Framework CLI."""
    pass


cli.add_command(update, name="update")
cli.add_command(brain, name="brain")


@cli.command()
@click.argument(
    'project_path', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.'
)
@click.option('--auto', is_flag=True, help='Automatically execute migrations without confirmation')
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
@click.option('--backup/--no-backup', default=True, help='Create a backup before migration')
@click.option('--gui', is_flag=True, help='Use GUI interface for migration')
@click.option('--strict', is_flag=True, help='Treat warnings as errors')
@click.option('--skip-style', is_flag=True, help='Skip code style checks')
@click.option(
    '--report-format',
    type=click.Choice(['text', 'markdown', 'json']),
    default='text',
    help='Output format for compatibility report',
)
@click.option('--output', type=click.Path(), help='Save report to file instead of stdout')
def migrate(
    project_path: str,
    auto: bool,
    dry_run: bool,
    backup: bool,
    gui: bool,
    strict: bool,
    skip_style: bool,
    report_format: str,
    output: Optional[str],
):
    """Migrate a project to NADOO Framework standards."""
    if gui:
        run_migration_gui(Path(project_path))
        return

    try:
        engine = MigrationEngine(Path(project_path))

        # First check what migrations are needed
        needed_migrations = engine.check_migrations()
        compatibility_check = engine.compatibility_checker.check_compatibility()

        # Generate report
        report = generate_compatibility_report(compatibility_check, report_format)

        # Handle output
        if output:
            with open(output, 'w') as f:
                f.write(report)
            click.echo(f"Compatibility report saved to {output}")
        else:
            click.echo(report)

        # Check for blocking issues
        blocking_issues = [
            issue
            for issue in compatibility_check.issues
            if issue.severity == 'error' or (strict and issue.severity == 'warning')
        ]

        if blocking_issues and not auto:
            click.echo("\nBlocking issues found:")
            for issue in blocking_issues:
                click.echo(f"  - [{issue.severity.upper()}] {issue.message}")
                if issue.fix_suggestion:
                    click.echo(f"    Fix: {issue.fix_suggestion}")
            if not click.confirm("\nDo you want to proceed despite these issues?"):
                click.echo("Migration cancelled.")
                return

        if not needed_migrations:
            click.echo("No migrations needed. Project is up to date.")
            return

        # Plan the migrations
        plan = engine.plan_migration()
        plan.backup_needed = backup

        if dry_run:
            click.echo("\nMigration Plan:")
            for step in plan.steps:
                click.echo(f"  - {step.description}")
            click.echo(f"\nEstimated time: {plan.estimated_time} seconds")
            return

        if not auto:
            click.echo("\nPlanned Changes:")
            for step in plan.steps:
                click.echo(f"  - {step.description}")
            click.echo(f"\nEstimated time: {plan.estimated_time} seconds")

            if not click.confirm("\nDo you want to proceed with these changes?"):
                click.echo("Migration cancelled.")
                return

        if engine.execute_plan(plan):
            click.echo("\nMigration completed successfully!")

            # Run final compatibility check
            final_check = engine.compatibility_checker.check_compatibility()
            if final_check.issues:
                click.echo("\nRemaining compatibility issues:")
                for issue in final_check.issues:
                    click.echo(f"  - [{issue.severity.upper()}] {issue.message}")
                    if issue.fix_suggestion:
                        click.echo(f"    Fix: {issue.fix_suggestion}")
        else:
            click.echo("\nMigration failed. Check the error messages above.")
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error during migration: {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument(
    'project_path', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.'
)
@click.option('--gui', is_flag=True, help='Use GUI interface for checking')
@click.option('--strict', is_flag=True, help='Treat warnings as errors')
@click.option('--skip-style', is_flag=True, help='Skip code style checks')
@click.option(
    '--report-format',
    type=click.Choice(['text', 'markdown', 'json']),
    default='text',
    help='Output format for compatibility report',
)
@click.option('--output', type=click.Path(), help='Save report to file instead of stdout')
@click.option(
    '--categories',
    type=str,
    help='Comma-separated list of categories to check (e.g., "python,dependencies")',
)
def check(
    project_path: str,
    gui: bool,
    strict: bool,
    skip_style: bool,
    report_format: str,
    output: Optional[str],
    categories: Optional[str],
):
    """Check project compatibility with NADOO Framework."""
    if gui:
        run_migration_gui(Path(project_path), check_only=True)
        return

    try:
        engine = MigrationEngine(Path(project_path))

        # Filter categories if specified
        if categories:
            selected_categories = [cat.strip().lower() for cat in categories.split(',')]
            engine.compatibility_checker.enabled_categories = selected_categories

        if skip_style:
            engine.compatibility_checker.skip_style_check = True

        # Run compatibility check
        compatibility_check = engine.compatibility_checker.check_compatibility()

        # Generate report
        report = generate_compatibility_report(compatibility_check, report_format)

        # Handle output
        if output:
            with open(output, 'w') as f:
                f.write(report)
            click.echo(f"Compatibility report saved to {output}")
        else:
            click.echo(report)

        # Exit with error if there are blocking issues
        blocking_issues = [
            issue
            for issue in compatibility_check.issues
            if issue.severity == 'error' or (strict and issue.severity == 'warning')
        ]
        if blocking_issues:
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error checking compatibility: {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument(
    'project_path', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.'
)
@click.option('--auto', is_flag=True, help='Automatically fix issues without confirmation')
@click.option(
    '--categories',
    type=str,
    help='Comma-separated list of categories to fix (e.g., "code-style,dependencies")',
)
@click.option(
    '--report-format',
    type=click.Choice(['text', 'markdown', 'json']),
    default='text',
    help='Output format for fix report',
)
@click.option('--output', type=click.Path(), help='Save report to file instead of stdout')
def fix(
    project_path: str,
    auto: bool,
    categories: Optional[str],
    report_format: str,
    output: Optional[str],
):
    """Automatically fix compatibility issues."""
    try:
        engine = MigrationEngine(Path(project_path))
        fix_manager = FixManager(Path(project_path))

        # Run compatibility check
        compatibility_check = engine.compatibility_checker.check_compatibility()

        # Filter issues by category if specified
        issues = compatibility_check.issues
        if categories:
            selected_categories = {cat.strip().lower() for cat in categories.split(',')}
            issues = [issue for issue in issues if issue.category.lower() in selected_categories]

        if not issues:
            click.echo("No issues to fix.")
            return

        # Show issues that will be fixed
        click.echo("\nIssues to fix:")
        for issue in issues:
            click.echo(f"  - [{issue.severity.upper()}] {issue.message}")
            if issue.fix_suggestion:
                click.echo(f"    Fix: {issue.fix_suggestion}")

        if not auto and not click.confirm("\nDo you want to proceed with these fixes?"):
            click.echo("Fix operation cancelled.")
            return

        # Apply fixes
        results = fix_manager.apply_fixes(issues)

        # Generate report
        report = generate_fix_report(results, report_format)

        # Handle output
        if output:
            with open(output, 'w') as f:
                f.write(report)
            click.echo(f"Fix report saved to {output}")
        else:
            click.echo("\nFix Results:")
            click.echo(report)

    except Exception as e:
        click.echo(f"Error during fix operation: {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument(
    'project_path', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.'
)
def voice(project_path: str):
    """Start voice command interface."""
    try:
        engine = MigrationEngine(Path(project_path))
        voice_manager = VoiceCommandManager()

        # Add commands
        voice_manager.add_command("check compatibility", lambda: check(project_path))
        voice_manager.add_command("fix issues", lambda: fix(project_path, True, None, "text", None))
        voice_manager.add_command("show status", lambda: status(project_path))
        voice_manager.add_command("run migration", lambda: migrate(project_path))
        voice_manager.add_command("stop listening", voice_manager.stop_listening)

        # Start listening
        print("\nVoice Command Interface")
        print("=====================")
        print("Available commands:")
        print("  - Check compatibility")
        print("  - Fix issues")
        print("  - Show status")
        print("  - Run migration")
        print("  - Stop listening")
        print("\nListening for commands... (say 'stop listening' to exit)")

        voice_manager.speak("Voice command interface ready")
        voice_manager.start_listening()

        # Keep the main thread alive
        try:
            while voice_manager.is_listening:
                click.pause(1.0)
        except KeyboardInterrupt:
            voice_manager.stop_listening()
            print("\nVoice command interface stopped")

    except Exception as e:
        click.echo(f"Error starting voice interface: {str(e)}")
        sys.exit(1)


def generate_compatibility_report(check: CompatibilityCheck, format: str) -> str:
    """Generate a compatibility report in the specified format."""
    if format == 'json':
        return json.dumps(check.to_dict(), indent=2)
    elif format == 'markdown':
        return check.to_markdown()
    else:  # text format
        lines = []

        # Environment info
        lines.extend(
            [
                "Environment:",
                f"  Python Version: {check.python_version}",
                f"  Operating System: {check.os_name}\n",
            ]
        )

        # Project status
        lines.extend(
            [
                "Project Status:",
                f"  Type: {'NADOO' if check.is_nadoo_project else 'Non-NADOO'} Project",
                f"  Current Version: {check.current_version or 'Not using NADOO Framework'}",
                f"  Latest Version: {check.latest_version}",
                f"  Needs Migration: {'Yes' if check.needs_migration else 'No'}\n",
            ]
        )

        # Compatibility issues
        if check.issues:
            lines.append("Compatibility Issues:")
            current_category = None
            for issue in sorted(check.issues, key=lambda x: (x.category, x.severity)):
                if issue.category != current_category:
                    lines.append(f"\n  {issue.category}:")
                    current_category = issue.category
                lines.append(f"    [{issue.severity.upper()}] {issue.message}")
                if issue.details:
                    lines.append(f"      Details: {issue.details}")
                if issue.fix_suggestion:
                    lines.append(f"      Fix: {issue.fix_suggestion}")
            lines.append("")

        # Required changes
        if check.changes:
            lines.extend(["Required Changes:", *[f"  - {change}" for change in check.changes], ""])

        return "\n".join(lines)


def generate_fix_report(results: Dict[str, List[FixResult]], format: str) -> str:
    """Generate a report of fix results."""
    if format == 'json':
        return json.dumps(
            {
                category: [
                    {
                        "success": result.success,
                        "message": result.message,
                        "details": result.details,
                    }
                    for result in category_results
                ]
                for category, category_results in results.items()
            },
            indent=2,
        )
    elif format == 'markdown':
        lines = ["# NADOO Framework Fix Report\n"]

        for category, category_results in results.items():
            lines.extend(
                [
                    f"## {category}",
                    "| Status | Message | Details |",
                    "|--------|---------|----------|",
                ]
            )

            for result in category_results:
                status = "✅" if result.success else "❌"
                lines.append(f"| {status} | {result.message} | {result.details or 'N/A'} |")
            lines.append("")

        return "\n".join(lines)
    else:  # text format
        lines = []

        for category, category_results in results.items():
            lines.append(f"\n{category}:")
            for result in category_results:
                status = "SUCCESS" if result.success else "FAILED"
                lines.append(f"  [{status}] {result.message}")
                if result.details:
                    lines.append(f"    Details: {result.details}")

        return "\n".join(lines)


@cli.command()
@click.argument(
    'project_path', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.'
)
@click.option('--name', prompt='Project name', help='Name of the project')
def init(project_path: str, name: str):
    """Initialize a new NADOO Framework project."""
    try:
        engine = MigrationEngine(Path(project_path))
        plan = engine.plan_migration()

        click.echo("\nInitialization Plan:")
        for step in plan.steps:
            click.echo(f"  - {step.description}")

        if click.confirm("\nDo you want to proceed with initialization?"):
            if engine.execute_plan(plan):
                click.echo("\nProject initialized successfully!")
            else:
                click.echo("\nInitialization failed. Check the error messages above.")
                sys.exit(1)

    except Exception as e:
        click.echo(f"Error during initialization: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
