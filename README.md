# NADOO Migration Framework

A powerful framework for migrating NADOO projects, providing tools and utilities to streamline the migration process.

## Quick Start

### Prerequisites
- macOS (for now)
- Git
- Terminal access

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/nadooit/NADOO-Migration-Framework.git
   cd NADOO-Migration-Framework
   ```

2. Run the installation script:
   ```bash
   ./++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh
   ```

   Options:
   - `-reinstall`: Clean and reinstall everything
   - `-python-version X.Y`: Use specific Python version (default: 3.12)
   - `-set-default-python X.Y`: Set default Python version for future installs

## MacOS Installation Script Usage

The `++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh` script is used to set up and run the NADOO Migration Framework application on macOS. Below are the available flags and example usage:

### Flags

- `-set-default-python X.Y`: Sets the default Python version to X.Y for the virtual environment.
- `-reinstall`: Removes the existing virtual environment and creates a new one.
- `-python-version X.Y`: Specifies a custom Python version for the virtual environment.
- `-run-tests`: Runs the Bats tests after setting up the environment.
- `--dry-run`: Executes the script in dry-run mode, showing what would be done without making any changes.

### Example Commands

#### Run the Application
To set the default Python version and run the application:
```bash
./++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh -set-default-python 3.12
```

#### Run Tests
To set the default Python version, set up the environment, and run tests:
```bash
./++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh -set-default-python 3.12 -run-tests
```

#### Reinstall the Environment
To reinstall the environment with a specific Python version:
```bash
./++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh -reinstall -python-version 3.12
```

#### Dry Run
To see what the script would do without making changes:
```bash
./++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh --dry-run
```

## Running Tests

To run the tests, use the following command:

```bash
pytest --ignore=tests/django --maxfail=1 --disable-warnings -q
```

This command will execute the test suite while ignoring the Django tests.

### Development

1. Activate the virtual environment (if not already active):
   ```bash
   source .venv/bin/activate
   ```

2. Run tests:
   ```bash
   # Run all tests
   pytest

   # Run tests with coverage
   pytest --cov=src/nadoo_migration_framework

   # Run tests in watch mode (great for TDD)
   pytest-watch  # or ptw for short
   ```

3. Start development:
   - The framework is installed in editable mode (`-e`)
   - Any changes to the code are immediately reflected
   - Use the CLI commands:
     ```bash
     nadoo-migrate  # Run migrations
     nadoo-init     # Initialize new project
     nadoo-publish  # Publish changes
     nadoo-update   # Update framework
     ```

### Testing

The project includes automated tests for both Python code and shell scripts:

1. Shell Script Tests:
   ```bash
   # Run all shell script tests
   bats tests/*.bats

   # Run specific test file
   bats tests/test_install_script.bats
   ```

   **Note:** During testing, the `pyproject.toml` file is copied to a temporary directory to ensure tests always use the latest version. This ensures that any updates to dependencies are reflected in the tests without affecting the original files.

2. Python Tests:
   ```bash
   # Run all tests
   pytest

   # Run tests with coverage
   pytest --cov=src/nadoo_migration_framework

   # Run tests in watch mode (great for TDD)
   pytest-watch  # or ptw for short
   ```

## Project Structure

```
NADOO-Migration-Framework/
├── src/
│   └── nadoo_migration_framework/  # Main package
├── tests/                          # Test files
├── pyproject.toml                  # Project configuration and dependencies
└── ++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh  # Installation script
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests to ensure everything works
5. Submit a pull request

## License

MIT License - see the [LICENSE](LICENSE) file for details.
