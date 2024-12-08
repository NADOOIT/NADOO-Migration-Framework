import os
import re
from typing import List, Dict, Any


def update_feed_manager(project_path: str) -> bool:
    """
    Updates the FeedManager implementation in a project to use the latest NADOO Framework version.

    Args:
        project_path: Path to the project root

    Returns:
        bool: True if update was successful
    """
    try:
        # Find all Python files that might contain FeedManager references
        feed_manager_files = []
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'FeedManager' in content or 'create_main_window' in content:
                            feed_manager_files.append(file_path)

        for file_path in feed_manager_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Update imports
            content = re.sub(
                r'from \.FeedManager import FeedManager',
                'from nadoo_framework.feed_manager import FeedManager',
                content,
            )

            # Add import for add_element_to_feed if needed
            if (
                'manager.create_element(' in content
                and 'from nadoo_framework.feed_manager import add_element_to_feed' not in content
            ):
                content = 'from nadoo_framework.feed_manager import add_element_to_feed\n' + content

            # Update direct element creation to use add_element_to_feed
            content = re.sub(
                r'manager\s*=\s*FeedManager\.get_instance\(\)\s*\n\s*manager\.create_element\((.*?)\)',
                r'add_element_to_feed(\1)',
                content,
            )

            # Update window creation pattern
            content = re.sub(
                r'def create_main_window\((.*?)\):', r'def get_main_window_element_for_\1:', content
            )

            # Update window creation pattern (no args)
            content = re.sub(
                r'def create_main_window\(\):', r'def get_main_window_element:', content
            )

            # Add base path setup for FeedManager
            if 'FeedManager.get_instance()' in content and 'set_base_path' not in content:
                base_path_setup = '''
# Set base path for function discovery
manager = FeedManager.get_instance()
manager.set_base_path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
'''
                content = 'import os\n' + content
                content = content.replace(
                    'FeedManager.get_instance()', 'FeedManager.get_instance()\n' + base_path_setup
                )

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        return True
    except Exception as e:
        print(f"Error updating FeedManager: {str(e)}")
        return False
