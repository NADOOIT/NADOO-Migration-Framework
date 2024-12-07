import os
from typing import List

def create_standard_directory_structure_for_path(project_path: str) -> List[str]:
    """
    Creates the standard directory structure for a project.
    
    Args:
        project_path: Path where to create the structure
        
    Returns:
        List of created directories
    """
    directories = [
        'src/functions',
        'src/classes',
        'src/processes',
        'src/types',
        'tests',
        'logs'
    ]
    
    created_dirs = []
    for directory in directories:
        dir_path = os.path.join(project_path, directory)
        os.makedirs(dir_path, exist_ok=True)
        created_dirs.append(dir_path)
        
        # Create __init__.py in each Python package directory
        if directory.startswith('src/'):
            init_file = os.path.join(dir_path, '__init__.py')
            if not os.path.exists(init_file):
                with open(init_file, 'w') as f:
                    f.write('"""This module contains {}."""'.format(directory.split('/')[-1]))
