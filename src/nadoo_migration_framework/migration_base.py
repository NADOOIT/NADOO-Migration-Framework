"""Base class for all migrations in the NADOO Migration Framework.

This module provides the foundation for creating migrations that can be used to
transform NADOO projects from one structure to another. Each migration should
inherit from this base class and implement the required methods.

Example:
    ```python
    class MyMigration(MigrationBase):
        def __init__(self):
            super().__init__()
            self.migration_id = "0001_my_migration"
            self.description = "Performs specific transformation on the project"

        def migrate(self) -> bool:
            # Implementation of the migration
            return True

        def rollback(self) -> bool:
            # Implementation of the rollback
            return True
    ```
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging


class MigrationBase(ABC):
    """Base class for all migrations.
    
    This abstract class defines the interface that all migrations must implement.
    It provides basic functionality for migration identification, logging, and
    state management.

    Attributes:
        migration_id (str): Unique identifier for the migration
        description (str): Human-readable description of what the migration does
        logger (logging.Logger): Logger instance for the migration
        state (Dict[str, Any]): State dictionary to store migration-specific data
    """

    def __init__(self):
        """Initialize the migration with default values."""
        self.migration_id: str = ""
        self.description: str = ""
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self.state: Dict[str, Any] = {}

    @abstractmethod
    def migrate(self) -> bool:
        """Perform the migration.
        
        This method should implement the actual migration logic. It should be
        idempotent, meaning it can be safely run multiple times without causing
        issues.

        Returns:
            bool: True if migration was successful, False otherwise
        
        Raises:
            NotImplementedError: If the method is not implemented by the subclass
        """
        pass

    @abstractmethod
    def rollback(self) -> bool:
        """Rollback the migration.
        
        This method should implement the logic to undo the changes made by the
        migrate() method. It should also be idempotent.

        Returns:
            bool: True if rollback was successful, False otherwise
        
        Raises:
            NotImplementedError: If the method is not implemented by the subclass
        """
        pass

    def validate(self) -> bool:
        """Validate that the migration can be run.
        
        This method can be overridden by subclasses to add custom validation
        logic before running the migration.

        Returns:
            bool: True if validation passes, False otherwise
        """
        return bool(self.migration_id and self.description)

    def save_state(self, key: str, value: Any) -> None:
        """Save a value to the migration state.
        
        Args:
            key (str): Key to store the value under
            value (Any): Value to store
        """
        self.state[key] = value
        self.logger.debug(f"Saved state: {key}={value}")

    def get_state(self, key: str, default: Any = None) -> Optional[Any]:
        """Retrieve a value from the migration state.
        
        Args:
            key (str): Key to retrieve
            default (Any, optional): Default value if key doesn't exist

        Returns:
            Optional[Any]: The stored value or default if not found
        """
        return self.state.get(key, default)
