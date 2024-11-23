"""Functions for analyzing and manipulating project structure."""

from pathlib import Path
from typing import Dict, List, Set, Optional

def find_python_files(root_dir: Path) -> List[Path]:
    """Find all Python files in a directory recursively.
    
    Args:
        root_dir: Root directory to search from
        
    Returns:
        List of paths to Python files
    """
    return list(root_dir.rglob("*.py"))

def find_package_files(root_dir: Path) -> List[Path]:
    """Find all package configuration files.
    
    Args:
        root_dir: Root directory to search from
        
    Returns:
        List of paths to package files (setup.py, pyproject.toml, etc.)
    """
    package_files = []
    for pattern in ["setup.py", "pyproject.toml", "setup.cfg", "requirements.txt"]:
        package_files.extend(root_dir.rglob(pattern))
    return package_files

def get_package_structure(root_dir: Path) -> Dict[str, any]:
    """Analyze Python package structure.
    
    Args:
        root_dir: Root directory of the package
        
    Returns:
        Dictionary describing package structure
    """
    structure = {
        'root': str(root_dir),
        'packages': [],
        'modules': [],
        'tests': [],
        'config_files': []
    }
    
    for path in root_dir.rglob("*"):
        if path.is_file():
            rel_path = str(path.relative_to(root_dir))
            
            if path.suffix == '.py':
                if 'test' in path.stem.lower() or 'tests' in path.parts:
                    structure['tests'].append(rel_path)
                elif path.name == '__init__.py':
                    structure['packages'].append(str(path.parent.relative_to(root_dir)))
                else:
                    structure['modules'].append(rel_path)
            elif path.name in ['setup.py', 'pyproject.toml', 'setup.cfg', 'requirements.txt']:
                structure['config_files'].append(rel_path)
                
    return structure

def is_package_root(path: Path) -> bool:
    """Check if a directory is a Python package root.
    
    Args:
        path: Directory path to check
        
    Returns:
        True if directory appears to be a Python package root
    """
    return any((path / f).exists() for f in [
        'setup.py',
        'pyproject.toml',
        'setup.cfg',
        'requirements.txt'
    ])

def find_entry_points(root_dir: Path) -> List[Dict[str, str]]:
    """Find potential entry points in a Python project.
    
    Args:
        root_dir: Root directory to search from
        
    Returns:
        List of dictionaries containing entry point information
    """
    entry_points = []
    
    # Common entry point patterns
    patterns = [
        'main.py',
        'app.py',
        'run.py',
        'cli.py',
        'server.py'
    ]
    
    for pattern in patterns:
        for path in root_dir.rglob(pattern):
            entry_points.append({
                'name': path.stem,
                'path': str(path.relative_to(root_dir)),
                'type': 'script'
            })
            
    # Also check setup.py/pyproject.toml for console_scripts
    # TODO: Implement parsing of setup.py and pyproject.toml for entry points
    
    return entry_points
