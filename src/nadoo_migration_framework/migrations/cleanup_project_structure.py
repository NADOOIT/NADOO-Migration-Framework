"""Migration to clean up project structure."""

import os
import shutil
from pathlib import Path
from typing import List, Set


class CleanupProjectStructureMigration:
    """Migration to clean up project structure."""

    def __init__(self):
        """Initialize migration."""
        self.old_files: Set[Path] = set()
        self.new_files: Set[Path] = set()
        self.rollback_operations: List[tuple] = []

    def migrate(self, project_path: str) -> bool:
        """Migrate project structure.

        Args:
            project_path: Path to project root.

        Returns:
            bool: True if migration succeeded, False otherwise.
        """
        try:
            project_path = Path(project_path)
            self._move_existing_code(project_path)
            self._update_imports(project_path)
            self._cleanup_clutter(project_path)
            return True
        except Exception as e:
            print(f"Migration failed: {e}")
            self.rollback(str(project_path))
            return False

    def _move_existing_code(self, project_path: Path):
        """Move existing code to new structure.

        Args:
            project_path: Path to project root.
        """
        old_src = project_path / "src"
        project_name = project_path.name.replace('-', '_')
        new_src = project_path / "src" / project_name

        # Move files from old structure to new structure
        for old_path in old_src.rglob("*"):
            # Skip .github directory
            if ".github" in old_path.parts:
                continue

            if old_path.is_file() and not str(old_path).startswith(str(new_src)):
                relative_path = old_path.relative_to(old_src)
                new_path = new_src / relative_path

                # Skip if file already exists in new structure
                if new_path.exists():
                    continue

                # Create parent directories if they don't exist
                new_path.parent.mkdir(parents=True, exist_ok=True)

                # Move file
                shutil.move(str(old_path), str(new_path))
                self.old_files.add(old_path)
                self.new_files.add(new_path)
                self.rollback_operations.append(("move", new_path, old_path))

    def _update_imports(self, project_path: Path):
        """Update import statements to reflect new project structure.

        Args:
            project_path: Path to project root.
        """
        project_name = project_path.name.replace('-', '_')
        new_src = project_path / "src" / project_name

        for file_path in new_src.rglob("*.py"):
            with file_path.open("r") as file:
                content = file.read()

            # Replace old import paths with new ones
            content = content.replace("from nadoo_migration_framework.", f"from {project_name}.")

            with file_path.open("w") as file:
                file.write(content)

    def _cleanup_clutter(self, project_path: Path):
        """Clean up unnecessary files and directories.

        Args:
            project_path: Path to project root.
        """
        clutter_files = [".DS_Store", ".coverage"]
        clutter_dirs = ["build", "dist", ".pytest_cache"]

        # Remove clutter files
        for file_name in clutter_files:
            file_path = project_path / file_name
            if file_path.exists():
                file_path.unlink()
                self.rollback_operations.append(("unlink", file_path, None))

        # Remove clutter directories
        for dir_name in clutter_dirs:
            dir_path = project_path / dir_name
            if dir_path.exists():
                shutil.rmtree(str(dir_path))
                self.rollback_operations.append(("rmtree", dir_path, None))

    def rollback(self, project_path: str):
        """Rollback all changes made during migration.

        Args:
            project_path: Path to project root.
        """
        try:
            self._rollback()
            return True
        except Exception as e:
            print(f"Rollback failed: {e}")
            return False

    def _rollback(self):
        """Internal method to rollback all changes."""
        for operation, path, old_path in reversed(self.rollback_operations):
            try:
                if operation == "move":
                    old_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(path), str(old_path))
                elif operation == "unlink":
                    path.touch()
                elif operation == "rmtree":
                    path.mkdir(parents=True)
            except Exception as e:
                print(f"Rollback failed for {operation} {path}: {e}")
