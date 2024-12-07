"""Template system for NADOO Migration Framework."""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import toml

class MigrationTemplate:
    """Base class for migration templates."""

    def __init__(self, name: str, description: str):
        """Initialize migration template.
        
        Args:
            name: Template name
            description: Template description
        """
        self.name = name
        self.description = description
        self.migrations: List[str] = []
        self.config: Dict[str, Any] = {}

    def add_migration(self, migration_class: str) -> None:
        """Add a migration to the template.
        
        Args:
            migration_class: Fully qualified migration class name
        """
        self.migrations.append(migration_class)

    def set_config(self, config: Dict[str, Any]) -> None:
        """Set template configuration.
        
        Args:
            config: Template configuration
        """
        self.config = config

class TemplateManager:
    """Manager for migration templates."""

    def __init__(self):
        """Initialize template manager."""
        self.templates: Dict[str, MigrationTemplate] = {}
        self._load_builtin_templates()

    def _load_builtin_templates(self) -> None:
        """Load built-in templates."""
        # Toga Single Window Template
        toga_single = MigrationTemplate(
            "toga-single",
            "Migration template for single-window Toga applications"
        )
        toga_single.add_migration("nadoo_migration_framework.migrations.CreateFunctionDirectoryMigration")
        toga_single.add_migration("nadoo_migration_framework.migrations.ExtractCurriedFunctionsMigration")
        toga_single.add_migration("nadoo_migration_framework.migrations.ExtractRegularFunctionsMigration")
        toga_single.add_migration("nadoo_migration_framework.migrations.ConsolidateImportsMigration")
        self.templates["toga-single"] = toga_single

        # Toga Multi Window Template
        toga_multi = MigrationTemplate(
            "toga-multi",
            "Migration template for multi-window Toga applications"
        )
        toga_multi.add_migration("nadoo_migration_framework.migrations.CreateFunctionDirectoryMigration")
        toga_multi.add_migration("nadoo_migration_framework.migrations.ExtractCurriedFunctionsMigration")
        toga_multi.add_migration("nadoo_migration_framework.migrations.ExtractRegularFunctionsMigration")
        toga_multi.add_migration("nadoo_migration_framework.migrations.ConsolidateImportsMigration")
        toga_multi.add_migration("nadoo_migration_framework.migrations.SplitWindowsMigration")
        self.templates["toga-multi"] = toga_multi

    def get_template(self, name: str) -> Optional[MigrationTemplate]:
        """Get a template by name.
        
        Args:
            name: Template name
            
        Returns:
            Optional[MigrationTemplate]: The template if found, None otherwise
        """
        return self.templates.get(name)

    def register_template(self, template: MigrationTemplate) -> None:
        """Register a new template.
        
        Args:
            template: Migration template to register
        """
        self.templates[template.name] = template

    def get_migrations_for_template(self, name: str) -> List[str]:
        """Get migrations for a template.
        
        Args:
            name: Template name
            
        Returns:
            List[str]: List of migration class names
        """
        template = self.get_template(name)
        return template.migrations if template else []

    def get_template_config(self, name: str) -> Dict[str, Any]:
        """Get configuration for a template.
        
        Args:
            name: Template name
            
        Returns:
            Dict[str, Any]: Template configuration
        """
        template = self.get_template(name)
        return template.config if template else {}
