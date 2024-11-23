"""Flask framework migration handler."""

from pathlib import Path
from typing import Dict, List

from . import FrameworkMigrator

class FlaskMigrator(FrameworkMigrator):
    """Flask framework migrator."""
    
    def detect(self) -> bool:
        """Detect if this is a Flask project."""
        # Look for common Flask patterns
        app_py = self.project_dir / "app.py"
        wsgi_py = self.project_dir / "wsgi.py"
        requirements = self.project_dir / "requirements.txt"
        
        if requirements.exists():
            with open(requirements) as f:
                content = f.read()
                if "flask" in content.lower():
                    return True
        
        return app_py.exists() or wsgi_py.exists()
    
    def get_migration_steps(self) -> List[Dict]:
        """Get Flask-specific migration steps."""
        return [
            {
                "name": "Update Flask app",
                "description": "Update Flask app for NADOO compatibility",
                "action": "update_app"
            },
            {
                "name": "Add NADOO middleware",
                "description": "Add NADOO middleware for request tracking",
                "action": "add_middleware"
            },
            {
                "name": "Configure Flask logging",
                "description": "Configure Flask logging for NADOO",
                "action": "configure_logging"
            }
        ]
    
    def get_requirements(self) -> List[str]:
        """Get Flask-specific requirements."""
        return [
            "flask>=2.0.0",
            "flask-nadoo>=0.1.0",
            "flask-debugtoolbar>=0.13.0"
        ]
