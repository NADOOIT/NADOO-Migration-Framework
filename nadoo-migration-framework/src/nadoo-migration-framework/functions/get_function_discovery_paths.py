import os
from typing import List, Optional

def get_function_discovery_paths(base_path: str) -> List[str]:
    """
    Gets all possible paths where functions could be located across different NADOO apps.
    
    Args:
        base_path: Base path where apps are installed
        
    Returns:
        List of paths to search for functions
    """
    discovery_paths = []
    
    # Walk through the base path
    for root, dirs, files in os.walk(base_path):
        # Look for src directories that might contain functions
        if 'src' in dirs:
            src_path = os.path.join(root, 'src')
            # Check if this is a NADOO app (has functions directory)
            for app_name in os.listdir(src_path):
                app_path = os.path.join(src_path, app_name)
                if os.path.isdir(app_path):
                    functions_path = os.path.join(app_path, 'functions')
                    if os.path.exists(functions_path):
                        discovery_paths.append(functions_path)
    
    return discovery_paths

def find_function_in_discovery_paths(function_name: str, discovery_paths: List[str]) -> Optional[str]:
    """
    Finds a function across all discovery paths.
    
    Args:
        function_name: Name of the function to find
        discovery_paths: List of paths to search
        
    Returns:
        Full path to the function module if found, None otherwise
    """
    for path in discovery_paths:
        function_file = os.path.join(path, f"{function_name}.py")
        if os.path.exists(function_file):
            return function_file
    return None
