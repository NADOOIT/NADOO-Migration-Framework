"""Migration to fix project structure."""
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any

from ..migration_base import MigrationBase


class FixProjectStructureMigration(MigrationBase):
    """Migration to fix project structure."""

    def __init__(self):
        """Initialize the migration."""
        super().__init__()
        self.migration_id = "fix_project_structure"
        self.description = "Fixes project structure to follow standards"
        self.backup_dir = None

    def backup_files(self, files_to_backup: List[Path]) -> None:
        """Backup files before migration.
        
        Args:
            files_to_backup: List of files to backup.
        """
        self.backup_dir = Path(".migration_backup")
        self.backup_dir.mkdir(exist_ok=True)
        
        for file in files_to_backup:
            if file.exists():
                backup_path = self.backup_dir / file.name
                if file.is_dir():
                    if backup_path.exists():
                        shutil.rmtree(backup_path)
                    shutil.copytree(file, backup_path)
                else:
                    shutil.copy2(file, backup_path)

    def merge_toml_files(self, files: List[Path]) -> Dict[str, Any]:
        """Merge multiple pyproject.toml files.
        
        Args:
            files: List of pyproject.toml files.
            
        Returns:
            Dict containing merged content.
        """
        import toml
        
        merged = {}
        for file in files:
            if file.exists():
                with open(file) as f:
                    content = toml.load(f)
                    for section, data in content.items():
                        if section not in merged:
                            merged[section] = data
                        elif isinstance(merged[section], dict) and isinstance(data, dict):
                            merged[section].update(data)
                        else:
                            merged[section] = data
        return merged

    def migrate(self) -> None:
        """Perform the migration."""
        # Backup current files
        files_to_backup = [
            Path("nadoo_law"),
            Path("README.md"),
            Path("pyproject.toml")
        ]
        self.backup_files(files_to_backup)
        
        # Create new directory structure
        src_dir = Path("src/nadoo_law")
        tests_dir = Path("tests")
        src_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)
        
        # Move source files
        old_src = Path("nadoo_law/src/nadoo_law")
        if old_src.exists():
            for item in old_src.glob("*"):
                if item.is_file():
                    shutil.copy2(item, src_dir)
                else:
                    shutil.copytree(item, src_dir / item.name, dirs_exist_ok=True)
        
        # Move test files
        old_tests = Path("nadoo_law/tests")
        if old_tests.exists():
            for item in old_tests.glob("*"):
                if item.name != "__pycache__":
                    if item.is_file():
                        shutil.copy2(item, tests_dir)
                    else:
                        shutil.copytree(item, tests_dir / item.name, dirs_exist_ok=True)
        
        # Merge and update pyproject.toml
        toml_files = [
            Path("pyproject.toml"),
            Path("nadoo_law/pyproject.toml")
        ]
        merged_toml = self.merge_toml_files(toml_files)
        
        # Update project metadata
        merged_toml.setdefault("project", {})
        merged_toml["project"].update({
            "name": "nadoo_law",
            "version": "0.1.0",
            "description": "NADOO Law - Legal Document Processing Framework",
            "readme": "README.md",
            "requires-python": ">=3.8",
            "license": {"file": "LICENSE"},
            "authors": [
                {"name": "NADOO", "email": "info@nadoo.ai"}
            ]
        })
        
        # Add build system
        merged_toml["build-system"] = {
            "requires": ["poetry-core>=1.0.0"],
            "build-backend": "poetry.core.masonry.api"
        }
        
        # Add test dependencies
        merged_toml.setdefault("tool", {}).setdefault("poetry", {}).setdefault("dependencies", {})
        merged_toml["tool"]["poetry"].setdefault("group", {}).setdefault("test", {}).setdefault("dependencies", {}).update({
            "pytest": "^7.0.0",
            "pytest-cov": "^4.0.0",
            "pytest-asyncio": "^0.21.0"
        })
        
        # Write updated pyproject.toml
        import toml
        with open("pyproject.toml", "w") as f:
            toml.dump(merged_toml, f)
        
        # Create/update README.md
        readme_content = """# NADOO Law

Legal Document Processing Framework

## Installation

```bash
pip install nadoo_law
```

## Usage

```python
from nadoo_law import process_document

# Process a legal document
result = process_document("contract.pdf")
```

## Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install poetry
   poetry install
   ```
3. Run tests:
   ```bash
   poetry run pytest
   ```

## License

This project is licensed under the terms of the license file included in the repository.
"""
        with open("README.md", "w") as f:
            f.write(readme_content)
        
        # Clean up old files
        if Path("nadoo_law").exists():
            shutil.rmtree("nadoo_law")

    def rollback(self) -> None:
        """Rollback the migration."""
        if self.backup_dir and self.backup_dir.exists():
            for item in self.backup_dir.iterdir():
                target = Path(item.name)
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                if item.is_dir():
                    shutil.copytree(item, target)
                else:
                    shutil.copy2(item, target)
            shutil.rmtree(self.backup_dir)
