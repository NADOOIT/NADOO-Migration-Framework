# NADOO Migration Framework

A powerful, Git-based migration framework for managing codebase changes in NADOO Framework projects.

## Features

- Git-based migrations with automatic commits and rollbacks
- Dependency management between migrations
- Topological sorting of migrations
- State tracking of applied migrations
- Clean rollback mechanism
- Support for both forward and backward migrations

## Installation

```bash
pip install nadoo-migration-framework
```

## Usage

### Basic Migration

```python
from nadoo_migration_framework import Migration

class MyMigration(Migration):
    def __init__(self):
        super().__init__()
        self.dependencies = []  # List any dependencies here
    
    def check_if_needed(self) -> bool:
        # Check if this migration should be applied
        return True
    
    def _up(self) -> None:
        # Implement your migration logic here
        pass
    
    def _down(self) -> None:
        # Implement your rollback logic here
        pass
```

### Using the Migration Manager

```python
from nadoo_migration_framework import MigrationManager

# Initialize the manager
manager = MigrationManager("path/to/your/app")

# Register your migrations
manager.register_migration(MyMigration)

# Run all pending migrations
manager.migrate()

# Or migrate to a specific version
manager.migrate(target_version="MyMigration")

# Rollback the last migration
manager.rollback()
```

## Contributing

We welcome contributions! Please feel free to submit a Pull Request.
