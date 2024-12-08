"""Migration to convert to Briefcase structure."""

import os
import shutil
from pathlib import Path
from .base import Migration
from ..functions.project_structure_migrator import (
    ProjectStructure,
    get_app_name,
    normalize_app_name,
    create_briefcase_structure,
    update_imports,
)


class Migration0002BriefcaseStructure(Migration):
    """Migration to convert to Briefcase structure."""

    def __init__(
        self,
        project_path: str,
        target_structure: ProjectStructure = ProjectStructure.BRIEFCASE_UNDERSCORE,
    ):
        super().__init__(project_path)
        self.target_structure = target_structure

    @property
    def dependencies(self) -> list[str]:
        return ['Migration0001Initial']

    def apply(self) -> bool:
        """Apply the Briefcase structure migration."""
        if self.is_applied():
            return False

        # Get app name and normalize it
        app_name = get_app_name(self.project_path)
        normalized_name = normalize_app_name(app_name, self.target_structure)

        # Create new structure
        path_mapping = create_briefcase_structure(self.project_path, normalized_name)

        # Copy files and update imports
        src_path = os.path.join(self.project_path, 'src')
        if os.path.exists(src_path):
            for old_path, new_path in path_mapping.items():
                if os.path.exists(old_path):
                    if not os.path.exists(new_path):
                        shutil.copytree(old_path, new_path)

                    # Update imports in Python files
                    for root, _, files in os.walk(new_path):
                        for file in files:
                            if file.endswith('.py'):
                                file_path = os.path.join(root, file)
                                update_imports(
                                    file_path,
                                    app_name,
                                    ProjectStructure.LEGACY,
                                    self.target_structure,
                                )

            # Backup old structure
            backup_path = os.path.join(self.project_path, 'src.bak')
            shutil.move(src_path, backup_path)

        self._save_state(True, f"Migrated to {self.target_structure.value} structure")
        return True

    def rollback(self) -> bool:
        """Rollback the Briefcase structure migration."""
        if not self.is_applied():
            return False

        app_name = get_app_name(self.project_path)
        normalized_name = normalize_app_name(app_name, self.target_structure)

        # Remove Briefcase structure
        briefcase_path = os.path.join(self.project_path, normalized_name)
        if os.path.exists(briefcase_path):
            shutil.rmtree(briefcase_path)

        # Restore backup if it exists
        backup_path = os.path.join(self.project_path, 'src.bak')
        if os.path.exists(backup_path):
            src_path = os.path.join(self.project_path, 'src')
            if os.path.exists(src_path):
                shutil.rmtree(src_path)
            shutil.move(backup_path, src_path)

        self._save_state(False, f"Rolled back from {self.target_structure.value} structure")
        return True
