"""Django code fixer for automatically applying common fixes."""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional
from .django_analyzer import CompatibilityIssue

class DjangoFixer:
    """Utility class for automatically fixing common Django issues."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
    
    def apply_fixes(self, issues: List[CompatibilityIssue]) -> Dict[str, bool]:
        """Apply fixes for the given issues."""
        results = {}
        
        for issue in issues:
            if issue.suggested_fix:
                if issue.issue_type == 'deprecated_setting':
                    results[issue.file] = self._fix_deprecated_setting(issue)
                elif issue.issue_type == 'deprecated_urls':
                    results[issue.file] = self._fix_deprecated_urls(issue)
                elif issue.issue_type == 'deprecated_template':
                    results[issue.file] = self._fix_deprecated_template(issue)
                elif issue.issue_type == 'security_setting':
                    results[issue.file] = self._fix_security_setting(issue)
                elif issue.issue_type == 'model_practice':
                    results[issue.file] = self._fix_model_practice(issue)
        
        return results
    
    def _fix_deprecated_setting(self, issue: CompatibilityIssue) -> bool:
        """Fix deprecated Django settings."""
        try:
            with open(issue.file) as f:
                content = f.read()
            
            # Common setting replacements
            replacements = {
                'MIDDLEWARE_CLASSES': ('MIDDLEWARE_CLASSES = [', 'MIDDLEWARE = ['),
                'TEMPLATE_DIRS': (
                    'TEMPLATE_DIRS',
                    'TEMPLATES = [{\n    "BACKEND": "django.template.backends.django.DjangoTemplates",\n'
                    '    "DIRS": ['
                ),
                'TEMPLATE_CONTEXT_PROCESSORS': (
                    'TEMPLATE_CONTEXT_PROCESSORS',
                    '"context_processors": ['
                )
            }
            
            for old, (old_pattern, new_pattern) in replacements.items():
                if old in issue.message:
                    content = content.replace(old_pattern, new_pattern)
                    
            with open(issue.file, 'w') as f:
                f.write(content)
                
            return True
        except Exception:
            return False
    
    def _fix_deprecated_urls(self, issue: CompatibilityIssue) -> bool:
        """Fix deprecated URL patterns."""
        try:
            with open(issue.file) as f:
                content = f.read()
            
            # Update imports
            content = content.replace(
                'from django.conf.urls import url',
                'from django.urls import path'
            )
            
            # Update url patterns
            content = re.sub(
                r'url\(r\'^(.+?)\'',
                lambda m: f"path('{m.group(1)}'",
                content
            )
            
            with open(issue.file, 'w') as f:
                f.write(content)
                
            return True
        except Exception:
            return False
    
    def _fix_deprecated_template(self, issue: CompatibilityIssue) -> bool:
        """Fix deprecated template tags."""
        try:
            with open(issue.file) as f:
                content = f.read()
            
            # Common template tag replacements
            replacements = {
                '{% load staticfiles %}': '{% load static %}',
                '{% load url from future %}': '',  # Remove deprecated tag
            }
            
            for old, new in replacements.items():
                content = content.replace(old, new)
                
            with open(issue.file, 'w') as f:
                f.write(content)
                
            return True
        except Exception:
            return False
    
    def _fix_security_setting(self, issue: CompatibilityIssue) -> bool:
        """Add recommended security settings."""
        try:
            with open(issue.file) as f:
                content = f.read()
            
            # Common security settings
            security_settings = {
                'SECURE_HSTS_SECONDS': 'SECURE_HSTS_SECONDS = 31536000  # 1 year',
                'SECURE_SSL_REDIRECT': 'SECURE_SSL_REDIRECT = True',
                'SESSION_COOKIE_SECURE': 'SESSION_COOKIE_SECURE = True',
                'CSRF_COOKIE_SECURE': 'CSRF_COOKIE_SECURE = True',
                'SECURE_BROWSER_XSS_FILTER': 'SECURE_BROWSER_XSS_FILTER = True',
            }
            
            # Add any missing security settings
            for setting, value in security_settings.items():
                if setting not in content:
                    content += f'\n\n# Security setting added by NADOO Migration Framework\n{value}'
                    
            with open(issue.file, 'w') as f:
                f.write(content)
                
            return True
        except Exception:
            return False
    
    def _fix_model_practice(self, issue: CompatibilityIssue) -> bool:
        """Fix model best practices."""
        try:
            with open(issue.file) as f:
                content = f.read()
                tree = ast.parse(content)
            
            # Add __str__ method to models
            if 'missing __str__ method' in issue.message:
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Find class name from issue message
                        class_name = re.search(r'Model (\w+) missing', issue.message)
                        if class_name and class_name.group(1) == node.name:
                            # Add __str__ method
                            str_method = """
    def __str__(self):
        return f"{self.__class__.__name__}({self.id})"
"""
                            # Find the last line of the class
                            class_end = node.end_lineno
                            lines = content.split('\n')
                            lines.insert(class_end - 1, str_method)
                            content = '\n'.join(lines)
                            
                            with open(issue.file, 'w') as f:
                                f.write(content)
                            return True
                            
            return False
        except Exception:
            return False
