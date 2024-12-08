"""Project analyzers for detecting and analyzing different project types."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
import toml

from .functions import code_analysis, project_structure, dependency_analysis


class ProjectAnalyzer(ABC):
    """Base class for project analyzers."""

    def __init__(self, project_path: Path):
        """Initialize analyzer with project path.

        Args:
            project_path (Path): Path to the project root
        """
        self.project_path = project_path

    @abstractmethod
    def analyze(self) -> Dict[str, any]:
        """Analyze the project and return findings.

        Returns:
            Dict[str, any]: Analysis results including project type, structure, etc.
        """
        pass

    @abstractmethod
    def get_required_migrations(self) -> List[str]:
        """Determine required migrations based on analysis.

        Returns:
            List[str]: List of required migration identifiers
        """
        pass


class NADOOProjectAnalyzer(ProjectAnalyzer):
    """Analyzer for existing NADOO Framework projects."""

    def analyze(self) -> Dict[str, any]:
        """Analyze the NADOO project.

        Returns:
            Dict[str, any]: Analysis results
        """
        results = {
            'project_type': 'nadoo',
            'version': self._get_project_version(),
            'structure': project_structure.get_package_structure(self.project_path),
            'dependencies': dependency_analysis.analyze_project_dependencies(self.project_path),
            'code_analysis': self._analyze_code(),
        }

        return results

    def get_required_migrations(self) -> List[str]:
        """Get required migrations for the NADOO project.

        Returns:
            List[str]: Required migrations
        """
        migrations = []

        # Check project structure
        if not self._has_valid_structure():
            migrations.append("Fix project structure")

        # Check dependencies
        if not self._has_valid_dependencies():
            migrations.append("Update dependencies")

        return migrations

    def is_nadoo_project(self) -> bool:
        """Check if this is a NADOO project.

        Returns:
            bool: True if this is a NADOO project
        """
        settings_path = self.project_path / "nadoo" / "config" / "settings.toml"
        if not settings_path.exists():
            return False

        try:
            settings = toml.load(settings_path)
            return "nadoo" in settings and "version" in settings["nadoo"]
        except:
            return False

    def _get_project_version(self) -> Optional[str]:
        """Get the project's NADOO Framework version.

        Returns:
            Optional[str]: Version string or None if not found
        """
        settings_path = self.project_path / "nadoo" / "config" / "settings.toml"
        if not settings_path.exists():
            return None

        try:
            settings = toml.load(settings_path)
            return settings.get("nadoo", {}).get("version")
        except:
            return None

    def _has_valid_structure(self) -> bool:
        """Check if project has valid NADOO structure.

        Returns:
            bool: True if structure is valid
        """
        required_dirs = [
            "nadoo",
            "nadoo/config",
            "nadoo/migrations",
            "nadoo/templates",
            "nadoo/static",
        ]

        for dir_path in required_dirs:
            if not (self.project_path / dir_path).exists():
                return False

        return True

    def _has_valid_dependencies(self) -> bool:
        """Check if project has valid dependencies.

        Returns:
            bool: True if dependencies are valid
        """
        deps = dependency_analysis.analyze_project_dependencies(self.project_path)
        required_deps = ["nadoo-framework", "toga"]

        for dep in required_deps:
            if dep not in deps:
                return False

        return True

    def _analyze_code(self) -> Dict[str, any]:
        """Analyze the codebase.

        Returns:
            Dict[str, any]: Code analysis results
        """
        return code_analysis.analyze_project_code(self.project_path)


class NonNADOOProjectAnalyzer(ProjectAnalyzer):
    """Analyzer for non-NADOO projects to be migrated."""

    def analyze(self) -> Dict[str, any]:
        """Analyze the non-NADOO project.

        Returns:
            Dict[str, any]: Analysis results
        """
        return {
            'project_type': self._detect_project_type(),
            'structure': project_structure.get_package_structure(self.project_path),
            'dependencies': dependency_analysis.analyze_project_dependencies(self.project_path),
            'code_analysis': self._analyze_code(),
        }

    def get_required_migrations(self) -> List[str]:
        """Get required migrations for the non-NADOO project.

        Returns:
            List[str]: Required migrations
        """
        migrations = [
            "Initialize NADOO Framework",
            "Create project structure",
            "Add framework dependencies",
            "Configure project settings",
        ]

        # Add GUI migrations if needed
        if self._needs_gui_migration():
            migrations.extend(["Create GUI structure", "Add GUI dependencies"])

        return migrations

    def _detect_project_type(self) -> str:
        """Detect the type of project.

        Returns:
            str: Project type (e.g., 'django', 'flask', etc.)
        """
        deps = dependency_analysis.analyze_project_dependencies(self.project_path)

        if "django" in deps:
            return "django"
        elif "flask" in deps:
            return "flask"
        else:
            return "python"

    def _needs_gui_migration(self) -> bool:
        """Check if project needs GUI migration.

        Returns:
            bool: True if GUI migration is needed
        """
        deps = dependency_analysis.analyze_project_dependencies(self.project_path)
        return "toga" not in deps

    def _analyze_code(self) -> Dict[str, any]:
        """Analyze the codebase.

        Returns:
            Dict[str, any]: Code analysis results
        """
        return code_analysis.analyze_project_code(self.project_path)
