"""
Project Structure Migrator for NADOO projects.

This module provides functionality to migrate between different project structures:
1. Legacy structure (flat)
2. Dash-based Briefcase structure (app-name)
3. Underscore-based Briefcase structure (app_name)

The Briefcase structure follows:
Repository/
    app_name/
        src/
            app_name/
                __init__.py
                app.py
                functions/
                classes/
                processes/
"""

import os
import shutil
import re
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum

class ProjectStructure(Enum):
    LEGACY = "legacy"  # Flat structure
    BRIEFCASE_DASH = "briefcase-dash"  # app-name
    BRIEFCASE_UNDERSCORE = "briefcase_underscore"  # app_name

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('project_migration.log'),
            logging.StreamHandler()
        ]
    )

def detect_project_structure(project_path: str) -> ProjectStructure:
    """
    Detect the current project structure.
    
    Args:
        project_path: Path to the project root
        
    Returns:
        ProjectStructure enum indicating the detected structure
    """
    src_path = os.path.join(project_path, 'src')
    
    # Check if it's a legacy structure (flat)
    if os.path.exists(src_path) and any(os.path.exists(os.path.join(src_path, d)) for d in ['functions', 'classes', 'processes']):
        return ProjectStructure.LEGACY
    
    # Get app name from pyproject.toml
    app_name = get_app_name(project_path)
    
    # Check for dash-based Briefcase structure
    if os.path.exists(os.path.join(project_path, app_name.replace('_', '-'), 'src')):
        return ProjectStructure.BRIEFCASE_DASH
    
    # Check for underscore-based Briefcase structure
    if os.path.exists(os.path.join(project_path, app_name.replace('-', '_'), 'src')):
        return ProjectStructure.BRIEFCASE_UNDERSCORE
    
    # Default to legacy if structure is unclear
    return ProjectStructure.LEGACY

def get_app_name(project_path: str) -> str:
    """
    Get the app name from pyproject.toml or directory name.
    
    Args:
        project_path: Path to the project root
        
    Returns:
        App name
    """
    pyproject_path = os.path.join(project_path, 'pyproject.toml')
    if os.path.exists(pyproject_path):
        with open(pyproject_path, 'r') as f:
            content = f.read()
            # Try to find name in pyproject.toml
            match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)
    
    # Fall back to directory name
    return os.path.basename(project_path)

def normalize_app_name(app_name: str, target_structure: ProjectStructure) -> str:
    """
    Normalize app name according to target structure.
    
    Args:
        app_name: Original app name
        target_structure: Target project structure
        
    Returns:
        Normalized app name
    """
    if target_structure == ProjectStructure.BRIEFCASE_DASH:
        return app_name.replace('_', '-')
    elif target_structure == ProjectStructure.BRIEFCASE_UNDERSCORE:
        return app_name.replace('-', '_')
    return app_name

def create_briefcase_structure(project_path: str, app_name: str) -> Dict[str, str]:
    """
    Create Briefcase directory structure.
    
    Args:
        project_path: Path to the project root
        app_name: Name of the app
        
    Returns:
        Dictionary mapping old paths to new paths
    """
    # Create new directory structure
    new_src_path = os.path.join(project_path, app_name, 'src', app_name)
    os.makedirs(new_src_path, exist_ok=True)
    
    # Create __init__.py
    with open(os.path.join(new_src_path, '__init__.py'), 'w') as f:
        f.write(f'"""Main package for {app_name}."""\n')
    
    # Create directories
    dirs = ['functions', 'classes', 'processes']
    for dir_name in dirs:
        os.makedirs(os.path.join(new_src_path, dir_name), exist_ok=True)
        init_path = os.path.join(new_src_path, dir_name, '__init__.py')
        if not os.path.exists(init_path):
            with open(init_path, 'w') as f:
                f.write(f'"""{dir_name.capitalize()} for {app_name}."""\n')
    
    return {
        os.path.join(project_path, 'src', 'functions'): os.path.join(new_src_path, 'functions'),
        os.path.join(project_path, 'src', 'classes'): os.path.join(new_src_path, 'classes'),
        os.path.join(project_path, 'src', 'processes'): os.path.join(new_src_path, 'processes')
    }

