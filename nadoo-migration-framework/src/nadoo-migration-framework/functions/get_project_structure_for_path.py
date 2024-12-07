import os
from typing import Dict, List, Any

def get_project_structure_for_path(project_path: str) -> Dict[str, Any]:
    """
    Analyzes a project directory and returns its structure.
    
    Args:
        project_path: Path to the project root directory
        
    Returns:
        Dict containing the project structure with files and their types
    """
    structure = {
        'files': [],
        'functions': [],
        'classes': [],
        'processes': [],
        'types': []
    }
    
    for root, dirs, files in os.walk(project_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Identify file type based on content and filename
                    if any(marker in content for marker in ['zmq.', 'ProcessManager', 'process']):
                        structure['processes'].append(file_path)
                    elif 'class ' in content:
                        structure['classes'].append(file_path)
                    elif 'def ' in content and not any(marker in content for marker in ['class ', 'if __name__']):
                        structure['functions'].append(file_path)
                    elif any(marker in content for marker in ['TypeAlias', 'TypeVar', '@dataclass']):
                        structure['types'].append(file_path)
                    else:
                        structure['files'].append(file_path)
                except Exception as e:
                    print(f"Error reading file {file_path}: {str(e)}")
                    structure['files'].append(file_path)
    
    return structure
