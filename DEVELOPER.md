# NADOO Migration Framework - Developer Guide

## Recent Changes (v0.2.1)
- Fixed circular import issues in migration engine
- Improved code organization with dedicated migration_engine module
- Enhanced error handling for migration operations
- Fixed PyPI publishing workflow

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/NADOOIT/nadoo-migration-framework.git
cd nadoo-migration-framework
```

2. Install development dependencies:
```bash
pip install poetry
poetry install
```

## Making Changes

1. Create a new branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes
3. Run tests:
```bash
poetry run pytest
```

4. Format code:
```bash
poetry run black .
```

## Publishing to PyPI

### Prerequisites
- PyPI account with maintainer access
- PyPI API token (get from https://pypi.org/manage/account/token/)

### Publishing Steps

1. Update version numbers:
   - Edit `pyproject.toml`:
     - Update `version` under `[tool.poetry]`
     - Update `version` under `[tool.nadoo]`
   
2. Build and publish:
```bash
# Build the package
poetry build

# Publish to PyPI
poetry publish --build
```

Alternatively, use our built-in command:
```bash
nadoo-publish --bump patch  # For bug fixes
nadoo-publish --bump minor  # For new features
nadoo-publish --bump major  # For breaking changes
```

### Version Numbering
- MAJOR version for incompatible API changes
- MINOR version for new functionality in a backward compatible manner
- PATCH version for backward compatible bug fixes

## Common Issues

### Circular Imports
If you encounter circular import issues:
1. Move the problematic class to its own module
2. Use local imports within functions where necessary
3. Update `__init__.py` files to maintain backward compatibility

### Publishing Issues
If you encounter publishing issues:
1. Ensure you have the latest poetry version: `pip install --upgrade poetry`
2. Check your PyPI token: `poetry config pypi-token.pypi`
3. Try building first: `poetry build`
4. Then publish separately: `poetry publish`

## Getting Help
- Open an issue on GitHub
- Contact NADOO IT team at info@nadoo.it
- Check the [documentation](https://github.com/NADOOIT/nadoo-migration-framework#readme)

## Code Organization

```
src/nadoo_migration_framework/
├── migrations/
│   ├── __init__.py
│   ├── migration_engine.py    # Core migration logic
│   ├── database_migrations.py # Database-specific migrations
│   └── toga_migrations.py     # UI-related migrations
├── cli.py                     # Command-line interface
├── manager.py                 # Migration management
└── version_management.py      # Version handling
```

## Testing

Run specific test files:
```bash
poetry run pytest tests/test_migrations.py -v
```

Run with coverage:
```bash
poetry run pytest --cov=nadoo_migration_framework
```

## Documentation

Update documentation when making changes:
1. Update README.md for user-facing changes
2. Update docstrings for API changes
3. Update CHANGELOG.md with version changes

## Release Checklist

1. Update version numbers
2. Run full test suite
3. Update documentation
4. Create GitHub release
5. Publish to PyPI
6. Verify installation works: `pip install --upgrade nadoo-migration-framework`
