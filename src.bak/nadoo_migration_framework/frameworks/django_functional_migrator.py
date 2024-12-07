"""Module for migrating traditional OOP Django code to functional patterns while preserving ORM."""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Set, Any
import libcst as cst
from libcst.codemod import CodemodContext, ContextAwareTransformer

@dataclass
class FunctionalTransformation:
    """Represents a transformation from OOP to functional code."""
    original_code: str
    transformed_code: str
    file_path: str
    line_number: int
    transformation_type: str
    description: str

class ClassToModuleTransformer(ContextAwareTransformer):
    """Transforms Django class-based views to functional views."""
    
    def __init__(self, context: CodemodContext):
        super().__init__(context)
        self.class_methods: Dict[str, List[cst.FunctionDef]] = {}
        self.class_attributes: Dict[str, List[cst.Assign]] = {}
        
    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Visit class definition and collect methods and attributes."""
        self.class_methods[node.name.value] = []
        self.class_attributes[node.name.value] = []
        
        for body_node in node.body.body:
            if isinstance(body_node, cst.FunctionDef):
                self.class_methods[node.name.value].append(body_node)
            elif isinstance(body_node, cst.Assign):
                self.class_attributes[node.name.value].append(body_node)
                
    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.Module:
        """Transform class-based view into functional views."""
        if not any(base.value for base in original_node.bases if 'View' in base.value):
            return updated_node
            
        functions = []
        
        # Transform class methods into standalone functions
        for method in self.class_methods[original_node.name.value]:
            if method.name.value in ('get', 'post', 'put', 'delete'):
                functions.append(self._transform_view_method(method))
                
        # Create module-level attributes from class attributes
        attributes = [
            self._transform_class_attribute(attr)
            for attr in self.class_attributes[original_node.name.value]
        ]
        
        return cst.Module(body=attributes + functions)
        
    def _transform_view_method(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Transform a class method into a standalone function."""
        # Remove 'self' parameter
        new_params = [
            param for param in method.params.params
            if param.name.value != 'self'
        ]
        
        # Update function name to include HTTP method
        new_name = f"{method.name.value}_view"
        
        return method.with_changes(
            name=cst.Name(new_name),
            params=method.params.with_changes(params=new_params)
        )
        
    def _transform_class_attribute(self, attr: cst.Assign) -> cst.Assign:
        """Transform class attribute into module-level constant."""
        return attr.with_changes(
            targets=[
                target.with_changes(
                    value=target.value.upper()
                ) for target in attr.targets
            ]
        )

