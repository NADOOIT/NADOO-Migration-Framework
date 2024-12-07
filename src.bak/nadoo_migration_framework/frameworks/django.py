"""Django framework migration handler specifically for NADOO-IT."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import toml
import re
import os
from packaging import version

from . import FrameworkMigrator
from .django_utils import DjangoUtils
from .django_analyzer import DjangoAnalyzer, CompatibilityIssue
from .django_functional_migrator import DjangoFunctionalMigrator

class DjangoMigrator(FrameworkMigrator):
    """Django framework migrator for NADOO-IT."""
    
    # Version-specific changes that need to be handled
    VERSION_CHANGES = {
        "2.0": {
            "url_changes": True,  # url() to path()
            "middleware_changes": True,  # MIDDLEWARE_CLASSES to MIDDLEWARE
            "template_changes": False
        },
        "3.0": {
            "url_changes": True,
            "template_changes": True,  # New template tag syntax
            "python_version": "3.6"
        },
        "4.0": {
            "url_changes": True,
            "template_changes": True,
            "python_version": "3.8",
            "async_changes": True  # Async views support
        },
        "5.0": {
            "url_changes": True,
            "template_changes": True,
            "python_version": "3.10",
            "async_changes": True,
            "db_constraints": True  # New database constraints
        }
    }
    
    def __init__(self, project_dir: Path):
        super().__init__(project_dir)
        self.current_django_version = None
        self.target_django_version = "5.0.0"  # Latest stable Django version
        self.settings_module = self._find_settings_module()
        self.settings_file = self._find_settings_file()
        self.urls_file = self._find_urls_file()
        self.templates_dir = self._find_templates_dir()
        self.static_dir = self._find_static_dir()
        self.analyzer = DjangoAnalyzer(project_dir)
        self.functional_migrator = DjangoFunctionalMigrator(project_dir)
        
    def _find_settings_module(self) -> str:
        """Find the Django settings module."""
        manage_py = self.project_dir / "manage.py"
        if not manage_py.exists():
            return "config.settings"
            
        with open(manage_py) as f:
            content = f.read()
            match = re.search(r'os\.environ\.setdefault\(["\']DJANGO_SETTINGS_MODULE["\'],\s*["\'](.+?)["\']', content)
            if match:
                return match.group(1)
        return "config.settings"
        
    def _find_settings_file(self) -> Optional[Path]:
        """Find the Django settings file."""
        parts = self.settings_module.split('.')
        settings_path = self.project_dir.joinpath(*parts[:-1]) / f"{parts[-1]}.py"
        if settings_path.exists():
            return settings_path
            
        # Try common locations
        common_locations = [
            self.project_dir / "config" / "settings.py",
            self.project_dir / parts[-2] / "settings.py" if len(parts) > 1 else None,
            self.project_dir / "settings.py"
        ]
        
        for loc in common_locations:
            if loc and loc.exists():
                return loc
        return None
        
    def _find_urls_file(self) -> Optional[Path]:
        """Find the Django URLs file."""
        settings_dir = self.settings_file.parent if self.settings_file else None
        if settings_dir:
            urls_file = settings_dir / "urls.py"
            if urls_file.exists():
                return urls_file
                
        # Try common locations
        common_locations = [
            self.project_dir / "config" / "urls.py",
            self.project_dir / "urls.py"
        ]
        
        for loc in common_locations:
            if loc.exists():
                return loc
        return None

    def _find_templates_dir(self) -> Optional[Path]:
        """Find the Django templates directory."""
        common_locations = [
            self.project_dir / "templates",
            self.settings_file.parent / "templates" if self.settings_file else None,
            self.project_dir / "src" / "templates",
        ]
        
        for loc in common_locations:
            if loc and loc.exists() and loc.is_dir():
                return loc
        return None

    def _find_static_dir(self) -> Optional[Path]:
        """Find the Django static files directory."""
        common_locations = [
            self.project_dir / "static",
            self.settings_file.parent / "static" if self.settings_file else None,
            self.project_dir / "src" / "static",
        ]
        
        for loc in common_locations:
            if loc and loc.exists() and loc.is_dir():
                return loc
        return None
    
    def detect(self) -> bool:
        """Detect if this is a Django project and get current version."""
        manage_py = self.project_dir / "manage.py"
        requirements = self.project_dir / "requirements.txt"
        pyproject = self.project_dir / "pyproject.toml"
        
        if not manage_py.exists():
            return False
            
        # Try to detect Django version
        if pyproject.exists():
            with open(pyproject) as f:
                try:
                    config = toml.load(f)
                    deps = config.get("tool", {}).get("poetry", {}).get("dependencies", {})
                    django_dep = deps.get("django", "")
                    if django_dep:
                        version_match = re.search(r'[\d.]+', django_dep)
                        if version_match:
                            self.current_django_version = version_match.group()
                except Exception:
                    pass
                    
        if not self.current_django_version and requirements.exists():
            with open(requirements) as f:
                for line in f:
                    if line.lower().startswith('django'):
                        version_match = re.search(r'[\d.]+', line)
                        if version_match:
                            self.current_django_version = version_match.group()
                            break
        
        return True

    def _get_required_changes(self) -> Dict[str, bool]:
        """Determine required changes based on version differences."""
        if not self.current_django_version:
            return {k: True for k in self.VERSION_CHANGES["5.0"].keys()}
            
        changes = {}
        current_ver = version.parse(self.current_django_version)
        target_ver = version.parse(self.target_django_version)
        
        for ver, ver_changes in self.VERSION_CHANGES.items():
            if current_ver < version.parse(ver) <= target_ver:
                for change_type, needed in ver_changes.items():
                    if needed:
                        changes[change_type] = True
                        
        return changes
    
    def backup_database(self) -> bool:
        """Create a backup of the database."""
        return DjangoUtils.backup_database(self.project_dir, self.settings_module)
        
    def upgrade_django(self) -> bool:
        """Upgrade Django version."""
        return DjangoUtils.upgrade_django(self.project_dir, self.target_django_version)
        
    def update_imports(self) -> bool:
        """Update deprecated imports and patterns."""
        return DjangoUtils.update_imports(self.project_dir)
        
    def update_settings(self) -> bool:
        """Update Django settings."""
        if not self.settings_file:
            return False
        return DjangoUtils.update_settings(self.project_dir, self.settings_file)
        
    def run_migrations(self) -> bool:
        """Run database migrations."""
        return DjangoUtils.run_migrations(self.project_dir, self.settings_module)
        
    def update_urls(self) -> bool:
        """Update URL patterns."""
        if not self.urls_file:
            return False
        return DjangoUtils.update_urls(self.project_dir, self.urls_file)
        
    def update_static(self) -> bool:
        """Update static files handling."""
        if not self.static_dir:
            return False
        return DjangoUtils.update_static(self.project_dir, self.static_dir, self.settings_module)

    def update_templates(self) -> bool:
        """Update template files for compatibility."""
        if not self.templates_dir:
            return False
        return DjangoUtils.update_templates(self.project_dir, self.templates_dir)
        
    def update_to_functional(self) -> bool:
        """Transform OOP code to functional patterns."""
        try:
            transformations = self.functional_migrator.migrate_project()
            for transformation in transformations:
                if transformation.transformed_code:
                    with open(transformation.file_path, 'w') as f:
                        f.write(transformation.transformed_code)
            return True
        except Exception as e:
            print(f"Error during functional transformation: {e}")
            return False
        
    def get_migration_steps(self) -> List[Dict]:
        """Get Django-specific migration steps for NADOO-IT."""
        steps = []
        
        # Analyze project first
        issues = self.analyzer.analyze_project()
        required_changes = self._get_required_changes()
        
        # Add steps based on analysis
        if any(i.issue_type == 'dependency' for i in issues):
            steps.append({
                "name": "Update dependencies",
                "description": "Update project dependencies to compatible versions",
                "action": "update_dependencies",
                "severity": "error",
                "issues": [i for i in issues if i.issue_type == 'dependency']
            })
            
        if any(i.issue_type == 'deprecated_setting' for i in issues):
            steps.append({
                "name": "Update deprecated settings",
                "description": "Update deprecated Django settings",
                "action": "update_settings",
                "severity": "error",
                "issues": [i for i in issues if i.issue_type == 'deprecated_setting']
            })
            
        if required_changes.get("url_changes") or any(i.issue_type == 'deprecated_urls' for i in issues):
            steps.append({
                "name": "Update URL patterns",
                "description": "Update deprecated URL patterns to path()",
                "action": "update_urls",
                "severity": "error",
                "issues": [i for i in issues if i.issue_type == 'deprecated_urls']
            })
            
        if required_changes.get("template_changes") or any(i.issue_type == 'deprecated_template' for i in issues):
            steps.append({
                "name": "Update templates",
                "description": "Update deprecated template tags and syntax",
                "action": "update_templates",
                "severity": "warning",
                "issues": [i for i in issues if i.issue_type == 'deprecated_template']
            })
            
        if any(i.issue_type == 'security_setting' for i in issues):
            steps.append({
                "name": "Update security settings",
                "description": "Add recommended security settings",
                "action": "update_security",
                "severity": "warning",
                "issues": [i for i in issues if i.issue_type == 'security_setting']
            })

        if required_changes.get("async_changes"):
            steps.append({
                "name": "Update async support",
                "description": "Add async view support and middleware",
                "action": "update_async",
                "severity": "info",
                "issues": []
            })

        if required_changes.get("db_constraints"):
            steps.append({
                "name": "Update database constraints",
                "description": "Update database constraint definitions",
                "action": "update_db_constraints",
                "severity": "warning",
                "issues": []
            })

        # Add functional transformation step
        steps.append({
            "name": "Transform to functional patterns",
            "description": "Transform OOP code to functional patterns",
            "action": "update_to_functional",
            "severity": "info",
            "issues": []
        })
            
        # Add version upgrade steps if needed
        if self.current_django_version and version.parse(self.current_django_version) < version.parse(self.target_django_version):
            steps.extend([
                {
                    "name": "Backup database",
                    "description": "Create database backup before migration",
                    "action": "backup_database",
                    "severity": "info"
                },
                {
                    "name": "Update Django version",
                    "description": f"Upgrade Django from {self.current_django_version} to {self.target_django_version}",
                    "action": "upgrade_django",
                    "severity": "error"
                }
            ])
            
        # Always run migrations last
        steps.append({
            "name": "Database migrations",
            "description": "Run and verify all database migrations",
            "action": "run_migrations",
            "severity": "error"
        })
        
        return steps

    def get_requirements(self) -> List[str]:
        """Get Django-specific requirements for NADOO-IT."""
        requirements = [
            f"django>={self.target_django_version}",
            "django-allauth>=0.58.2",  # For authentication
            "django-crispy-forms>=2.1",  # For forms
            "crispy-bootstrap5>=2023.10",  # Bootstrap 5 template pack
            "django-debug-toolbar>=4.2.0",  # For debugging
            "django-filter>=23.4",  # For filtering
            "django-tables2>=2.6.0",  # For tables
            "django-bootstrap5>=23.3",  # Bootstrap 5 integration
            "whitenoise>=6.6.0",  # Static files serving
            "gunicorn>=21.2.0"  # Production server
        ]

        # Add version-specific requirements
        required_changes = self._get_required_changes()
        if required_changes.get("async_changes"):
            requirements.extend([
                "asgiref>=3.7.2",  # For async support
                "channels>=4.0.0",  # For WebSocket support
            ])

        if required_changes.get("db_constraints"):
            requirements.extend([
                "psycopg>=3.1.12",  # For PostgreSQL support
            ])

        return requirements