def update_imports(file_path: str, app_name: str, old_structure: ProjectStructure, new_structure: ProjectStructure) -> None:
    """
    Update import statements in a Python file.
    
    Args:
        file_path: Path to the Python file
        app_name: Name of the app
        old_structure: Current project structure
        new_structure: Target project structure
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    old_app_name = normalize_app_name(app_name, old_structure)
    new_app_name = normalize_app_name(app_name, new_structure)
    
    # Update imports
    if old_structure == ProjectStructure.LEGACY:
        # Update from relative to absolute imports
        content = re.sub(r'from\s+src\.', f'from {new_app_name}.', content)
        content = re.sub(r'import\s+src\.', f'import {new_app_name}.', content)
    else:
        # Update between different Briefcase structures
        content = content.replace(old_app_name, new_app_name)
    
    with open(file_path, 'w') as f:
        f.write(content)

def migrate_files(path_mapping: Dict[str, str], app_name: str, old_structure: ProjectStructure, new_structure: ProjectStructure) -> None:
    """
    Migrate files to new structure and update imports.
    
    Args:
        path_mapping: Dictionary mapping old paths to new paths
        app_name: Name of the app
        old_structure: Current project structure
        new_structure: Target project structure
    """
    for old_path, new_path in path_mapping.items():
        if os.path.exists(old_path):
            # Copy files
            if not os.path.exists(new_path):
                shutil.copytree(old_path, new_path)
            
            # Update imports in Python files
            for root, _, files in os.walk(new_path):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        update_imports(file_path, app_name, old_structure, new_structure)

def update_pyproject_toml(project_path: str, app_name: str, target_structure: ProjectStructure) -> None:
    """
    Update pyproject.toml for target structure.
    
    Args:
        project_path: Path to the project root
        app_name: Name of the app
        target_structure: Target project structure
    """
    pyproject_path = os.path.join(project_path, 'pyproject.toml')
    if not os.path.exists(pyproject_path):
        return
    
    with open(pyproject_path, 'r') as f:
        content = f.read()
    
    # Update app name in pyproject.toml
    normalized_name = normalize_app_name(app_name, target_structure)
    content = re.sub(r'(name\s*=\s*["\'])([^"\']+)(["\'])', f'\\1{normalized_name}\\3', content)
    
    with open(pyproject_path, 'w') as f:
        f.write(content)

def migrate_project(project_path: str, target_structure: ProjectStructure = ProjectStructure.BRIEFCASE_UNDERSCORE) -> None:
    """
    Migrate a project to the target structure.
    
    Args:
        project_path: Path to the project root
        target_structure: Target project structure
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Detect current structure
        current_structure = detect_project_structure(project_path)
        if current_structure == target_structure:
            logger.info(f"Project is already in {target_structure.value} structure")
            return
        
        # Get and normalize app name
        app_name = get_app_name(project_path)
        normalized_name = normalize_app_name(app_name, target_structure)
        
        logger.info(f"Migrating project {app_name} from {current_structure.value} to {target_structure.value}")
        
        # Create new structure
        path_mapping = create_briefcase_structure(project_path, normalized_name)
        
        # Migrate files and update imports
        migrate_files(path_mapping, app_name, current_structure, target_structure)
        
        # Update pyproject.toml
        update_pyproject_toml(project_path, app_name, target_structure)
        
        # Backup old structure
        old_src = os.path.join(project_path, 'src')
        if os.path.exists(old_src):
            backup_path = os.path.join(project_path, 'src.bak')
            shutil.move(old_src, backup_path)
            logger.info(f"Created backup of old src directory at {backup_path}")
        
        logger.info(f"Successfully migrated {app_name} to {target_structure.value} structure")
        
    except Exception as e:
        logger.error(f"Error migrating project: {str(e)}")
        raise

def migrate_multiple_projects(base_path: str, project_patterns: List[str] = None, target_structure: ProjectStructure = ProjectStructure.BRIEFCASE_UNDERSCORE) -> None:
    """
    Migrate multiple projects to target structure.
    
    Args:
        base_path: Base path containing projects
        project_patterns: List of glob patterns to match project directories
        target_structure: Target project structure
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    if not project_patterns:
        project_patterns = ['**/pyproject.toml']
    
    for pattern in project_patterns:
        for pyproject_path in Path(base_path).glob(pattern):
            project_path = str(pyproject_path.parent)
            try:
                migrate_project(project_path, target_structure)
            except Exception as e:
                logger.error(f"Failed to migrate {project_path}: {str(e)}")
                continue

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python project_structure_migrator.py PROJECT_PATH [PROJECT_PATTERNS...]")
        sys.exit(1)
    
    project_path = sys.argv[1]
    patterns = sys.argv[2:] if len(sys.argv) > 2 else None
    
    if os.path.isdir(project_path):
        migrate_project(project_path)
    else:
        migrate_multiple_projects(project_path, patterns)