class ModelToFunctionsTransformer(ContextAwareTransformer):
    """Adds functional patterns while preserving Django ORM models."""
    
    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.Module:
        """Add functional operations while keeping the model class."""
        if not any(base.value for base in original_node.bases if 'Model' in base.value):
            return updated_node
            
        model_name = original_node.name.value
        
        # Keep the original model class
        new_body = [updated_node]
        
        # Add functional operations
        new_body.extend([
            self._create_query_function(model_name),
            self._create_validation_function(model_name),
            self._create_transformation_function(model_name),
            self._create_business_logic_functions(model_name)
        ])
        
        return cst.Module(body=new_body)
        
    def _create_query_function(self, model_name: str) -> cst.FunctionDef:
        """Create a function for composable queries."""
        return cst.FunctionDef(
            name=cst.Name(f"query_{model_name.lower()}"),
            params=cst.Parameters([
                cst.Param(cst.Name("filters"), annotation=cst.Annotation(cst.Name("Dict"))),
                cst.Param(
                    cst.Name("select_related"),
                    cst.Name("None"),
                    annotation=cst.Annotation(cst.Name("Optional[List[str]]"))
                )
            ]),
            body=cst.IndentedBlock([
                cst.parse_statement("queryset = " + model_name + ".objects.all()"),
                cst.parse_statement("if filters: queryset = queryset.filter(**filters)"),
                cst.parse_statement("if select_related: queryset = queryset.select_related(*select_related)"),
                cst.Return(cst.Name("queryset"))
            ]),
            returns=cst.Annotation(cst.Name("QuerySet"))
        )
        
    def _create_validation_function(self, model_name: str) -> cst.FunctionDef:
        """Create a function for data validation."""
        return cst.FunctionDef(
            name=cst.Name(f"validate_{model_name.lower()}_data"),
            params=cst.Parameters([
                cst.Param(cst.Name("data"), annotation=cst.Annotation(cst.Name("Dict[str, Any]")))
            ]),
            body=cst.IndentedBlock([
                cst.parse_statement(f"instance = {model_name}(**data)"),
                cst.parse_statement("try:"),
                cst.IndentedBlock([
                    cst.parse_statement("instance.full_clean()"),
                    cst.Return(cst.Constant(value=True))
                ]),
                cst.parse_statement("except ValidationError:"),
                cst.IndentedBlock([
                    cst.Return(cst.Constant(value=False))
                ])
            ]),
            returns=cst.Annotation(cst.Name("bool"))
        )
        
    def _create_transformation_function(self, model_name: str) -> cst.FunctionDef:
        """Create a function for data transformation."""
        return cst.FunctionDef(
            name=cst.Name(f"to_{model_name.lower()}_dict"),
            params=cst.Parameters([
                cst.Param(cst.Name("instance"), annotation=cst.Annotation(cst.Name(model_name)))
            ]),
            body=cst.IndentedBlock([
                cst.Return(cst.Dict([
                    cst.DictElement(
                        cst.SimpleString("'id'"),
                        cst.Attribute(cst.Name("instance"), cst.Name("id"))
                    )
                ]))
            ]),
            returns=cst.Annotation(cst.Name("Dict"))
        )
        
    def _create_business_logic_functions(self, model_name: str) -> List[cst.FunctionDef]:
        """Create functions for business logic operations."""
        functions = []
        
        # Add a function for safe creation
        functions.append(
            cst.FunctionDef(
                name=cst.Name(f"create_{model_name.lower()}_safely"),
                params=cst.Parameters([
                    cst.Param(cst.Name("data"), annotation=cst.Annotation(cst.Name("Dict")))
                ]),
                body=cst.IndentedBlock([
                    cst.parse_statement(f"if not validate_{model_name.lower()}_data(data): return None"),
                    cst.parse_statement(f"instance = {model_name}.objects.create(**data)"),
                    cst.Return(cst.Name("instance"))
                ]),
                returns=cst.Annotation(cst.Name(f"Optional[{model_name}]"))
            )
        )
        
        return functions

class DjangoFunctionalMigrator:
    """Main class for adding functional patterns to Django code."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        
    def analyze_project(self) -> List[FunctionalTransformation]:
        """Analyze project for OOP patterns that can be enhanced."""
        transformations = []
        
        # Find all Python files
        python_files = list(self.project_dir.rglob("*.py"))
        
        for file_path in python_files:
            with open(file_path) as f:
                content = f.read()
                
            # Parse the file
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
                
            # Analyze classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check for class-based views
                    if any('View' in base.id for base in node.bases if hasattr(base, 'id')):
                        transformations.append(
                            FunctionalTransformation(
                                original_code=ast.get_source_segment(content, node),
                                transformed_code="",  # Will be filled during transformation
                                file_path=str(file_path),
                                line_number=node.lineno,
                                transformation_type="class_to_function",
                                description=f"Transform class-based view '{node.name}' to functional view"
                            )
                        )
                    # Check for models
                    elif any('Model' in base.id for base in node.bases if hasattr(base, 'id')):
                        transformations.append(
                            FunctionalTransformation(
                                original_code=ast.get_source_segment(content, node),
                                transformed_code="",
                                file_path=str(file_path),
                                line_number=node.lineno,
                                transformation_type="model_to_functions",
                                description=f"Add functional operations to model '{node.name}'"
                            )
                        )
                        
        return transformations
        
    def transform_code(self, transformation: FunctionalTransformation) -> str:
        """Transform OOP code to include functional patterns."""
        with open(transformation.file_path) as f:
            source_code = f.read()
            
        context = CodemodContext()
        
        if transformation.transformation_type == "class_to_function":
            transformer = ClassToModuleTransformer(context)
        elif transformation.transformation_type == "model_to_functions":
            transformer = ModelToFunctionsTransformer(context)
        else:
            return source_code
            
        try:
            input_tree = cst.parse_module(source_code)
            output_tree = transformer.transform_module(input_tree)
            return output_tree.code
        except Exception as e:
            print(f"Error transforming {transformation.file_path}: {e}")
            return source_code
            
    def migrate_project(self) -> List[FunctionalTransformation]:
        """Add functional patterns to the project while preserving Django's ORM."""
        transformations = self.analyze_project()
        
        for transformation in transformations:
            transformed_code = self.transform_code(transformation)
            transformation.transformed_code = transformed_code
            
        return transformations
