"""Functions for analyzing code structure and patterns."""

import ast
from pathlib import Path
from typing import Dict, List, Set, Optional

def extract_imports(file_path: Path) -> List[str]:
    """Extract all imports from a Python file.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        List of imported module names
    """
    imports = []
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for name in node.names:
                    imports.append(f"{module}.{name.name}")
    except Exception:
        pass
    return imports

def find_class_definitions(file_path: Path) -> List[Dict[str, any]]:
    """Find all class definitions in a Python file.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        List of dictionaries containing class information
    """
    classes = []
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = {
                    'name': node.name,
                    'bases': [base.id for base in node.bases if isinstance(base, ast.Name)],
                    'methods': [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
                    'line_number': node.lineno
                }
                classes.append(class_info)
    except Exception:
        pass
    return classes

def find_function_definitions(file_path: Path) -> List[Dict[str, any]]:
    """Find all function definitions in a Python file.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        List of dictionaries containing function information
    """
    functions = []
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    'name': node.name,
                    'args': [arg.arg for arg in node.args.args],
                    'line_number': node.lineno,
                    'decorators': [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
                }
                functions.append(func_info)
    except Exception:
        pass
    return functions
