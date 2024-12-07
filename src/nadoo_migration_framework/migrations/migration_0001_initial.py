"""Initial migration to create the basic project structure."""

import os
import shutil
from pathlib import Path
from .base import Migration
from ..functions.project_structure_migrator import ProjectStructure

class Migration0001Initial(Migration):
    """Initial migration to create the basic project structure."""
    
    def apply(self) -> bool:
        """Apply the initial migration."""
        if self.is_applied():
            return False
        
        # Create src directory if it doesn't exist
        src_path = os.path.join(self.project_path, 'src')
        if not os.path.exists(src_path):
            os.makedirs(src_path)
            os.makedirs(os.path.join(src_path, 'functions'))
            os.makedirs(os.path.join(src_path, 'classes'))
            os.makedirs(os.path.join(src_path, 'processes'))
            
            # Create __init__.py files
            for dir_name in ['', 'functions', 'classes', 'processes']:
                init_path = os.path.join(src_path, dir_name, '__init__.py')
                with open(init_path, 'w') as f:
                    f.write(f'"""{"Main package" if not dir_name else dir_name.capitalize()} for the project."""\n')
        
        self._save_state(True, "Created initial project structure")
        return True
    
    def rollback(self) -> bool:
        """Rollback the initial migration."""
        if not self.is_applied():
            return False
        
        src_path = os.path.join(self.project_path, 'src')
        if os.path.exists(src_path):
            # Create backup
            backup_path = os.path.join(self.project_path, 'src.bak')
            if os.path.exists(src_path):
                shutil.move(src_path, backup_path)
        
        self._save_state(False, "Rolled back initial project structure")
        return True
