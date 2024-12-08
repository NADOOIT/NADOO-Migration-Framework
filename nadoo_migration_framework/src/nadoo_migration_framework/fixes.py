"""NADOO Framework automatic fixes."""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any

import black
import toml

from .compatibility import CompatibilityIssue


@dataclass
class FixResult:
    """Result of applying a fix."""

    success: bool
    message: str
    details: Optional[str] = None


class FixManager:
    """Manages automatic fixes for compatibility issues."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.pyproject_path = project_dir / "pyproject.toml"

    def _extract_file_path(self, issue: CompatibilityIssue) -> Optional[Path]:
        """Extract file path from issue message."""
        if "file://" in issue.message:
            # Extract path and line number if present
            parts = issue.message.split(" - ")[0].replace("file://", "").split(":")
            return Path(parts[0])
        return None

    def fix_code_style(self, issue: CompatibilityIssue) -> FixResult:
        """Fix code style issues using black."""
        return self._apply_code_style_fixes(issue)

    def _apply_code_style_fixes(self, issue: CompatibilityIssue) -> FixResult:
        """Apply code style fixes using black."""
        try:
            file_path = self._extract_file_path(issue)
            if not file_path:
                return FixResult(
                    success=False,
                    message="Could not determine file path from issue",
                    details=issue.message,
                )

            if not file_path.exists():
                return FixResult(
                    success=False, message=f"File not found: {file_path}", details=None
                )

            try:
                import black
            except ImportError:
                return FixResult(
                    success=False,
                    message="Black is not installed",
                    details="Run: poetry add --dev black",
                )

            try:
                with open(file_path, "r") as f:
                    content = f.read()

                formatted_content = black.format_file_contents(
                    content, fast=False, mode=black.FileMode()
                )

                with open(file_path, "w") as f:
                    f.write(formatted_content)

                return FixResult(
                    success=True, message=f"Successfully formatted {file_path}", details=None
                )

            except black.InvalidInput as e:
                return FixResult(
                    success=False,
                    message=f"Black formatting failed for {file_path}",
                    details=str(e),
                )

        except Exception as e:
            return FixResult(success=False, message="Error applying code style fix", details=str(e))

    def fix_dependencies(self, issue: CompatibilityIssue) -> FixResult:
        """Add missing dependencies using poetry."""
        try:
            # Extract package name from issue message
            if "Missing required tool:" not in issue.message:
                return FixResult(
                    success=False, message="Not a missing dependency issue", details=issue.message
                )

            package = issue.message.replace("Missing required tool:", "").strip()

            # Run poetry add command
            cmd = ["poetry", "add", "--group", "dev", package]
            result = subprocess.run(cmd, cwd=self.project_dir, capture_output=True, text=True)

            if result.returncode == 0:
                return FixResult(
                    success=True, message=f"Successfully added {package}", details=result.stdout
                )
            else:
                return FixResult(
                    success=False,
                    message=f"Failed to add {package}",
                    details=result.stderr or result.stdout,
                )

        except Exception as e:
            return FixResult(success=False, message="Error fixing dependencies", details=str(e))

    def fix_project_structure(self, issue: CompatibilityIssue) -> FixResult:
        """Fix project structure issues."""
        try:
            if "Missing required directory" in issue.message:
                dir_name = issue.message.split(":")[-1].strip()
                dir_path = self.project_dir / dir_name
                dir_path.mkdir(parents=True, exist_ok=True)
                return FixResult(
                    success=True,
                    message=f"Created directory: {dir_name}",
                    details=f"Path: {dir_path}",
                )

            elif "Missing required file" in issue.message:
                file_name = issue.message.split(":")[-1].strip()
                file_path = self.project_dir / file_name

                # Create parent directories if needed
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Create empty file or template based on file type
                if file_name == "pyproject.toml":
                    content = self._generate_pyproject_template()
                elif file_name == ".nadoo/config.toml":
                    content = self._generate_nadoo_config_template()
                else:
                    content = ""

                with open(file_path, 'w') as f:
                    f.write(content)

                return FixResult(
                    success=True, message=f"Created file: {file_name}", details=f"Path: {file_path}"
                )

            return FixResult(
                success=False, message="Unsupported project structure issue", details=issue.message
            )

        except Exception as e:
            return FixResult(
                success=False, message="Failed to fix project structure", details=str(e)
            )

    def _generate_pyproject_template(self) -> str:
        """Generate a template pyproject.toml file."""
        config = {
            "build-system": {
                "requires": ["poetry-core>=1.0.0"],
                "build-backend": "poetry.core.masonry.api",
            },
            "tool": {
                "poetry": {
                    "name": self.project_dir.name,
                    "version": "0.1.0",
                    "description": "",
                    "authors": [],
                    "dependencies": {"python": "^3.8"},
                    "dev-dependencies": {},
                },
                "nadoo": {"version": "0.2.5"},
            },
        }
        return toml.dumps(config)

    def _generate_nadoo_config_template(self) -> str:
        """Generate a template NADOO config file."""
        config = {
            "version": "0.2.5",
            "project": {"name": self.project_dir.name, "description": ""},
            "migration": {"backup": True, "auto_commit": True},
        }
        return toml.dumps(config)

    def apply_fixes(self, issues: List[CompatibilityIssue]) -> Dict[str, List[FixResult]]:
        """Apply fixes for all issues."""
        results: Dict[str, List[FixResult]] = {}

        for issue in issues:
            if issue.category not in results:
                results[issue.category] = []

            if issue.category == "Code Style":
                result = self.fix_code_style(issue)
            elif issue.category == "Dependencies":
                result = self.fix_dependencies(issue)
            elif issue.category == "Project Structure":
                result = self.fix_project_structure(issue)
            else:
                result = FixResult(
                    success=False,
                    message=f"No automatic fix available for {issue.category}",
                    details=issue.message,
                )

            results[issue.category].append(result)

        return results
