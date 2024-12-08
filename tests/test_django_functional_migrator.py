"""Tests for Django functional migrator."""

import pytest
from pathlib import Path
from textwrap import dedent
from nadoo_migration_framework.frameworks.django_functional_migrator import (
    DjangoFunctionalMigrator,
    ClassToModuleTransformer,
    ModelToFunctionsTransformer,
    FunctionalTransformation,
)
from libcst.codemod import CodemodContext


@pytest.fixture
def temp_django_project(tmp_path):
    """Create a temporary Django project with OOP patterns."""
    project_dir = tmp_path / "django_project"
    project_dir.mkdir()

    # Create a views.py file with class-based views
    views_file = project_dir / "views.py"
    views_file.write_text(
        dedent(
            """
        from django.views import View
        from django.http import HttpResponse
        
        class UserView(View):
            template_name = 'user.html'
            
            def get(self, request, user_id):
                user = User.objects.get(id=user_id)
                return render(request, self.template_name, {'user': user})
                
            def post(self, request):
                data = request.POST
                user = User.objects.create(**data)
                return HttpResponse(status=201)
    """
        )
    )

    # Create a models.py file with Django models
    models_file = project_dir / "models.py"
    models_file.write_text(
        dedent(
            """
        from django.db import models
        
        class User(models.Model):
            name = models.CharField(max_length=100)
            email = models.EmailField(unique=True)
            created_at = models.DateTimeField(auto_now_add=True)
            
            def get_full_profile(self):
                return {
                    'name': self.name,
                    'email': self.email,
                    'created_at': self.created_at
                }
    """
        )
    )

    return project_dir


def test_functional_migrator_initialization(temp_django_project):
    """Test migrator initialization."""
    migrator = DjangoFunctionalMigrator(temp_django_project)
    assert migrator.project_dir == temp_django_project


def test_analyze_project(temp_django_project):
    """Test project analysis for transformable patterns."""
    migrator = DjangoFunctionalMigrator(temp_django_project)
    transformations = migrator.analyze_project()

    assert len(transformations) == 2
    assert any(t.transformation_type == "class_to_function" for t in transformations)
    assert any(t.transformation_type == "model_to_functions" for t in transformations)


def test_class_to_module_transformer():
    """Test transformation of class-based view to functional views."""
    source = dedent(
        """
        from django.views import View
        
        class UserView(View):
            template_name = 'user.html'
            
            def get(self, request, user_id):
                return render(request, self.template_name, {'user_id': user_id})
    """
    )

    context = CodemodContext()
    transformer = ClassToModuleTransformer(context)

    # Transform the code
    input_tree = cst.parse_module(source)
    output_tree = transformer.transform_module(input_tree)
    transformed_code = output_tree.code

    # Verify transformation
    assert "def get_view" in transformed_code
    assert "template_name = 'user.html'" in transformed_code
    assert "class UserView" not in transformed_code


def test_model_to_functions_transformer():
    """Test transformation of Django model to functional operations."""
    source = dedent(
        """
        from django.db import models
        
        class User(models.Model):
            name = models.CharField(max_length=100)
            email = models.EmailField(unique=True)
    """
    )

    context = CodemodContext()
    transformer = ModelToFunctionsTransformer(context)

    # Transform the code
    input_tree = cst.parse_module(source)
    output_tree = transformer.transform_module(input_tree)
    transformed_code = output_tree.code

    # Verify transformation
    assert "def create_user" in transformed_code
    assert "def get_user" in transformed_code
    assert "def update_user" in transformed_code
    assert "def delete_user" in transformed_code
    assert "def list_user" in transformed_code
    assert "class User" not in transformed_code


def test_complete_project_migration(temp_django_project):
    """Test complete project migration to functional patterns."""
    migrator = DjangoFunctionalMigrator(temp_django_project)
    transformations = migrator.migrate_project()

    # Verify transformations
    assert len(transformations) == 2

    # Check views.py transformation
    views_file = temp_django_project / "views.py"
    transformed_views = views_file.read_text()
    assert "def get_view" in transformed_views
    assert "def post_view" in transformed_views
    assert "class UserView" not in transformed_views

    # Check models.py transformation
    models_file = temp_django_project / "models.py"
    transformed_models = models_file.read_text()
    assert "def create_user" in transformed_models
    assert "def get_user" in transformed_models
    assert "class User" not in transformed_models


def test_transformation_error_handling(temp_django_project):
    """Test error handling during transformation."""
    # Create a file with invalid syntax
    invalid_file = temp_django_project / "invalid.py"
    invalid_file.write_text("class InvalidView(View: pass")  # Syntax error

    migrator = DjangoFunctionalMigrator(temp_django_project)
    transformations = migrator.migrate_project()

    # Verify that valid files were still transformed
    assert len(transformations) == 2  # Only views.py and models.py should be transformed
    assert all(t.file_path != str(invalid_file) for t in transformations)


def test_functional_transformation_dataclass():
    """Test FunctionalTransformation dataclass."""
    transformation = FunctionalTransformation(
        original_code="class TestView(View): pass",
        transformed_code="def test_view(): pass",
        file_path="/test/views.py",
        line_number=1,
        transformation_type="class_to_function",
        description="Transform TestView to function",
    )

    assert transformation.original_code == "class TestView(View): pass"
    assert transformation.transformed_code == "def test_view(): pass"
    assert transformation.file_path == "/test/views.py"
    assert transformation.line_number == 1
    assert transformation.transformation_type == "class_to_function"
    assert transformation.description == "Transform TestView to function"
