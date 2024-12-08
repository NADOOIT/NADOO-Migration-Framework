import os
import shutil
from typing import Dict, Any


def convert_to_briefcase_toga(project_path: str, app_name: str, app_formal_name: str) -> bool:
    """
    Converts a project to a briefcase toga app structure.

    Args:
        project_path: Path to the project
        app_name: The package name of the app (e.g., 'myapp')
        app_formal_name: The formal name of the app (e.g., 'My App')

    Returns:
        bool: True if conversion was successful
    """
    try:
        # Create pyproject.toml
        pyproject_content = f'''[tool.briefcase]
project_name = "{app_name}"
version = "0.0.1"
url = ""
license = "BSD license"
author = 'NADOO Framework'
author_email = ""

[tool.briefcase.app.{app_name}]
formal_name = "{app_formal_name}"
description = "A NADOO Framework App"
icon = "src/resources/icon"
sources = ['src/{app_name}']
requires = [
    'toga>=0.3.0',
    'pyzmq>=25.1.0',
]

[tool.briefcase.app.{app_name}.macOS]
requires = []

[tool.briefcase.app.{app_name}.linux]
requires = []

[tool.briefcase.app.{app_name}.windows]
requires = []
'''
        with open(os.path.join(project_path, 'pyproject.toml'), 'w') as f:
            f.write(pyproject_content)

        # Create app directory structure
        app_dir = os.path.join(project_path, 'src', app_name)
        os.makedirs(app_dir, exist_ok=True)
        os.makedirs(os.path.join(app_dir, 'resources'), exist_ok=True)

        # Move existing src contents into app directory
        src_path = os.path.join(project_path, 'src')
        for item in os.listdir(src_path):
            if item != app_name:
                src_item = os.path.join(src_path, item)
                dst_item = os.path.join(app_dir, item)
                if os.path.isdir(src_item):
                    shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_item, dst_item)

        # Create __main__.py if it doesn't exist
        main_py_path = os.path.join(app_dir, '__main__.py')
        if not os.path.exists(main_py_path):
            main_py_content = f'''import toga
from .app import {app_formal_name.replace(" ", "")}App

def main():
    return {app_formal_name.replace(" ", "")}App()

if __name__ == '__main__':
    main().main_loop()
'''
            with open(main_py_path, 'w') as f:
                f.write(main_py_content)

        return True
    except Exception as e:
        print(f"Error converting to briefcase toga app: {str(e)}")
        return False
