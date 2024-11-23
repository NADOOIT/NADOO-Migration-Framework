"""Django project analyzer for detecting compatibility issues and needed migrations."""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass

@dataclass
class CompatibilityIssue:
    """Represents a compatibility issue found in the codebase."""
    file: str
    line_number: int
    issue_type: str
    message: str
    severity: str  # 'error', 'warning', or 'info'
    suggested_fix: Optional[str] = None

class DjangoAnalyzer:
    """Analyzes Django projects for compatibility issues and migration needs."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.issues: List[CompatibilityIssue] = []
        
    def analyze_project(self) -> List[CompatibilityIssue]:
        """Run all analysis checks on the project."""
        self._check_project_structure()
        self._analyze_settings()
        self._analyze_urls()
        self._analyze_models()
        self._analyze_views()
        self._analyze_templates()
        self._check_dependencies()
        return self.issues
        
    def _check_project_structure(self):
        """Check project structure and common files."""
        required_files = [
            'manage.py',
            'requirements.txt',
            'README.md',
        ]
        
        for file in required_files:
            if not (self.project_dir / file).exists():
                self.issues.append(CompatibilityIssue(
                    file=str(self.project_dir / file),
                    line_number=0,
                    issue_type='structure',
                    message=f'Missing required file: {file}',
                    severity='warning',
                    suggested_fix=f'Create {file} file'
                ))
    
    def _analyze_settings(self):
        """Analyze Django settings for compatibility issues."""
        settings_files = list(self.project_dir.rglob('settings*.py'))
        
        for settings_file in settings_files:
            with open(settings_file) as f:
                content = f.read()
                
            # Check for deprecated settings
            deprecated_settings = {
                'MIDDLEWARE_CLASSES': 'Use MIDDLEWARE instead',
                'TEMPLATE_DIRS': 'Use TEMPLATES setting instead',
                'TEMPLATE_CONTEXT_PROCESSORS': 'Use TEMPLATES["OPTIONS"]["context_processors"] instead',
            }
            
            for setting, fix in deprecated_settings.items():
                if setting in content:
                    self.issues.append(CompatibilityIssue(
                        file=str(settings_file),
                        line_number=content.count('\n', 0, content.index(setting)) + 1,
                        issue_type='deprecated_setting',
                        message=f'Deprecated setting found: {setting}',
                        severity='error',
                        suggested_fix=fix
                    ))
                    
            # Check security settings
            required_security_settings = {
                'SECURE_HSTS_SECONDS': 'Add SECURE_HSTS_SECONDS for improved security',
                'SECURE_SSL_REDIRECT': 'Add SECURE_SSL_REDIRECT for SSL',
                'SESSION_COOKIE_SECURE': 'Add SESSION_COOKIE_SECURE for secure cookies',
            }
            
            for setting, fix in required_security_settings.items():
                if setting not in content:
                    self.issues.append(CompatibilityIssue(
                        file=str(settings_file),
                        line_number=0,
                        issue_type='security_setting',
                        message=f'Missing security setting: {setting}',
                        severity='warning',
                        suggested_fix=fix
                    ))
    
    def _analyze_urls(self):
        """Analyze URL patterns for deprecated patterns."""
        urls_files = list(self.project_dir.rglob('urls.py'))
        
        for urls_file in urls_files:
            with open(urls_file) as f:
                content = f.read()
                
            # Check for old-style URL patterns
            if 'url(r\'^' in content:
                self.issues.append(CompatibilityIssue(
                    file=str(urls_file),
                    line_number=0,
                    issue_type='deprecated_urls',
                    message='Using deprecated url() function with regex patterns',
                    severity='warning',
                    suggested_fix='Use path() instead of url()'
                ))
    
    def _analyze_models(self):
        """Analyze models for deprecated features and best practices."""
        model_files = list(self.project_dir.rglob('models.py'))
        
        for model_file in model_files:
            with open(model_file) as f:
                content = f.read()
                try:
                    tree = ast.parse(content)
                except:
                    continue
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check for models without __str__ method
                    has_str = any(n.name == '__str__' for n in node.body if isinstance(n, ast.FunctionDef))
                    if not has_str:
                        self.issues.append(CompatibilityIssue(
                            file=str(model_file),
                            line_number=node.lineno,
                            issue_type='model_practice',
                            message=f'Model {node.name} missing __str__ method',
                            severity='info',
                            suggested_fix='Add __str__ method for better object representation'
                        ))
    
    def _analyze_views(self):
        """Analyze views for deprecated patterns and best practices."""
        view_files = list(self.project_dir.rglob('views.py'))
        
        for view_file in view_files:
            with open(view_file) as f:
                content = f.read()
                
            # Check for function-based views without decorators
            fbv_pattern = r'def\s+\w+\s*\([^)]*\):\s*(?!@)'
            for match in re.finditer(fbv_pattern, content):
                self.issues.append(CompatibilityIssue(
                    file=str(view_file),
                    line_number=content.count('\n', 0, match.start()) + 1,
                    issue_type='view_practice',
                    message='Function-based view without decorators',
                    severity='info',
                    suggested_fix='Consider using class-based views or add appropriate decorators'
                ))
    
    def _analyze_templates(self):
        """Analyze templates for deprecated tags and filters."""
        template_files = []
        for ext in ['.html', '.django', '.jinja']:
            template_files.extend(self.project_dir.rglob(f'*{ext}'))
        
        deprecated_tags = {
            '{% load staticfiles %}': 'Use {% load static %} instead',
            '{% load url from future %}': 'Remove this deprecated tag',
        }
        
        for template_file in template_files:
            with open(template_file) as f:
                content = f.read()
                
            for tag, fix in deprecated_tags.items():
                if tag in content:
                    self.issues.append(CompatibilityIssue(
                        file=str(template_file),
                        line_number=content.count('\n', 0, content.index(tag)) + 1,
                        issue_type='deprecated_template',
                        message=f'Deprecated template tag: {tag}',
                        severity='warning',
                        suggested_fix=fix
                    ))
    
    def _check_dependencies(self):
        """Check project dependencies for compatibility issues."""
        req_files = ['requirements.txt', 'pyproject.toml']
        dependencies = {}
        
        for req_file in req_files:
            req_path = self.project_dir / req_file
            if not req_path.exists():
                continue
                
            with open(req_path) as f:
                content = f.read()
                
            # Extract dependencies and versions
            if req_file == 'requirements.txt':
                for line in content.split('\n'):
                    if '==' in line:
                        package, version = line.split('==')
                        dependencies[package.strip()] = version.strip()
            elif req_file == 'pyproject.toml':
                try:
                    import toml
                    config = toml.loads(content)
                    deps = config.get('tool', {}).get('poetry', {}).get('dependencies', {})
                    for package, version in deps.items():
                        if isinstance(version, str):
                            dependencies[package] = version
                except:
                    pass
        
        # Check known compatibility issues
        compatibility_issues = {
            'django-filter': {
                '<23.0': 'Upgrade to django-filter>=23.0 for Django 5.0 compatibility',
            },
            'django-crispy-forms': {
                '<2.0': 'Upgrade to django-crispy-forms>=2.0 for Django 5.0 compatibility',
            },
            'djangorestframework': {
                '<3.14': 'Upgrade to djangorestframework>=3.14 for Django 5.0 compatibility',
            }
        }
        
        for package, versions in compatibility_issues.items():
            if package in dependencies:
                current_version = dependencies[package]
                for version_constraint, message in versions.items():
                    if self._version_matches_constraint(current_version, version_constraint):
                        self.issues.append(CompatibilityIssue(
                            file=str(self.project_dir / req_file),
                            line_number=0,
                            issue_type='dependency',
                            message=f'Incompatible package version: {package}=={current_version}',
                            severity='error',
                            suggested_fix=message
                        ))
    
    @staticmethod
    def _version_matches_constraint(version: str, constraint: str) -> bool:
        """Check if version matches the constraint."""
        import re
        from packaging import version as pkg_version
        
        version = re.search(r'[\d.]+', version).group()
        constraint_op = constraint[0]
        constraint_version = constraint[1:]
        
        v1 = pkg_version.parse(version)
        v2 = pkg_version.parse(constraint_version)
        
        if constraint_op == '<':
            return v1 < v2
        elif constraint_op == '>':
            return v1 > v2
        elif constraint_op == '<=':
            return v1 <= v2
        elif constraint_op == '>=':
            return v1 >= v2
        elif constraint_op == '==':
            return v1 == v2
        return False
