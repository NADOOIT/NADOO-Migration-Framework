"""NADOO Framework compatibility checking."""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import toml
import requests

from .analyzers import NADOOProjectAnalyzer, NonNADOOProjectAnalyzer
from .version_management import Version, VersionManager


@dataclass
class CompatibilityRequirements:
    """Requirements for NADOO Framework compatibility."""

    min_python_version: str = "3.8"
    supported_os: List[str] = field(default_factory=lambda: ["Linux", "Darwin", "Windows"])
    required_dirs: List[str] = field(default_factory=lambda: ["src", "tests", ".nadoo"])
    required_files: List[str] = field(
        default_factory=lambda: ["pyproject.toml", ".nadoo/config.toml"]
    )
    style_rules: dict = field(
        default_factory=lambda: {
            "max_line_length": 100,
            "indent_size": 4,
            "string_quotes": "single",
        }
    )
    required_tools: List[str] = field(default_factory=lambda: ["poetry", "pytest", "black"])


@dataclass
class CompatibilityIssue:
    """Represents a compatibility issue."""

    category: str
    severity: str  # 'error', 'warning', or 'info'
    message: str
    details: Optional[str] = None
    fix_suggestion: Optional[str] = None


@dataclass
class CompatibilityCheck:
    """Results of a compatibility check."""

    project_path: Path
    current_version: Optional[Version]
    latest_version: Version
    needs_migration: bool
    changes: List[str]
    timestamp: datetime
    is_nadoo_project: bool
    python_version: str
    os_name: str
    issues: List[CompatibilityIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        base_dict = {
            "project_path": str(self.project_path),
            "current_version": str(self.current_version) if self.current_version else None,
            "latest_version": str(self.latest_version),
            "needs_migration": self.needs_migration,
            "changes": self.changes,
            "timestamp": self.timestamp.isoformat(),
            "is_nadoo_project": self.is_nadoo_project,
            "python_version": self.python_version,
            "os_name": self.os_name,
            "issues": [
                {
                    "category": issue.category,
                    "severity": issue.severity,
                    "message": issue.message,
                    "details": issue.details,
                    "fix_suggestion": issue.fix_suggestion,
                }
                for issue in self.issues
            ],
        }
        return base_dict

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        lines = [
            "# NADOO Framework Compatibility Check\n",
            f"Check performed on: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n",
            "## Environment",
            f"- Python Version: {self.python_version}",
            f"- Operating System: {self.os_name}\n",
            "## Project Status",
            f"- Project Type: {'NADOO' if self.is_nadoo_project else 'Non-NADOO'} Project",
            f"- Current Version: {self.current_version or 'Not using NADOO Framework'}",
            f"- Latest Version: {self.latest_version}",
            f"- Needs Migration: {'Yes' if self.needs_migration else 'No'}\n",
        ]

        if self.issues:
            lines.extend(
                [
                    "## Compatibility Issues\n",
                    "| Category | Severity | Issue | Fix Suggestion |",
                    "|----------|----------|-------|----------------|",
                ]
            )
            for issue in self.issues:
                lines.append(
                    f"| {issue.category} | {issue.severity} | {issue.message} | "
                    f"{issue.fix_suggestion or 'N/A'} |"
                )
            lines.append("")

        if self.changes:
            lines.extend(["## Required Changes", *[f"- {change}" for change in self.changes], ""])

        return "\n".join(lines)


class CompatibilityChecker:
    """Checks project compatibility with NADOO Framework."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.pyproject_path = project_dir / "pyproject.toml"
        self.requirements = CompatibilityRequirements()

    def check_python_version(self) -> List[CompatibilityIssue]:
        """Check Python version compatibility."""
        issues = []
        current_version = '.'.join(map(str, sys.version_info[:3]))
        min_version_parts = self.requirements.min_python_version.split('.')
        current_version_parts = current_version.split('.')

        # Compare major and minor version numbers
        current_major, current_minor = map(int, current_version_parts[:2])
        min_major, min_minor = map(int, min_version_parts[:2])

        if current_major < min_major or (current_major == min_major and current_minor < min_minor):
            issues.append(
                CompatibilityIssue(
                    category="Python Version",
                    severity="error",
                    message=f"Python version {current_version} is below minimum required version {self.requirements.min_python_version}",
                    fix_suggestion=f"Upgrade Python to version {self.requirements.min_python_version} or higher",
                )
            )
        return issues

    def check_os_compatibility(self) -> List[CompatibilityIssue]:
        """Check operating system compatibility."""
        issues = []
        if sys.platform.startswith("win32"):
            os_name = "Windows"
        elif sys.platform.startswith("darwin"):
            os_name = "Darwin"
        elif sys.platform.startswith("linux"):
            os_name = "Linux"
        else:
            os_name = sys.platform

        if os_name not in self.requirements.supported_os:
            issues.append(
                CompatibilityIssue(
                    category="Operating System",
                    severity="warning",
                    message=f"Operating system {os_name} is not officially supported",
                    details=f"Supported operating systems: {', '.join(self.requirements.supported_os)}",
                    fix_suggestion="Consider using a supported operating system for best compatibility",
                )
            )
        return issues

    def check_project_structure(self) -> List[CompatibilityIssue]:
        """Check project structure compatibility."""
        issues = []

        # Check required directories
        for required_dir in self.requirements.required_dirs:
            dir_path = self.project_dir / required_dir
            if not dir_path.exists():
                issues.append(
                    CompatibilityIssue(
                        category="Project Structure",
                        severity="error",
                        message=f"Missing required directory: {required_dir}",
                        fix_suggestion=f"Create directory: {required_dir}",
                    )
                )

        # Check required files
        for required_file in self.requirements.required_files:
            file_path = self.project_dir / required_file
            if not file_path.exists():
                issues.append(
                    CompatibilityIssue(
                        category="Project Structure",
                        severity="error",
                        message=f"Missing required file: {required_file}",
                        fix_suggestion=f"Create file: {required_file}",
                    )
                )

        return issues

    def check_dependencies(self) -> List[CompatibilityIssue]:
        """Check dependencies compatibility."""
        issues = []

        if not self.pyproject_path.exists():
            return [
                CompatibilityIssue(
                    category="Dependencies",
                    severity="error",
                    message="Missing pyproject.toml file",
                    fix_suggestion="Initialize project with Poetry: poetry init",
                )
            ]

        try:
            with open(self.pyproject_path) as f:
                pyproject_data = toml.load(f)

            # Check required tools
            for tool in self.requirements.required_tools:
                if tool not in str(pyproject_data):
                    issues.append(
                        CompatibilityIssue(
                            category="Dependencies",
                            severity="warning",
                            message=f"Missing required tool: {tool}",
                            fix_suggestion=f"Add {tool} to development dependencies",
                        )
                    )

            # Check Python version constraint
            if "tool" in pyproject_data and "poetry" in pyproject_data["tool"]:
                python_constraint = (
                    pyproject_data["tool"]["poetry"].get("dependencies", {}).get("python", "")
                )
                if not any(
                    v in python_constraint
                    for v in [self.requirements.min_python_version, "^3", ">=3"]
                ):
                    issues.append(
                        CompatibilityIssue(
                            category="Dependencies",
                            severity="warning",
                            message=f"Python version constraint may be too restrictive: {python_constraint}",
                            fix_suggestion=f"Update Python constraint to >={self.requirements.min_python_version}",
                        )
                    )

        except Exception as e:
            issues.append(
                CompatibilityIssue(
                    category="Dependencies",
                    severity="error",
                    message=f"Error parsing pyproject.toml: {str(e)}",
                    fix_suggestion="Validate pyproject.toml format",
                )
            )

        return issues

    def check_code_style(self) -> List[CompatibilityIssue]:
        """Check code style using black."""
        issues = []

        try:
            import black
        except ImportError:
            issues.append(
                CompatibilityIssue(
                    severity="warning",
                    category="code-style",
                    message="Missing required tool: black",
                    fix_suggestion="Add black to development dependencies",
                )
            )
            return issues

        for python_file in self.project_dir.rglob("*.py"):
            try:
                with open(python_file, "r") as f:
                    content = f.read()

                # Check indentation
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if line.strip() and line[0] == " " and not line.startswith("    "):
                        issues.append(
                            CompatibilityIssue(
                                severity="warning",
                                category="code-style",
                                message=f"file://{python_file}:{i} - Invalid indentation",
                                fix_suggestion="Use 4 spaces for indentation",
                            )
                        )

                # Try to format with black to check for other style issues
                try:
                    black.format_file_contents(content, fast=True, mode=black.FileMode())
                except black.InvalidInput as e:
                    issues.append(
                        CompatibilityIssue(
                            severity="warning",
                            category="code-style",
                            message=f"file://{python_file} - {str(e)}",
                            fix_suggestion="Run black to format the file",
                        )
                    )
            except Exception as e:
                issues.append(
                    CompatibilityIssue(
                        severity="error",
                        category="code-style",
                        message=f"file://{python_file} - Error checking code style: {str(e)}",
                        fix_suggestion=None,
                    )
                )

        return issues

    def get_latest_version(self) -> Version:
        """Get latest NADOO Framework version from PyPI."""
        try:
            response = requests.get("https://pypi.org/pypi/nadoo-migration-framework/json")
            response.raise_for_status()
            data = response.json()
            return Version.from_string(data["info"]["version"])
        except Exception as e:
            print(f"Error fetching latest version: {e}", file=sys.stderr)
            return Version(0, 2, 5)  # Updated fallback version

    def check_compatibility(self) -> CompatibilityCheck:
        """Check project compatibility with latest NADOO Framework version."""
        latest_version = self.get_latest_version()
        current_version = None
        changes = []
        is_nadoo_project = False

        # Collect all compatibility issues
        issues = []
        issues.extend(self.check_python_version())
        issues.extend(self.check_os_compatibility())
        issues.extend(self.check_project_structure())
        issues.extend(self.check_dependencies())
        issues.extend(self.check_code_style())

        # Determine project type and analyze
        if self.pyproject_path.exists():
            with open(self.pyproject_path) as f:
                data = toml.load(f)

            # Check if it's a NADOO project
            if "tool" in data and "nadoo" in data["tool"]:
                is_nadoo_project = True
                current_version = Version.from_string(data["tool"]["nadoo"]["version"])

        # Determine required changes based on issues
        for issue in issues:
            if issue.fix_suggestion:
                changes.append(issue.fix_suggestion)

        # Add version update if needed
        if is_nadoo_project and current_version < latest_version:
            changes.append(f"Update NADOO Framework from {current_version} to {latest_version}")
        elif not is_nadoo_project:
            changes.extend(
                [
                    "Initialize NADOO Framework structure",
                    "Add NADOO Framework configuration",
                    "Configure project settings",
                ]
            )

        return CompatibilityCheck(
            project_path=self.project_dir,
            current_version=current_version,
            latest_version=latest_version,
            needs_migration=bool(changes),
            changes=changes,
            timestamp=datetime.now(),
            is_nadoo_project=is_nadoo_project,
            python_version='.'.join(map(str, sys.version_info[:3])),
            os_name=sys.platform,
            issues=issues,
        )
