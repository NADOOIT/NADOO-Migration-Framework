"""Migration to clean up and restructure project according to NADOO-Framework standards."""

import os
import shutil
import re
import gc
import stat
import psutil
from pathlib import Path
from typing import List, Set, Tuple
from ..version import Version
from .base_migration import BaseMigration

class SecurityError(Exception):
    """Exception raised for security-related issues."""
    pass

class MemoryError(Exception):
    """Exception raised for memory-related issues."""
    pass

class CleanupProjectStructureMigration(BaseMigration):
    """Migration to clean up and restructure the project."""
    
    def __init__(self):
        """Initialize the migration."""
        super().__init__(
            name="cleanup_project_structure",
            description="Restructures project to follow NADOO-Framework standards",
            version=Version.from_string("0.2.7")
        )
        self._memory_limit = 1024 * 1024 * 1024  # 1GB default limit
        self.secure_file_mode = 0o644
        self.secure_dir_mode = 0o755
    
    def _check_memory_usage(self) -> None:
        """Check current memory usage against limit."""
        current_memory = psutil.Process().memory_info().rss
        if current_memory > self._memory_limit:
            gc.collect()  # Try to free memory
            current_memory = psutil.Process().memory_info().rss
            if current_memory > self._memory_limit:
                raise MemoryError(f"Memory usage ({current_memory / 1024 / 1024:.2f}MB) exceeds limit")
    
    def _verify_file_security(self, path: Path) -> None:
        """Verify file security aspects."""
        try:
            # Check for symlinks
            if path.is_symlink():
                raise SecurityError(f"Symlinks are not allowed: {path}")
            
            # Check for path traversal
            real_path = path.resolve()
            if not str(real_path).startswith(str(path.parent.resolve())):
                raise SecurityError(f"Path traversal detected: {path}")
            
            # Check permissions
            if path.exists():
                mode = path.stat().st_mode
                if mode & stat.S_IWOTH or mode & stat.S_IXOTH:
                    # Remove write and execute permissions for others
                    path.chmod(mode & ~stat.S_IWOTH & ~stat.S_IXOTH)
        except Exception as e:
            if not isinstance(e, SecurityError):
                raise SecurityError(f"Security check failed for {path}: {str(e)}")
            raise

    def _check_symlink_security(self, path: Path) -> None:
        """Check if a path contains malicious symlinks."""
        if path.is_symlink():
            target = path.resolve()
            if not str(target).startswith(str(path.parent.resolve())):
                raise SecurityError(f"Malicious symlink detected: {path} -> {target}")

    def _enforce_secure_permissions(self, path: Path) -> None:
        """Enforce secure file permissions."""
        if path.is_file():
            path.chmod(self.secure_file_mode)
        elif path.is_dir():
            path.chmod(self.secure_dir_mode)

    def _safe_copy(self, src: Path, dst: Path) -> None:
        """Safely copy a file with security checks."""
        self._verify_file_security(src)
        self._check_memory_usage()
        
        # Create parent directories with secure permissions
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.parent.chmod(0o755)  # rwxr-x
        
        # Copy file and set secure permissions
        shutil.copy2(src, dst)
        dst.chmod(0o644)  # rw-r--r--
    
    def _get_excludes(self) -> Set[str]:
        """Get list of paths to exclude from cleanup."""
        return {
            '.git',
            '.github',
            '.gitignore',
            'LICENSE',
            'README.md',
            'pyproject.toml',
            'poetry.lock',
            '.venv',
            'venv',
            'env',
            '.backup',
            '__pycache__',
        }
    
    def _create_nadoo_structure(self, project_path: str) -> None:
        """Create NADOO-Framework standard directory structure."""
        base_path = Path(project_path)
        project_name = base_path.name.replace('-', '_')
        
        # Create main package structure
        paths = [
            base_path / 'src' / project_name,
            base_path / 'src' / project_name / 'functions',
            base_path / 'src' / project_name / 'classes',
            base_path / 'tests',
            base_path / 'docs',
        ]
        
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
            init_file = path / '__init__.py'
            if not init_file.exists():
                init_file.touch()
                init_file.chmod(0o644)  # rw-r--r--
        
        # Create root package __init__.py
        root_init = base_path / 'src' / '__init__.py'
        if not root_init.exists():
            root_init.touch()
            root_init.chmod(0o644)  # rw-r--r--
    
    def _update_imports(self, content: str, old_package: str, new_package: str) -> str:
        """Update import statements in the file content."""
        patterns = [
            # Handle imports from functions directory
            (rf"from {old_package}\.functions\.(\w+)", rf"from {new_package}.functions.\1"),
            (rf"import {old_package}\.functions\.(\w+)", rf"import {new_package}.functions.\1"),
            
            # Handle imports from classes directory
            (rf"from {old_package}\.classes\.(\w+)", rf"from {new_package}.classes.\1"),
            (rf"import {old_package}\.classes\.(\w+)", rf"import {new_package}.classes.\1"),
            
            # Handle direct imports from the root package
            (rf"from {old_package}\.(\w+)", rf"from {new_package}.\1"),
            (rf"import {old_package}\.(\w+)", rf"import {new_package}.\1"),
            
            # Handle relative imports
            (r"from \.([\w\.]+)", rf"from {new_package}.\1"),
            (r"from \.\.([\w\.]+)", rf"from {new_package}.\1"),
        ]
        
        updated_content = content
        for pattern, replacement in patterns:
            updated_content = re.sub(pattern, replacement, updated_content)
        
        return updated_content
    
    def _normalize_content(self, content: str) -> str:
        """Normalize file content for comparison by removing Path import and whitespace."""
        lines = content.split('\n')
        normalized = []
        for line in lines:
            if not line.strip():  # Skip empty lines
                continue
            if 'from pathlib import Path' in line:  # Skip Path import
                continue
            normalized.append(line.strip())
        return '\n'.join(normalized)
    
    def _update_file_content(self, file_path: Path, project_name: str) -> None:
        """Update the content of a Python file."""
        if file_path.suffix != '.py':
            return
            
        content = file_path.read_text()
        original_content = content
        
        # Add Path import if the file uses Path
        if 'Path(' in content and 'from pathlib import Path' not in content:
            content = 'from pathlib import Path\n' + content
        
        # Update imports
        content = self._update_imports(content, 'nadoo_migration_framework', project_name)
        content = self._update_imports(content, 'functions', f'{project_name}.functions')
        content = self._update_imports(content, 'classes', f'{project_name}.classes')
        
        # Only write if content has changed
        if self._normalize_content(content) != self._normalize_content(original_content):
            file_path.write_text(content)
    
    def _move_existing_code(self, project_path: str) -> None:
        """Move existing code to new structure."""
        try:
            base_path = Path(project_path)
            project_name = base_path.name.replace('-', '_')
            src_path = base_path / 'src' / project_name
            
            # Map of old paths to new locations
            moves = {
                'src/functions': src_path / 'functions',
                'src/classes': src_path / 'classes',
                'src/nadoo_migration_framework/functions': src_path / 'functions',
                'src/nadoo_migration_framework/classes': src_path / 'classes',
            }
            
            # First collect all files to move
            files_to_move = []
            for old_path, new_path in moves.items():
                old_full_path = base_path / old_path
                if old_full_path.exists():
                    for item in old_full_path.rglob('*'):
                        if item.is_file() and item.name not in self._get_excludes():
                            self._verify_file_security(item)
                            rel_path = item.relative_to(old_full_path)
                            target_path = new_path / rel_path
                            files_to_move.append((item, target_path))
                            
                        # Check memory usage periodically
                        self._check_memory_usage()
            
            # Then move all files
            for src_file, dst_file in files_to_move:
                if src_file != dst_file:  # Only copy if source and destination are different
                    self._safe_copy(src_file, dst_file)
                    self._update_file_content(dst_file, project_name)
            
            # Create __init__.py files in all package directories
            for root, dirs, _ in os.walk(src_path):
                for dir_name in dirs:
                    init_file = Path(root) / dir_name / '__init__.py'
                    if not init_file.exists():
                        init_file.touch()
                        init_file.chmod(0o644)  # rw-r--r--
                        
                # Check memory usage periodically
                self._check_memory_usage()
                
        except Exception as e:
            self.logger.error(f"Failed to move existing code: {str(e)}")
            raise
    
    def _cleanup_old_files(self, project_path: str) -> None:
        """Remove old files and directories."""
        base_path = Path(project_path)
        excludes = self._get_excludes()
        
        # Clean up old directories
        old_dirs = [
            'src/functions',
            'src/classes',
            'src/nadoo_migration_framework',
            'build',
            'dist',
            '__pycache__',
            '.pytest_cache',
            '.coverage',
            '.DS_Store',
        ]
        
        for old_dir in old_dirs:
            path = base_path / old_dir
            if path.exists() and path.name not in excludes:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
    
    def migrate(self, project_path: str, dry_run: bool = False) -> bool:
        """Perform the migration."""
        try:
            if dry_run:
                self.logger.info("Would restructure project (dry run)")
                return True
            
            # Security checks first
            project_dir = Path(project_path)
            for path in project_dir.rglob("*"):
                self._check_symlink_security(path)
                self._enforce_secure_permissions(path)
            
            # Create backup
            backup_dir = Path(project_path) / '.backup'
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.copytree(project_path, backup_dir, ignore=shutil.ignore_patterns(*self._get_excludes()))
            
            # Create new structure
            self._create_nadoo_structure(project_path)
            
            # Move existing code
            self._move_existing_code(project_path)
            
            # Clean up old files
            self._cleanup_old_files(project_path)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to restructure project: {str(e)}")
            # Restore from backup if available
            backup_dir = Path(project_path) / '.backup'
            if backup_dir.exists():
                # Remove current structure except backup and excluded files
                for item in Path(project_path).iterdir():
                    if item.name not in self._get_excludes() and item != backup_dir:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                
                # Restore from backup
                for item in backup_dir.iterdir():
                    target = Path(project_path) / item.name
                    if item.is_dir():
                        shutil.copytree(item, target, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, target)
                
                # Clean up backup
                shutil.rmtree(backup_dir)
            return False
    
    def rollback(self, project_path: str) -> bool:
        """Rollback the migration."""
        try:
            backup_dir = Path(project_path) / '.backup'
            if backup_dir.exists():
                # Remove current structure except backup and excluded files
                for item in Path(project_path).iterdir():
                    if item.name not in self._get_excludes() and item != backup_dir:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                
                # Restore from backup
                for item in backup_dir.iterdir():
                    target = Path(project_path) / item.name
                    if item.is_dir():
                        shutil.copytree(item, target, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, target)
                
                # Clean up backup
                shutil.rmtree(backup_dir)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to rollback project structure: {str(e)}")
            return False
