"""Django migration utilities."""

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class DjangoUtils:
    """Utility functions for Django migrations."""
    
    @staticmethod
    def backup_database(project_dir: Path, settings_module: str) -> bool:
        """Create a database backup."""
        backup_dir = project_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"db_backup_{timestamp}.json"
        
        try:
            # Use dumpdata to create a JSON backup
            subprocess.run([
                "python", "manage.py", "dumpdata",
                "--exclude", "auth.permission",
                "--exclude", "contenttypes",
                "--exclude", "sessions",
                "-o", str(backup_file),
                "--settings", settings_module
            ], cwd=project_dir, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def update_settings(project_dir: Path, settings_file: Path) -> bool:
        """Update Django settings for latest version."""
        if not settings_file.exists():
            return False
            
        with open(settings_file) as f:
            content = f.read()
            
        # Update middleware
        middleware_updates = {
            'django.middleware.security.SecurityMiddleware': 0,
            'django.contrib.sessions.middleware.SessionMiddleware': 1,
            'django.middleware.common.CommonMiddleware': 2,
            'django.middleware.csrf.CsrfViewMiddleware': 3,
            'django.contrib.auth.middleware.AuthenticationMiddleware': 4,
            'django.contrib.messages.middleware.MessageMiddleware': 5,
            'django.middleware.clickjacking.XFrameOptionsMiddleware': 6,
            'whitenoise.middleware.WhiteNoiseMiddleware': 7,
        }
        
        # Update installed apps
        required_apps = [
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'django.contrib.sites',
            'allauth',
            'allauth.account',
            'allauth.socialaccount',
            'crispy_forms',
            'crispy_bootstrap5',
            'django_filters',
            'django_tables2',
            'django_bootstrap5',
            'debug_toolbar',
        ]
        
        # Update templates
        template_config = {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [os.path.join(project_dir, 'templates')],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ]
            }
        }
        
        # Update static files
        static_config = {
            'STATIC_URL': '/static/',
            'STATIC_ROOT': os.path.join(project_dir, 'staticfiles'),
            'STATICFILES_DIRS': [os.path.join(project_dir, 'static')],
            'STATICFILES_STORAGE': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        }
        
        # Update content
        # TODO: Implement actual settings file update logic
        return True
    
    @staticmethod
    def update_urls(project_dir: Path, urls_file: Path) -> bool:
        """Update URL patterns to new style."""
        if not urls_file.exists():
            return False
            
        with open(urls_file) as f:
            content = f.read()
            
        # Update patterns from url() to path()
        content = re.sub(
            r'url\(r\'^(.+?)\'',
            lambda m: f"path('{m.group(1)}'",
            content
        )
        
        # Add static/media serving in debug mode
        debug_patterns = """
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
"""
        
        if debug_patterns not in content:
            content += f"\n{debug_patterns}\n"
            
        with open(urls_file, 'w') as f:
            f.write(content)
            
        return True
    
    @staticmethod
    def run_migrations(project_dir: Path, settings_module: str) -> bool:
        """Run database migrations."""
        try:
            # Make migrations
            subprocess.run([
                "python", "manage.py", "makemigrations",
                "--settings", settings_module
            ], cwd=project_dir, check=True)
            
            # Apply migrations
            subprocess.run([
                "python", "manage.py", "migrate",
                "--settings", settings_module
            ], cwd=project_dir, check=True)
            
            return True
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def collect_static(project_dir: Path, settings_module: str) -> bool:
        """Collect static files."""
        try:
            subprocess.run([
                "python", "manage.py", "collectstatic",
                "--noinput",
                "--settings", settings_module
            ], cwd=project_dir, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
