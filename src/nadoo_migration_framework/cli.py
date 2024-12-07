"""Command-line interface for NADOO Migration Framework."""

import os
import sys
import argparse
from typing import List
from .migrations.migration_manager import MigrationManager
from .migrations.repository_scanner import RepositoryScanner
from .functions.project_structure_migrator import ProjectStructure

def parse_args(args: List[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="NADOO Migration Framework CLI")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Migrate a project')
    migrate_parser.add_argument('project_path', help='Path to the project to migrate')
    migrate_parser.add_argument('--migration', help='Specific migration to run')
    migrate_parser.add_argument('--dry-run', action='store_true', help='Perform a dry run')
    migrate_parser.add_argument('--target', choices=['underscore', 'dash'],
                              default='underscore',
                              help='Target naming convention for Briefcase structure')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Roll back migrations')
    rollback_parser.add_argument('project_path', help='Path to the project')
    rollback_parser.add_argument('--migration', help='Specific migration to rollback')
    
    # Show migrations command
    show_parser = subparsers.add_parser('showmigrations', help='Show migration status')
    show_parser.add_argument('project_path', help='Path to the project')
    
    # Scan repositories command
    scan_parser = subparsers.add_parser('scan', help='Scan GitHub repositories')
    scan_parser.add_argument('github_path', help='Path to GitHub repositories directory')
    scan_parser.add_argument('--save', help='Save scan results to file', action='store_true')
    scan_parser.add_argument('--output', help='Output file for scan results', default='repositories.json')
    
    # Migrate repositories command
    migrate_repos_parser = subparsers.add_parser('migraterepos', help='Migrate GitHub repositories')
    migrate_repos_parser.add_argument('github_path', help='Path to GitHub repositories directory')
    migrate_repos_parser.add_argument('--target', choices=['underscore', 'dash'],
                                    default='underscore',
                                    help='Target naming convention for Briefcase structure')
    migrate_repos_parser.add_argument('--input', help='Input file with scan results')
    
    # GUI command
    gui_parser = subparsers.add_parser('gui', help='Launch the NADOO Migration Framework GUI')
    
    return parser.parse_args(args)

def main(args: List[str] = None) -> None:
    """Main entry point for the CLI."""
    if args is None:
        args = sys.argv[1:]
    
    parsed_args = parse_args(args)
    
    if not parsed_args.command:
        print("Error: No command specified", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Handle repository scanning commands
        if parsed_args.command in ['scan', 'migraterepos']:
            github_path = os.path.abspath(parsed_args.github_path)
            scanner = RepositoryScanner(github_path)
            
            if parsed_args.command == 'scan':
                repos = scanner.scan_repositories()
                if parsed_args.save:
                    scanner.save_scan_results(parsed_args.output)
                else:
                    print("\nFound repositories:")
                    for repo in repos:
                        print(f"- {repo['name']}: {repo['path']}")
            
            else:  # migraterepos
                target_structure = (ProjectStructure.BRIEFCASE_UNDERSCORE 
                                  if parsed_args.target == 'underscore' 
                                  else ProjectStructure.BRIEFCASE_DASH)
                
                if parsed_args.input:
                    repos = scanner.load_scan_results(parsed_args.input)
                    if not repos:
                        print(f"No repositories found in {parsed_args.input}", file=sys.stderr)
                        sys.exit(1)
                
                scanner.migrate_repositories(target_structure)
        
        # Handle single project commands
        elif parsed_args.command in ['migrate', 'rollback', 'showmigrations']:
            project_path = os.path.abspath(parsed_args.project_path)
            manager = MigrationManager(project_path)
            
            if parsed_args.command == 'migrate':
                if parsed_args.migration:
                    # Run specific migration
                    for migration in manager.migrations:
                        if migration.name == parsed_args.migration:
                            if manager.migrate(migration, parsed_args.dry_run):
                                print(f"Successfully ran migration: {migration.name}")
                            else:
                                print(f"Failed to run migration: {migration.name}")
                            break
                    else:
                        print(f"Migration not found: {parsed_args.migration}")
                else:
                    # Run all migrations
                    target_structure = (ProjectStructure.BRIEFCASE_UNDERSCORE 
                                     if parsed_args.target == 'underscore' 
                                     else ProjectStructure.BRIEFCASE_DASH)
                    manager.apply_migrations(target_structure)
            
            elif parsed_args.command == 'rollback':
                if parsed_args.migration:
                    manager.rollback_migration(parsed_args.migration)
                else:
                    manager.rollback_all()
            
            elif parsed_args.command == 'showmigrations':
                manager.show_migrations()
        
        # Handle GUI command
        elif parsed_args.command == 'gui':
            from .gui.toga_app import main
            main().main_loop()
    
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
