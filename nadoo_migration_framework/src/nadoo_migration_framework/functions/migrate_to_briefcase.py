"""
Migrate a NADOO project to Briefcase structure.

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
from typing import List, Dict, Set


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler('briefcase_migration.log'), logging.StreamHandler()],
    )


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
        os.path.join(project_path, 'src', 'processes'): os.path.join(new_src_path, 'processes'),
    }


def update_imports(file_path: str, app_name: str) -> None:
    """
    Update import statements in a Python file.

    Args:
        file_path: Path to the Python file
        app_name: Name of the app
    """
    with open(file_path, 'r') as f:
        content = f.read()

    # Update relative imports
    content = re.sub(r'from \.\.(functions|classes|processes)', f'from {app_name}.\\1', content)
    content = re.sub(r'from \.(functions|classes|processes)', f'from {app_name}.\\1', content)

    # Update absolute imports
    content = re.sub(r'from src\.(functions|classes|processes)', f'from {app_name}.\\1', content)

    with open(file_path, 'w') as f:
        f.write(content)


def migrate_files(path_mapping: Dict[str, str], app_name: str) -> None:
    """
    Migrate files to new structure and update imports.

    Args:
        path_mapping: Dictionary mapping old paths to new paths
        app_name: Name of the app
    """
    for old_path, new_path in path_mapping.items():
        if os.path.exists(old_path):
            # Copy files
            for item in os.listdir(old_path):
                if item == '__pycache__':
                    continue

                src = os.path.join(old_path, item)
                dst = os.path.join(new_path, item)

                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    if src.endswith('.py'):
                        update_imports(dst, app_name)
                elif os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                    # Update imports in all Python files
                    for root, _, files in os.walk(dst):
                        for file in files:
                            if file.endswith('.py'):
                                update_imports(os.path.join(root, file), app_name)


def update_pyproject_toml(project_path: str, app_name: str) -> None:
    """
    Update pyproject.toml for Briefcase structure.

    Args:
        project_path: Path to the project root
        app_name: Name of the app
    """
    pyproject_path = os.path.join(project_path, 'pyproject.toml')
    if not os.path.exists(pyproject_path):
        return

    with open(pyproject_path, 'r') as f:
        content = f.read()

    # Update package path if needed
    content = re.sub(
        r'packages\s*=\s*\[\s*{\s*include\s*=\s*"src"',
        f'packages = [{{ include = "{app_name}"',
        content,
    )

    with open(pyproject_path, 'w') as f:
        f.write(content)


def migrate_project(project_path: str) -> None:
    """
    Migrate a project to Briefcase structure.

    Args:
        project_path: Path to the project root
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Get app name
        app_name = get_app_name(project_path)
        logger.info(f"Migrating project {app_name}")

        # Create new structure
        path_mapping = create_briefcase_structure(project_path, app_name)
        logger.info("Created Briefcase directory structure")

        # Migrate files
        migrate_files(path_mapping, app_name)
        logger.info("Migrated files and updated imports")

        # Update pyproject.toml
        update_pyproject_toml(project_path, app_name)
        logger.info("Updated pyproject.toml")

        # Create backup of old src directory
        old_src = os.path.join(project_path, 'src')
        if os.path.exists(old_src):
            backup_src = os.path.join(project_path, 'src.bak')
            shutil.move(old_src, backup_src)
            logger.info(f"Created backup of old src directory at {backup_src}")

        logger.info(f"Successfully migrated {app_name} to Briefcase structure")

    except Exception as e:
        logger.error(f"Error migrating project: {str(e)}")
        raise


def migrate_multiple_projects(base_path: str, project_patterns: List[str] = None) -> None:
    """
    Migrate multiple projects to Briefcase structure.

    Args:
        base_path: Base path containing projects
        project_patterns: List of glob patterns to match project directories
    """
    if project_patterns is None:
        project_patterns = ['*']

    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Find all project directories
        projects = set()
        for pattern in project_patterns:
            for path in Path(base_path).glob(pattern):
                if path.is_dir() and (path / 'pyproject.toml').exists():
                    projects.add(str(path))

        if not projects:
            logger.warning(
                f"No projects found in {base_path} matching patterns: {project_patterns}"
            )
            return

        logger.info(f"Found {len(projects)} projects to migrate")

        # Migrate each project
        for project_path in sorted(projects):
            try:
                migrate_project(project_path)
            except Exception as e:
                logger.error(f"Failed to migrate {project_path}: {str(e)}")
                continue

        logger.info("Finished migrating all projects")

    except Exception as e:
        logger.error(f"Error in batch migration: {str(e)}")
        raise


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python migrate_to_briefcase.py PROJECT_PATH [PROJECT_PATTERNS...]")
        sys.exit(1)

    base_path = sys.argv[1]
    patterns = sys.argv[2:] if len(sys.argv) > 2 else None

    migrate_multiple_projects(base_path, patterns)
