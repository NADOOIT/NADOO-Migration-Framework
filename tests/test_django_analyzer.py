"""Tests for Django project analyzer."""

import os
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from nadoo_migration_framework.frameworks.django_analyzer import DjangoAnalyzer, CompatibilityIssue

@pytest.fixture
def temp_django_project():
    """Create a temporary Django project for testing."""
    with TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir)
        
        # Create basic project structure
        (project_dir / 'manage.py').touch()
        (project_dir / 'requirements.txt').write_text('Django==4.2.0\ndjango-filter==21.1')
        (project_dir / 'README.md').touch()
        
        # Create settings with some issues
        settings_content = """
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
]

MIDDLEWARE_CLASSES = [  # Deprecated
    'django.middleware.common.CommonMiddleware',
]

TEMPLATE_DIRS = [  # Deprecated
    'templates',
]
"""
        (project_dir / 'config').mkdir()
        (project_dir / 'config' / 'settings.py').write_text(settings_content)
        
        # Create URLs with old patterns
        urls_content = """
from django.conf.urls import url

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api/', include('api.urls')),
]
"""
        (project_dir / 'config' / 'urls.py').write_text(urls_content)
        
        # Create models with missing __str__
        models_content = """
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
    # Missing __str__ method
"""
        (project_dir / 'app').mkdir()
        (project_dir / 'app' / 'models.py').write_text(models_content)
        
        # Create views with function-based view
        views_content = """
from django.shortcuts import render

def home(request):  # No decorator
    return render(request, 'home.html')
"""
        (project_dir / 'app' / 'views.py').write_text(views_content)
        
        # Create template with deprecated tag
        templates_dir = project_dir / 'templates'
        templates_dir.mkdir()
        template_content = """
{% load staticfiles %}
<!DOCTYPE html>
<html>
<body>
    <h1>Hello</h1>
</body>
</html>
"""
        (templates_dir / 'base.html').write_text(template_content)
        
        yield project_dir

def test_project_structure(temp_django_project):
    """Test project structure analysis."""
    analyzer = DjangoAnalyzer(temp_django_project)
    issues = analyzer.analyze_project()
    
    # Should not find structure issues as we created all required files
    structure_issues = [i for i in issues if i.issue_type == 'structure']
    assert len(structure_issues) == 0

def test_deprecated_settings(temp_django_project):
    """Test detection of deprecated settings."""
    analyzer = DjangoAnalyzer(temp_django_project)
    issues = analyzer.analyze_project()
    
    # Should find MIDDLEWARE_CLASSES and TEMPLATE_DIRS
    settings_issues = [i for i in issues if i.issue_type == 'deprecated_setting']
    assert len(settings_issues) == 2
    assert any('MIDDLEWARE_CLASSES' in i.message for i in settings_issues)
    assert any('TEMPLATE_DIRS' in i.message for i in settings_issues)

def test_url_patterns(temp_django_project):
    """Test detection of old-style URL patterns."""
    analyzer = DjangoAnalyzer(temp_django_project)
    issues = analyzer.analyze_project()
    
    url_issues = [i for i in issues if i.issue_type == 'deprecated_urls']
    assert len(url_issues) == 1
    assert 'deprecated url() function' in url_issues[0].message

def test_model_practices(temp_django_project):
    """Test detection of model best practices."""
    analyzer = DjangoAnalyzer(temp_django_project)
    issues = analyzer.analyze_project()
    
    model_issues = [i for i in issues if i.issue_type == 'model_practice']
    assert len(model_issues) == 1
    assert 'missing __str__ method' in model_issues[0].message

def test_view_practices(temp_django_project):
    """Test detection of view best practices."""
    analyzer = DjangoAnalyzer(temp_django_project)
    issues = analyzer.analyze_project()
    
    view_issues = [i for i in issues if i.issue_type == 'view_practice']
    assert len(view_issues) == 1
    assert 'Function-based view without decorators' in view_issues[0].message

def test_template_issues(temp_django_project):
    """Test detection of template issues."""
    analyzer = DjangoAnalyzer(temp_django_project)
    issues = analyzer.analyze_project()
    
    template_issues = [i for i in issues if i.issue_type == 'deprecated_template']
    assert len(template_issues) == 1
    assert 'load staticfiles' in template_issues[0].message

def test_dependency_issues(temp_django_project):
    """Test detection of dependency compatibility issues."""
    analyzer = DjangoAnalyzer(temp_django_project)
    issues = analyzer.analyze_project()
    
    dependency_issues = [i for i in issues if i.issue_type == 'dependency']
    assert len(dependency_issues) == 1
    assert 'django-filter' in dependency_issues[0].message
    assert '23.0' in dependency_issues[0].suggested_fix

def test_security_settings(temp_django_project):
    """Test detection of missing security settings."""
    analyzer = DjangoAnalyzer(temp_django_project)
    issues = analyzer.analyze_project()
    
    security_issues = [i for i in issues if i.issue_type == 'security_setting']
    assert len(security_issues) > 0
    assert any('SECURE_SSL_REDIRECT' in i.message for i in security_issues)
