"""Version compatibility management for NADOO Migration Framework."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from packaging import version
import toml
from pathlib import Path

@dataclass
class VersionRequirement:
    """Version requirement for a framework or template."""
    min_version: str
    max_version: str
    excluded_versions: Set[str] = None
    required_dependencies: Dict[str, str] = None

    def __post_init__(self):
        """Initialize after creation."""
        if self.excluded_versions is None:
            self.excluded_versions = set()
        if self.required_dependencies is None:
            self.required_dependencies = {}

    def is_compatible(self, target_version: str) -> bool:
        """Check if a version is compatible.
        
        Args:
            target_version: Version to check
            
        Returns:
            bool: True if version is compatible
        """
        if target_version in self.excluded_versions:
            return False
            
        try:
            ver = version.parse(target_version)
            min_ver = version.parse(self.min_version)
            max_ver = version.parse(self.max_version)
            return min_ver <= ver <= max_ver
        except version.InvalidVersion:
            return False

class VersionCompatibilityMatrix:
    """Version compatibility matrix for frameworks and templates."""

    def __init__(self):
        """Initialize version compatibility matrix."""
        self.framework_requirements: Dict[str, Dict[str, VersionRequirement]] = {}
        self.template_requirements: Dict[str, Dict[str, VersionRequirement]] = {}
        self._load_requirements()

    def _load_requirements(self):
        """Load version requirements from configuration."""
        # Toga Framework Requirements
        self.framework_requirements["toga"] = {
            "0.3.0": VersionRequirement(
                min_version="0.3.0",
                max_version="0.3.3",
                excluded_versions={"0.3.1"},  # Known buggy version
                required_dependencies={
                    "briefcase": ">=0.3.14",
                    "libcst": ">=1.0.0"
                }
            ),
            "0.3.3": VersionRequirement(
                min_version="0.3.3",
                max_version="0.4.0",
                required_dependencies={
                    "briefcase": ">=0.3.15",
                    "libcst": ">=1.1.0"
                }
            )
        }

        # Template Requirements
        self.template_requirements["toga-single"] = {
            "0.3.0": VersionRequirement(
                min_version="0.3.0",
                max_version="0.3.3",
                required_dependencies={
                    "toga": ">=0.3.0",
                    "briefcase": ">=0.3.14"
                }
            )
        }
        self.template_requirements["toga-multi"] = {
            "0.3.0": VersionRequirement(
                min_version="0.3.0",
                max_version="0.3.3",
                required_dependencies={
                    "toga": ">=0.3.0",
                    "briefcase": ">=0.3.14"
                }
            )
        }

    def check_framework_compatibility(
        self, framework: str, current_version: str, target_version: str
    ) -> Tuple[bool, List[str]]:
        """Check framework version compatibility.
        
        Args:
            framework: Framework name
            current_version: Current framework version
            target_version: Target framework version
            
        Returns:
            Tuple[bool, List[str]]: (is_compatible, list of incompatibility reasons)
        """
        if framework not in self.framework_requirements:
            return False, [f"Unknown framework: {framework}"]

        if target_version not in self.framework_requirements[framework]:
            return False, [f"Unknown target version: {target_version}"]

        requirement = self.framework_requirements[framework][target_version]
        reasons = []

        if not requirement.is_compatible(current_version):
            reasons.append(
                f"Current version {current_version} is not compatible with target version {target_version}"
            )

        return len(reasons) == 0, reasons

    def check_template_compatibility(
        self, template: str, framework_version: str, template_version: str
    ) -> Tuple[bool, List[str]]:
        """Check template version compatibility.
        
        Args:
            template: Template name
            framework_version: Framework version
            template_version: Template version
            
        Returns:
            Tuple[bool, List[str]]: (is_compatible, list of incompatibility reasons)
        """
        if template not in self.template_requirements:
            return False, [f"Unknown template: {template}"]

        if template_version not in self.template_requirements[template]:
            return False, [f"Unknown template version: {template_version}"]

        requirement = self.template_requirements[template][template_version]
        reasons = []

        if not requirement.is_compatible(framework_version):
            reasons.append(
                f"Framework version {framework_version} is not compatible with template version {template_version}"
            )

        return len(reasons) == 0, reasons

    def get_compatible_versions(
        self, framework: str, current_version: str
    ) -> List[str]:
        """Get list of compatible versions for a framework.
        
        Args:
            framework: Framework name
            current_version: Current framework version
            
        Returns:
            List[str]: List of compatible versions
        """
        if framework not in self.framework_requirements:
            return []

        compatible_versions = []
        for ver, req in self.framework_requirements[framework].items():
            if req.is_compatible(current_version):
                compatible_versions.append(ver)

        return sorted(compatible_versions, key=version.parse)

    def get_required_dependencies(
        self, framework: str, version: str
    ) -> Dict[str, str]:
        """Get required dependencies for a framework version.
        
        Args:
            framework: Framework name
            version: Framework version
            
        Returns:
            Dict[str, str]: Dictionary of required dependencies and their versions
        """
        if (framework in self.framework_requirements and 
            version in self.framework_requirements[framework]):
            return self.framework_requirements[framework][version].required_dependencies
        return {}
