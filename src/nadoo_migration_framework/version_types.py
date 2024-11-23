"""Version types for NADOO Migration Framework."""

from enum import Enum


class VersionType(Enum):
    """Types of version changes."""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
