"""Module for migrating NADOO-Launchpad code to separate GUI and logic."""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
import libcst as cst
from libcst.codemod import CodemodContext, ContextAwareTransformer

@dataclass
class ElementTransformation:
    """Represents a transformation of a NADOO Element class."""
    element_file: str
    logic_file: str
    original_code: str
    element_code: str
    logic_code: str
    imports_to_update: List[str]
    description: str

class ElementLogicExtractor(ast.NodeVisitor):
    """Extracts logic methods from Element classes for separation."""
    
    def __init__(self):
        self.gui_methods: List[ast.FunctionDef] = []
        self.logic_methods: List[ast.FunctionDef] = []
        self.imports: List[ast.Import] = []
        self.class_name: Optional[str] = None
        
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition and collect methods."""
        if node.name.endswith('Element'):
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
        gui_prefixes = {'on_', 'handle_', 'create_', 'update_ui_', 'refresh_'}
        if any(node.name.startswith(prefix) for prefix in gui_prefixes):
            return True
            
        # Check method body for Toga usage
        toga_usage = False
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and 'toga' in child.id:
                toga_usage = True
                break
        return toga_usage

class NADOOImportUpdater(ContextAwareTransformer):
    """Updates imports using NADOO-Launchpad Watchdog patterns."""
    
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

class NADOOLaunchpadMigrator:
    """Main class for migrating NADOO-Launchpad code."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.functions_dir = project_dir / 'functions'
        self.classes_dir = project_dir / 'classes'
        
    def find_element_files(self) -> List[Path]:
        """Find all Element files in the classes directory."""
        return list(self.classes_dir.glob('*Element.py'))
        
    def analyze_element(self, file_path: Path) -> ElementTransformation:
        """Analyze an Element file for transformation."""
        with open(file_path) as f:
            content = f.read()
            
        # Parse the file
        tree = ast.parse(content)
        extractor = ElementLogicExtractor()
        extractor.visit(tree)
        
        # Create corresponding function module name
        logic_file = self.functions_dir / f"{file_path.stem.lower()}_logic.py"
        
        # Generate new element code (GUI-only)
        element_code = self._generate_element_code(
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
        
        return ElementTransformation(
            element_file=str(file_path),
            logic_file=str(logic_file),
            original_code=content,
            element_code=element_code,
            logic_code=logic_code,
            imports_to_update=[],  # Will be filled during transformation
            description=f"Separate {file_path.stem} into GUI and logic components"
        )
        
    def _generate_element_code(self, class_name: str, gui_methods: List[ast.FunctionDef],
                             imports: List[ast.Import]) -> str:
        """Generate GUI-only Element class code."""
        # Add imports
        code = "import toga\n"
        code += f"from functions.{class_name.lower()}_logic import *\n\n"
        
        # Create class
        code += f"class {class_name}:\n"
        code += "    def __init__(self):\n"
        code += "        self.box = toga.Box()\n\n"
        
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
        
    def migrate_element(self, transformation: ElementTransformation) -> None:
        """Apply the Element transformation."""
        # Create functions directory if it doesn't exist
        self.functions_dir.mkdir(exist_ok=True)
        
        # Write new element file
        with open(transformation.element_file, 'w') as f:
            f.write(transformation.element_code)
            
        # Write logic file
        with open(transformation.logic_file, 'w') as f:
            f.write(transformation.logic_code)
            
    def update_imports(self, file_path: Path, old_to_new: Dict[str, str]) -> None:
        """Update imports using NADOO-Launchpad Watchdog patterns."""
        with open(file_path) as f:
            source_code = f.read()
            
        context = CodemodContext()
        transformer = NADOOImportUpdater(context, old_to_new)
        
        input_tree = cst.parse_module(source_code)
        output_tree = transformer.transform_module(input_tree)
        
        with open(file_path, 'w') as f:
            f.write(output_tree.code)
            
    def migrate_project(self) -> List[ElementTransformation]:
        """Migrate the entire NADOO-Launchpad project."""
        transformations = []
        
        # Find and transform all Element files
        for element_file in self.find_element_files():
            transformation = self.analyze_element(element_file)
            self.migrate_element(transformation)
            transformations.append(transformation)
            
        return transformations
