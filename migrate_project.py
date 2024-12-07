#!/usr/bin/env python3
import os
import sys
import argparse
import logging
from src.classes.ProjectMigrator import ProjectMigrator
from src.processes.ProcessManager import ProcessManager

def setup_logging():
    """Sets up logging for the migration script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('migration.log')
        ]
    )
    return logging.getLogger('migrate_project')

def main():
    """Main entry point for the migration script."""
    logger = setup_logging()
    
    parser = argparse.ArgumentParser(description='Migrate a project to the new structure.')
    parser.add_argument('project_path', help='Path to the project to migrate')
    args = parser.parse_args()
    
    # Ensure project path exists
    if not os.path.exists(args.project_path):
        logger.error(f"Project path does not exist: {args.project_path}")
        return 1
        
    try:
        # Start the process manager
        process_manager = ProcessManager()
        
        # Create and run the project migrator
        migrator = ProjectMigrator(args.project_path)
        success = migrator.migrate()
        
        if success:
            logger.info(f"Successfully migrated project: {args.project_path}")
            return 0
        else:
            logger.error(f"Failed to migrate project: {args.project_path}")
            return 1
            
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return 1
    finally:
        # Ensure process manager is shut down
        if 'process_manager' in locals():
            process_manager.running = False

if __name__ == "__main__":
    sys.exit(main())
