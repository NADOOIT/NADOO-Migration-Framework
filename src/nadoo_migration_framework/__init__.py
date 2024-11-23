"""NADOO Migration Framework - A powerful, Git-based migration framework."""

from .base import Migration
from .manager import MigrationManager

__version__ = "0.1.0"
__all__ = ["Migration", "MigrationManager"]
