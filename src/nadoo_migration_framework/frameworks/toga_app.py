"""Module for migrating Briefcase Toga apps to a more modular structure."""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
import libcst as cst
from libcst.codemod import CodemodContext, ContextAwareTransformer

@dataclass
class ViewTransformation:
    """Represents a transformation of a Toga view/window class."""
    view_file: str
    logic_file: str
    original_code: str
    view_code: str
    logic_code: str
    imports_to_update: List[str]
    description: str

class ViewLogicExtractor(ast.NodeVisitor):
    """Extracts logic methods from Toga view/window classes."""
    
    def __init__(self):
        self.gui_methods: List[ast.FunctionDef] = []
        self.logic_methods: List[ast.FunctionDef] = []
        self.imports: List[ast.Import] = []
        self.class_name: Optional[str] = None
        
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition and collect methods."""
        # Check if this is a Toga window/view class
        is_toga_class = False
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in {'Window', 'Box', 'ScrollContainer', 'SplitContainer'}:
                is_toga_class = True
                break
                
        if is_toga_class:
            self.class_name = node.name
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    # Check if method is GUI-related
                    if self._is_gui_method(item):
                        self.gui_methods.append(item)
                    else:
                        self.logic_methods.append(item)
        self.generic_visit(node)
        
    def _is_gui_method(self, node: ast.FunctionDef) -> bool:
        """Determine if a method is GUI-related."""
        # Methods that are clearly GUI-related
        gui_prefixes = {'on_', 'handle_', 'create_', 'update_ui_', 'refresh_', 'startup', 'shutdown'}
        if any(node.name.startswith(prefix) for prefix in gui_prefixes):
            return True
            
        # Check method body for Toga usage
        toga_usage = False
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and any(toga_name in child.id for toga_name in ['toga', 'Window', 'Box', 'Button', 'TextInput']):
                toga_usage = True
                break
        return toga_usage

class TogaImportUpdater(ContextAwareTransformer):
    """Updates imports in Toga app files."""
    
    def __init__(self, context: CodemodContext, old_to_new: Dict[str, str]):
        super().__init__(context)
        self.old_to_new = old_to_new
        
    def leave_Import(self, original_node: cst.Import, updated_node: cst.Import) -> cst.Import:
        """Update import statements."""
        new_names = []
        for name in original_node.names:
            old_name = name.name.value
            if old_name in self.old_to_new:
                new_names.append(name.with_changes(
                    name=cst.Name(self.old_to_new[old_name])
                ))
            else:
                new_names.append(name)
        return updated_node.with_changes(names=new_names)

class BriefcaseTogaMigrator:
    """Main class for migrating Briefcase Toga apps."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.src_dir = self._find_src_dir()
        self.logic_dir = self.src_dir / 'logic' if self.src_dir else None
        
    def _find_src_dir(self) -> Optional[Path]:
        """Find the src directory containing the app code."""
        # Common Briefcase src directory patterns
        patterns = [
            'src',
            'src/*/src',  # For multi-platform projects
            '**/src'
        ]
        
        for pattern in patterns:
            src_dirs = list(self.project_dir.glob(pattern))
            if src_dirs:
                # Look for pyproject.toml to verify it's a Briefcase project
                if any((self.project_dir / 'pyproject.toml').exists() for d in src_dirs):
                    return src_dirs[0]
        return None
        
    def find_view_files(self) -> List[Path]:
        """Find all view files in the src directory."""
        if not self.src_dir:
            return []
            
        view_files = []
        for py_file in self.src_dir.rglob('*.py'):
            if py_file.stem in {'app', 'main'}:
                continue  # Skip main app files
                
            with open(py_file) as f:
                content = f.read()
                
            # Check if file contains Toga view/window classes
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for base in node.bases:
                            if isinstance(base, ast.Name) and base.id in {'Window', 'Box', 'ScrollContainer', 'SplitContainer'}:
                                view_files.append(py_file)
                                break
            except SyntaxError:
                continue
                
        return view_files
        
    def analyze_view(self, file_path: Path) -> ViewTransformation:
        """Analyze a view file for transformation."""
        with open(file_path) as f:
            content = f.read()
            
        # Parse the file
        tree = ast.parse(content)
        extractor = ViewLogicExtractor()
        extractor.visit(tree)
        
        # Create corresponding logic module name
        logic_file = self.logic_dir / f"{file_path.stem.lower()}_logic.py"
        
        # Generate new view code (GUI-only)
        view_code = self._generate_view_code(
            extractor.class_name,
            extractor.gui_methods,
            extractor.imports
        )
        
        # Generate logic code
        logic_code = self._generate_logic_code(
            extractor.class_name,
            extractor.logic_methods,
            extractor.imports
        )
        
        return ViewTransformation(
            view_file=str(file_path),
            logic_file=str(logic_file),
            original_code=content,
            view_code=view_code,
            logic_code=logic_code,
            imports_to_update=[],  # Will be filled during transformation
            description=f"Separate {file_path.stem} into GUI and logic components"
        )
        
    def _generate_view_code(self, class_name: str, gui_methods: List[ast.FunctionDef],
                          imports: List[ast.Import]) -> str:
        """Generate GUI-only view class code."""
        # Add imports
        code = "import toga\n"
        code += f"from .logic.{class_name.lower()}_logic import *\n\n"
        
        # Create class
        code += f"class {class_name}:\n"
        code += "    def __init__(self):\n"
        code += "        super().__init__()\n\n"
        
        # Add GUI methods
        for method in gui_methods:
            code += ast.unparse(method) + "\n\n"
            
        return code
        
    def _generate_logic_code(self, class_name: str, logic_methods: List[ast.FunctionDef],
                           imports: List[ast.Import]) -> str:
        """Generate logic module code."""
        # Add imports
        code = "from typing import Any, Dict, List, Optional\n\n"
        
        # Add logic functions
        for method in logic_methods:
            # Convert method to standalone function
            func_def = ast.FunctionDef(
                name=method.name,
                args=ast.arguments(
                    posonlyargs=[],
                    args=[arg for arg in method.args.args if arg.arg != 'self'],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[]
                ),
                body=method.body,
                decorator_list=[]
            )
            code += ast.unparse(func_def) + "\n\n"
            
        return code
        
    def migrate_view(self, transformation: ViewTransformation) -> None:
        """Apply the view transformation."""
        # Create logic directory if it doesn't exist
        self.logic_dir.mkdir(exist_ok=True)
        
        # Write new view file
        with open(transformation.view_file, 'w') as f:
            f.write(transformation.view_code)
            
        # Write logic file
        with open(transformation.logic_file, 'w') as f:
            f.write(transformation.logic_code)
            
    def update_imports(self, file_path: Path, old_to_new: Dict[str, str]) -> None:
        """Update imports using provided patterns."""
        with open(file_path) as f:
            source_code = f.read()
            
        context = CodemodContext()
        transformer = TogaImportUpdater(context, old_to_new)
        
        input_tree = cst.parse_module(source_code)
        output_tree = transformer.transform_module(input_tree)
        
        with open(file_path, 'w') as f:
            f.write(output_tree.code)
            
    def migrate_project(self) -> List[ViewTransformation]:
        """Migrate the entire Toga app project."""
        transformations = []
        
        # Find and transform all view files
        for view_file in self.find_view_files():
            transformation = self.analyze_view(view_file)
            self.migrate_view(transformation)
            transformations.append(transformation)
            
        return transformations
