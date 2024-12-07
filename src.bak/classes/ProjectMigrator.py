import os
import logging
import shutil
from typing import Dict, List, Any
from ..functions.get_project_structure_for_path import get_project_structure_for_path
from ..functions.create_standard_directory_structure_for_path import create_standard_directory_structure_for_path
from ..functions.extract_function_from_file_to_new_file import extract_function_from_file_to_new_file
from ..functions.convert_to_briefcase_toga import convert_to_briefcase_toga
from ..functions.update_feed_manager import update_feed_manager

class ProjectMigrator:
    def __init__(self, project_path: str, app_name: str = None, app_formal_name: str = None):
        """
        Initialize the ProjectMigrator.
        
        Args:
            project_path: Path to the project to migrate
            app_name: Optional name for the toga app (default: derived from directory name)
            app_formal_name: Optional formal name for the toga app (default: derived from app_name)
        """
        self.project_path = project_path
        self.app_name = app_name or os.path.basename(project_path).lower().replace('-', '_')
        self.app_formal_name = app_formal_name or ' '.join(word.capitalize() for word in self.app_name.split('_'))
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Sets up logging for the migrator."""
        logger = logging.getLogger(f'ProjectMigrator-{os.path.basename(self.project_path)}')
        logger.setLevel(logging.INFO)
        
        # Create handlers
        log_file = os.path.join(self.project_path, 'logs', 'migration.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create formatters and add it to handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handlers to the logger
        logger.addHandler(file_handler)
        
        return logger
        
    def migrate(self) -> bool:
        """
        Migrates the project to the new structure.
        
        Returns:
            bool: True if migration was successful, False otherwise
        """
        try:
            self.logger.info(f"Starting migration for project: {self.project_path}")
            
            # Get current project structure
            structure = get_project_structure_for_path(self.project_path)
            
            # Create new directory structure
            create_standard_directory_structure_for_path(self.project_path)
            
            # Migrate functions
            functions_dir = os.path.join(self.project_path, 'src', 'functions')
            for func_file in structure['functions']:
                # Get function name from file content
                with open(func_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Simple function name extraction - can be improved
                    for line in content.split('\n'):
                        if line.strip().startswith('def '):
                            func_name = line.strip().split('def ')[1].split('(')[0].strip()
                            new_file = extract_function_from_file_to_new_file(func_file, func_name, functions_dir)
                            if new_file:
                                self.logger.info(f"Migrated function {func_name} to {new_file}")
                                break
                    
            # Move class files
            classes_dir = os.path.join(self.project_path, 'src', 'classes')
            for class_file in structure['classes']:
                target_file = os.path.join(classes_dir, os.path.basename(class_file))
                shutil.copy2(class_file, target_file)
                self.logger.info(f"Moved class file {class_file} to {target_file}")
                
            # Move process files
            processes_dir = os.path.join(self.project_path, 'src', 'processes')
            for process_file in structure['processes']:
                target_file = os.path.join(processes_dir, os.path.basename(process_file))
                shutil.copy2(process_file, target_file)
                self.logger.info(f"Moved process file {process_file} to {target_file}")
                
            # Move type files
            types_dir = os.path.join(self.project_path, 'src', 'types')
            for type_file in structure['types']:
                target_file = os.path.join(types_dir, os.path.basename(type_file))
                shutil.copy2(type_file, target_file)
                self.logger.info(f"Moved type file {type_file} to {target_file}")

            # Convert to briefcase toga app
            if convert_to_briefcase_toga(self.project_path, self.app_name, self.app_formal_name):
                self.logger.info("Successfully converted to briefcase toga app")
            else:
                self.logger.error("Failed to convert to briefcase toga app")
                return False

            # Update FeedManager implementations
            if update_feed_manager(self.project_path):
                self.logger.info("Successfully updated FeedManager implementations")
            else:
                self.logger.error("Failed to update FeedManager implementations")
                return False
                
            self.logger.info("Migration completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during migration: {str(e)}")
            return False
