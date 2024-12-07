import os
import ast
from typing import Optional, Tuple

def extract_function_from_file_to_new_file(source_file: str, function_name: str, target_dir: str) -> Optional[str]:
    """
    Extracts a function from a source file and creates a new file for it.
    
    Args:
        source_file: Path to the source file
        function_name: Name of the function to extract
        target_dir: Directory where to create the new file
        
    Returns:
        Path to the new file if successful, None otherwise
    """
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        imports = []
        function_node = None
        
        # Find imports and the target function
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.get_source_segment(content, node))
            elif isinstance(node, ast.FunctionDef) and node.name == function_name:
                function_node = node
                
        if not function_node:
            return None
            
        # Create new file content
        new_content = '\n'.join(imports) + '\n\n'
        new_content += ast.get_source_segment(content, function_node)
        
        # Create new file
        new_file = os.path.join(target_dir, f"{function_name}.py")
        with open(new_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return new_file
    except Exception as e:
        print(f"Error extracting function {function_name}: {str(e)}")
        return None
