"""Module for migrating Toga apps to a functional style."""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import libcst as cst
from libcst.codemod import CodemodContext, ContextAwareTransformer

@dataclass
class FunctionTransformation:
    """Represents a transformation of a function to its own file."""
    original_file: str
    new_file: str
    function_name: str
    function_code: str
    imports: List[str]
    is_curried: bool
    description: str

class FunctionExtractor(ast.NodeVisitor):
    """Extracts functions from Python files."""
    
    def __init__(self):
        self.functions: List[ast.FunctionDef] = []
        self.imports: List[ast.Import] = []
        self.curried_functions: Set[str] = set()
        
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self.functions.append(node)
        # Check if this function returns another function (currying)
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and isinstance(child.value, ast.Lambda):
                self.curried_functions.add(node.name)
        self.generic_visit(node)
        
    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement."""
        self.imports.append(node)
        
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from-import statement."""
        self.imports.append(node)

class TogaFunctionalMigrator:
    """Main class for migrating Toga apps to functional style."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.src_dir = self._find_src_dir()
        self.functions_dir = self.src_dir / 'functions' if self.src_dir else None
        
    def _find_src_dir(self) -> Optional[Path]:
        """Find the src directory containing the app code."""
        patterns = [
            'src',
            'src/*/src',  # For multi-platform projects
            '**/src'
        ]
        
        for pattern in patterns:
            src_dirs = list(self.project_dir.glob(pattern))
            if src_dirs:
                if any((self.project_dir / 'pyproject.toml').exists() for d in src_dirs):
                    return src_dirs[0]
        return None
        
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the src directory."""
        if not self.src_dir:
            return []
            
        py_files = []
        for py_file in self.src_dir.rglob('*.py'):
            # Skip test files and __init__.py
            if not py_file.name.startswith('test_') and py_file.name != '__init__.py':
                py_files.append(py_file)
        return py_files
        
    def analyze_file(self, file_path: Path) -> List[FunctionTransformation]:
        """Analyze a Python file for functions to extract."""
        with open(file_path) as f:
            content = f.read()
            
        # Parse the file
        tree = ast.parse(content)
        extractor = FunctionExtractor()
        extractor.visit(tree)
        
        transformations = []
        for func in extractor.functions:
            # Create function module name
            new_file = self.functions_dir / f"{func.name.lower()}.py"
            
            # Generate function code
            function_code = self._generate_function_code(
                func,
                extractor.imports,
                func.name in extractor.curried_functions
            )
            
            transformations.append(FunctionTransformation(
                original_file=str(file_path),
                new_file=str(new_file),
                function_name=func.name,
                function_code=function_code,
                imports=[ast.unparse(imp) for imp in extractor.imports],
                is_curried=func.name in extractor.curried_functions,
                description=f"Extract function {func.name} to its own module"
            ))
            
        return transformations
        
    def _generate_function_code(self, func: ast.FunctionDef, imports: List[ast.Import],
                             is_curried: bool) -> str:
        """Generate code for a function module."""
        code = "from typing import Any, Callable, Dict, List, Optional, TypeVar, Union\n\n"
        
        # Add original imports
        for imp in imports:
            code += ast.unparse(imp) + "\n"
        code += "\n"
        
        # Add type hints for curried functions if needed
        if is_curried:
            code += "T = TypeVar('T')\n"
            code += "R = TypeVar('R')\n\n"
            
        # Add function with docstring
        code += ast.unparse(func) + "\n"
        
        return code
        
    def extract_functions(self, transformations: List[FunctionTransformation]) -> None:
        """Extract functions to their own modules."""
        # Create functions directory if it doesn't exist
        self.functions_dir.mkdir(exist_ok=True)
        
        # Create function modules
        for transform in transformations:
            # Write function to new file
            with open(transform.new_file, 'w') as f:
                f.write(transform.function_code)
                
            # Update original file to import the function
            self._update_original_file(transform)
            
    def _update_original_file(self, transform: FunctionTransformation) -> None:
        """Update the original file to import the extracted function."""
        with open(transform.original_file) as f:
            tree = ast.parse(f.read())
            
        # Remove the original function
        new_body = []
        for node in tree.body:
            if not (isinstance(node, ast.FunctionDef) and node.name == transform.function_name):
                new_body.append(node)
                
        # Add import for the extracted function
        import_stmt = ast.ImportFrom(
            module=f"functions.{transform.function_name.lower()}",
            names=[ast.alias(name=transform.function_name)],
            level=0
        )
        new_body.insert(0, import_stmt)
        
        # Write updated file
        with open(transform.original_file, 'w') as f:
            f.write(ast.unparse(ast.Module(body=new_body, type_ignores=[])))
            
    def migrate_project(self) -> List[FunctionTransformation]:
        """Migrate the entire Toga app project."""
        transformations = []
        
        # Find and transform all Python files
        for py_file in self.find_python_files():
            file_transforms = self.analyze_file(py_file)
            if file_transforms:
                transformations.extend(file_transforms)
                
        # Apply transformations
        self.extract_functions(transformations)
        
        return transformations
