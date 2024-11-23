"""Functions for analyzing project dependencies."""

from pathlib import Path
from typing import Dict, List, Set, Optional
import re
import toml
import ast

def parse_requirements_txt(file_path: Path) -> List[Dict[str, str]]:
    """Parse requirements from requirements.txt file.
    
    Args:
        file_path: Path to requirements.txt
        
    Returns:
        List of dictionaries containing package information
    """
    requirements = []
    if not file_path.exists():
        return requirements
        
    with open(file_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Parse package name and version
                match = re.match(r'^([^=<>]+)([=<>]+.+)?$', line)
                if match:
                    req = {
                        'name': match.group(1).strip(),
                        'constraint': (match.group(2) or '').strip()
                    }
                    requirements.append(req)
    return requirements

def parse_pyproject_toml(file_path: Path) -> Dict[str, any]:
    """Parse dependencies from pyproject.toml.
    
    Args:
        file_path: Path to pyproject.toml
        
    Returns:
        Dictionary containing project dependencies
    """
    if not file_path.exists():
        return {}
        
    try:
        data = toml.load(file_path)
        dependencies = {}
        
        # Check poetry dependencies
        if 'tool' in data and 'poetry' in data['tool']:
            poetry = data['tool']['poetry']
            if 'dependencies' in poetry:
                dependencies['main'] = poetry['dependencies']
            if 'dev-dependencies' in poetry:
                dependencies['dev'] = poetry['dev-dependencies']
                
        # Check project dependencies
        if 'project' in data:
            project = data['project']
            if 'dependencies' in project:
                dependencies['main'] = project['dependencies']
            if 'optional-dependencies' in project:
                dependencies['optional'] = project['optional-dependencies']
                
        return dependencies
    except Exception:
        return {}

def find_imported_packages(python_file: Path) -> Set[str]:
    """Find all imported packages in a Python file.
    
    Args:
        python_file: Path to Python file
        
    Returns:
        Set of imported package names
    """
    imports = set()
    try:
        with open(python_file) as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    # Get the base package name
                    base_package = name.name.split('.')[0]
                    imports.add(base_package)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Get the base package name
                    base_package = node.module.split('.')[0]
                    imports.add(base_package)
    except Exception:
        pass
    
    return imports

def analyze_project_dependencies(root_dir: Path) -> Dict[str, any]:
    """Analyze all dependencies in a Python project.
    
    Args:
        root_dir: Root directory of the project
        
    Returns:
        Dictionary containing dependency analysis
    """
    analysis = {
        'declared': {
            'requirements.txt': [],
            'pyproject.toml': {},
            'setup.py': []  # TODO: Implement setup.py parsing
        },
        'imported': set()
    }
    
    # Check requirements.txt
    req_file = root_dir / 'requirements.txt'
    if req_file.exists():
        analysis['declared']['requirements.txt'] = parse_requirements_txt(req_file)
        
    # Check pyproject.toml
    pyproject_file = root_dir / 'pyproject.toml'
    if pyproject_file.exists():
        analysis['declared']['pyproject.toml'] = parse_pyproject_toml(pyproject_file)
        
    # Find all imported packages
    for python_file in root_dir.rglob("*.py"):
        imports = find_imported_packages(python_file)
        analysis['imported'].update(imports)
        
    return analysis
