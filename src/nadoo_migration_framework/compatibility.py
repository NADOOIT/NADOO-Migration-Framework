"""NADOO Framework compatibility checking."""

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import toml
import requests

from .analyzers import NADOOProjectAnalyzer, NonNADOOProjectAnalyzer
from .version_management import Version, VersionManager


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
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "project_path": str(self.project_path),
            "current_version": str(self.current_version) if self.current_version else None,
            "latest_version": str(self.latest_version),
            "needs_migration": self.needs_migration,
            "changes": self.changes,
            "timestamp": self.timestamp.isoformat(),
            "is_nadoo_project": self.is_nadoo_project
        }
    
    def to_markdown(self) -> str:
        """Convert to markdown format."""
        lines = [
            "# NADOO Framework Compatibility Check\n",
            f"Check performed on: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n",
            "## Project Status",
            f"- Project Type: {'NADOO' if self.is_nadoo_project else 'Non-NADOO'} Project",
            f"- Current Version: {self.current_version or 'Not using NADOO Framework'}",
            f"- Latest Version: {self.latest_version}",
            f"- Needs Migration: {'Yes' if self.needs_migration else 'No'}\n"
        ]
        
        if self.changes:
            lines.extend([
                "## Required Changes",
                *[f"- {change}" for change in self.changes],
                ""
            ])
        
        return "\n".join(lines)


class CompatibilityChecker:
    """Checks project compatibility with NADOO Framework."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.pyproject_path = project_dir / "pyproject.toml"
    
    def get_latest_version(self) -> Version:
        """Get latest NADOO Framework version from PyPI."""
        try:
            response = requests.get("https://pypi.org/pypi/nadoo-migration-framework/json")
            response.raise_for_status()
            data = response.json()
            return Version.from_string(data["info"]["version"])
        except Exception as e:
            print(f"Error fetching latest version: {e}", file=sys.stderr)
            # Return current package version as fallback
            return Version(0, 1, 2)  # TODO: Update this dynamically
    
    def check_compatibility(self) -> CompatibilityCheck:
        """Check project compatibility with latest NADOO Framework version."""
        latest_version = self.get_latest_version()
        current_version = None
        changes = []
        is_nadoo_project = False
        
        # Determine project type and analyze
        if self.pyproject_path.exists():
            with open(self.pyproject_path) as f:
                data = toml.load(f)
                
            # Check if it's a NADOO project
            if "tool" in data and "poetry" in data["tool"]:
                deps = data["tool"]["poetry"].get("dependencies", {})
                if "nadoo-framework" in deps:
                    is_nadoo_project = True
                    analyzer = NADOOProjectAnalyzer(self.project_dir)
                    current_version = Version.from_string(deps["nadoo-framework"].strip("^~="))
        
        if not is_nadoo_project:
            analyzer = NonNADOOProjectAnalyzer(self.project_dir)
        
        # Analyze project structure
        analysis = analyzer.analyze()
        
        # Determine required changes
        if is_nadoo_project:
            if current_version < latest_version:
                changes.append(f"Update NADOO Framework from {current_version} to {latest_version}")
        else:
            changes.extend([
                "Initialize NADOO Framework structure",
                "Add NADOO Framework dependency",
                "Configure project settings"
            ])
        
        # Add specific changes based on analysis
        if analysis.get("missing_files"):
            changes.extend([f"Create missing file: {f}" for f in analysis["missing_files"]])
        if analysis.get("invalid_structure"):
            changes.extend([f"Fix structure: {issue}" for issue in analysis["invalid_structure"]])
        
        return CompatibilityCheck(
            project_path=self.project_dir,
            current_version=current_version,
            latest_version=latest_version,
            needs_migration=bool(changes),
            changes=changes,
            timestamp=datetime.now(),
            is_nadoo_project=is_nadoo_project
        )
