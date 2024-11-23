"""Tests for the Django fixer functionality."""

import os
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from nadoo_migration_framework.frameworks.django_fixer import DjangoFixer
from nadoo_migration_framework.frameworks.django_analyzer import CompatibilityIssue

@pytest.fixture
def temp_django_project():
    """Create a temporary Django project structure."""
    with TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir)
        
        # Create basic Django project structure
        (project_dir / "manage.py").touch()
        (project_dir / "myapp").mkdir()
        (project_dir / "myapp" / "__init__.py").touch()
        
        yield project_dir

def test_fix_deprecated_settings(temp_django_project):
    """Test fixing deprecated Django settings."""
    settings_content = """
MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
]

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)

TEMPLATE_CONTEXT_PROCESSORS = [
    'django.template.context_processors.debug',
]
"""
    
    settings_file = temp_django_project / "myapp" / "settings.py"
    with open(settings_file, "w") as f:
        f.write(settings_content)
    
    fixer = DjangoFixer(temp_django_project)
    issue = CompatibilityIssue(
        issue_type="deprecated_setting",
        message="MIDDLEWARE_CLASSES is deprecated",
        file=str(settings_file),
        line_number=2,
        severity="error",
        suggested_fix="Use MIDDLEWARE instead"
    )
    
    result = fixer._fix_deprecated_setting(issue)
    assert result is True
    
    with open(settings_file) as f:
        new_content = f.read()
    
    assert "MIDDLEWARE = [" in new_content
    assert "MIDDLEWARE_CLASSES = [" not in new_content
    assert 'TEMPLATES = [{\n    "BACKEND": "django.template.backends.django.DjangoTemplates",' in new_content

def test_fix_deprecated_urls(temp_django_project):
    """Test fixing deprecated URL patterns."""
    urls_content = """
from django.conf.urls import url
from myapp import views

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^about/$', views.about, name='about'),
]
"""
    
    urls_file = temp_django_project / "myapp" / "urls.py"
    with open(urls_file, "w") as f:
        f.write(urls_content)
    
    fixer = DjangoFixer(temp_django_project)
    issue = CompatibilityIssue(
        issue_type="deprecated_urls",
        message="url() is deprecated",
        file=str(urls_file),
        line_number=5,
        severity="warning",
        suggested_fix="Use path() instead"
    )
    
    result = fixer._fix_deprecated_urls(issue)
    assert result is True
    
    with open(urls_file) as f:
        new_content = f.read()
    
    assert "from django.urls import path" in new_content
    assert "path(''" in new_content
    assert "path('about/'" in new_content
    assert "url(r'^" not in new_content

def test_fix_deprecated_template(temp_django_project):
    """Test fixing deprecated template tags."""
    template_content = """
{% load staticfiles %}
{% load url from future %}

<img src="{% static 'img/logo.png' %}" />
"""
    
    template_file = temp_django_project / "myapp" / "templates" / "base.html"
    os.makedirs(template_file.parent)
    with open(template_file, "w") as f:
        f.write(template_content)
    
    fixer = DjangoFixer(temp_django_project)
    issue = CompatibilityIssue(
        issue_type="deprecated_template",
        message="staticfiles tag is deprecated",
        file=str(template_file),
        line_number=2,
        severity="warning",
        suggested_fix="Use static tag instead"
    )
    
    result = fixer._fix_deprecated_template(issue)
    assert result is True
    
    with open(template_file) as f:
        new_content = f.read()
    
    assert "{% load static %}" in new_content
    assert "{% load staticfiles %}" not in new_content
    assert "{% load url from future %}" not in new_content

def test_fix_security_settings(temp_django_project):
    """Test adding security settings."""
    settings_content = """
DEBUG = False
ALLOWED_HOSTS = ['example.com']
"""
    
    settings_file = temp_django_project / "myapp" / "settings.py"
    with open(settings_file, "w") as f:
        f.write(settings_content)
    
    fixer = DjangoFixer(temp_django_project)
    issue = CompatibilityIssue(
        issue_type="security_setting",
        message="Missing security settings",
        file=str(settings_file),
        line_number=1,
        severity="warning",
        suggested_fix="Add recommended security settings"
    )
    
    result = fixer._fix_security_setting(issue)
    assert result is True
    
    with open(settings_file) as f:
        new_content = f.read()
    
    assert "SECURE_HSTS_SECONDS = 31536000" in new_content
    assert "SECURE_SSL_REDIRECT = True" in new_content
    assert "SESSION_COOKIE_SECURE = True" in new_content
    assert "CSRF_COOKIE_SECURE = True" in new_content
    assert "SECURE_BROWSER_XSS_FILTER = True" in new_content

def test_fix_model_practice(temp_django_project):
    """Test fixing model best practices."""
    model_content = """
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
"""
    
    model_file = temp_django_project / "myapp" / "models.py"
    with open(model_file, "w") as f:
        f.write(model_content)
    
    fixer = DjangoFixer(temp_django_project)
    issue = CompatibilityIssue(
        issue_type="model_practice",
        message="Model User missing __str__ method",
        file=str(model_file),
        line_number=3,
        severity="info",
        suggested_fix="Add __str__ method"
    )
    
    result = fixer._fix_model_practice(issue)
    assert result is True
    
    with open(model_file) as f:
        new_content = f.read()
    
    assert "def __str__(self):" in new_content
    assert 'return f"{self.__class__.__name__}({self.id})"' in new_content

def test_apply_fixes(temp_django_project):
    """Test applying multiple fixes at once."""
    settings_file = temp_django_project / "myapp" / "settings.py"
    urls_file = temp_django_project / "myapp" / "urls.py"
    
    with open(settings_file, "w") as f:
        f.write("MIDDLEWARE_CLASSES = []")
    
    with open(urls_file, "w") as f:
        f.write("from django.conf.urls import url\n\nurlpatterns = [url(r'^$', views.home)]")
    
    issues = [
        CompatibilityIssue(
            issue_type="deprecated_setting",
            message="MIDDLEWARE_CLASSES is deprecated",
            file=str(settings_file),
            line_number=1,
            severity="error",
            suggested_fix="Use MIDDLEWARE instead"
        ),
        CompatibilityIssue(
            issue_type="deprecated_urls",
            message="url() is deprecated",
            file=str(urls_file),
            line_number=3,
            severity="warning",
            suggested_fix="Use path() instead"
        )
    ]
    
    fixer = DjangoFixer(temp_django_project)
    results = fixer.apply_fixes(issues)
    
    assert len(results) == 2
    assert all(results.values())
    
    with open(settings_file) as f:
        settings_content = f.read()
    assert "MIDDLEWARE = [" in settings_content
    
    with open(urls_file) as f:
        urls_content = f.read()
    assert "from django.urls import path" in urls_content
