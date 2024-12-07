"""Migration to add Briefcase and Toga support to NADOO projects."""

import os
import toml
from pathlib import Path
from ..version import Version
from .base_migration import BaseMigration
from ..functions.project_structure_migrator import ProjectStructure

class AddBriefcaseTogaMigration(BaseMigration):
    """Migration to add Briefcase and Toga support."""
    
    def __init__(self):
        """Initialize the migration."""
        super().__init__(
            name="add_briefcase_toga",
            description="Adds Briefcase and Toga support to the project",
            version=Version.from_string("0.2.6")
        )

    def _update_pyproject_toml(self, project_path: str) -> None:
        """Update pyproject.toml with Briefcase and Toga configurations."""
        pyproject_path = os.path.join(project_path, "pyproject.toml")
        
        try:
            with open(pyproject_path, 'r') as f:
                config = toml.load(f)
        except FileNotFoundError:
            self.logger.error(f"pyproject.toml not found in {project_path}")
            return
        
        # Add Toga dependency if not present
        if 'tool' not in config:
            config['tool'] = {}
        if 'poetry' not in config['tool']:
            config['tool']['poetry'] = {}
        if 'dependencies' not in config['tool']['poetry']:
            config['tool']['poetry']['dependencies'] = {}
        
        dependencies = config['tool']['poetry']['dependencies']
        dependencies['toga'] = {'version': '>=0.4.0', 'platform': 'darwin', 'extras': ['cocoa']}
        
        # Add Briefcase configuration
        if 'briefcase' not in config['tool']:
            project_name = config['tool']['poetry']['name']
            formal_name = project_name.replace('-', ' ').title()
            
            config['tool']['briefcase'] = {
                'project_name': formal_name,
                'bundle': f"it.nadoo.{project_name.replace('-', '')}",
                'version': config['tool']['poetry'].get('version', '0.1.0'),
                'url': "https://nadoo.it",
                'author': config['tool']['poetry'].get('authors', ['NADOO IT Team <info@nadoo.it>'])[0],
                'author_email': "info@nadoo.it",
                'license': config['tool']['poetry'].get('license', 'MIT')
            }
            
            # Add app configuration
            app_name = project_name.replace('-', '_')
            config['tool']['briefcase']['app'] = {
                app_name: {
                    'formal_name': formal_name,
                    'description': config['tool']['poetry'].get('description', ''),
                    'icon': f"src/{app_name}/resources/{app_name}",
                    'sources': [f"src/{app_name}"],
                    'requires': ['toga>=0.4.0'],
                }
            }
            
            # Add platform-specific configurations
            platforms = {
                'macOS': {'toga-cocoa': '>=0.4.0', 'std-nslog': '>=1.0.0'},
                'linux': {'toga-gtk': '>=0.4.0'},
                'windows': {'toga-winforms': '>=0.4.0'},
                'iOS': {'toga-iOS': '>=0.4.0'},
                'android': {'toga-android': '>=0.4.0'}
            }
            
            for platform, requires in platforms.items():
                config['tool']['briefcase']['app'][app_name][platform] = {
                    'requires': [f"{pkg}{ver}" for pkg, ver in requires.items()]
                }
        
        # Save updated configuration
        with open(pyproject_path, 'w') as f:
            toml.dump(config, f)

    def _create_resources_dir(self, project_path: str) -> None:
        """Create resources directory for app icons."""
        project_name = Path(project_path).name.replace('-', '_')
        resources_path = os.path.join(project_path, 'src', project_name, 'resources')
        os.makedirs(resources_path, exist_ok=True)

    def migrate(self, project_path: str, dry_run: bool = False) -> bool:
        """Perform the migration."""
        try:
            if not dry_run:
                self._update_pyproject_toml(project_path)
                self._create_resources_dir(project_path)
            return True
        except Exception as e:
            self.logger.error(f"Failed to add Briefcase and Toga support: {str(e)}")
            return False

    def rollback(self, project_path: str) -> bool:
        """Rollback the migration."""
        try:
            pyproject_path = os.path.join(project_path, "pyproject.toml")
            with open(pyproject_path, 'r') as f:
                config = toml.load(f)
            
            # Remove Toga dependency
            if 'tool' in config and 'poetry' in config['tool'] and 'dependencies' in config['tool']['poetry']:
                if 'toga' in config['tool']['poetry']['dependencies']:
                    del config['tool']['poetry']['dependencies']['toga']
            
            # Remove Briefcase configuration
            if 'tool' in config and 'briefcase' in config['tool']:
                del config['tool']['briefcase']
            
            with open(pyproject_path, 'w') as f:
                toml.dump(config, f)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to rollback Briefcase and Toga support: {str(e)}")
            return False
