# NADOO Migration Framework

A powerful, Git-based migration framework for NADOO Framework projects. This tool helps you:
- Migrate older NADOO Framework projects to newer versions
- Convert non-NADOO projects to NADOO Framework projects
- Manage dependencies in NADOO Framework projects

## Installation

You can install the NADOO Migration Framework using pip:

```bash
pip install nadoo-migration-framework
```

Or using Poetry:

```bash
poetry add nadoo-migration-framework
```

After installation, the following commands will be available globally in your terminal:

- `nadoo` - Main command with all subcommands
- `nadoo-init` - Quick command to create new projects
- `nadoo-migrate` - Quick command to run migrations
- `nadoo-add` - Quick command to add packages

## Usage

### Creating a New Project

Create a new NADOO Framework project:

```bash
# Using the main command
nadoo init my-project

# Or using the quick command
nadoo-init my-project

# Specify a custom path
nadoo init my-project --path /path/to/projects
```

### Migrating a Project

To migrate a project to the latest NADOO Framework version:

```bash
# In your project directory
nadoo migrate

# Or using the quick command
nadoo-migrate

# Specify a project path
nadoo migrate /path/to/project

# Force migration even if checks fail
nadoo migrate --force
```

The migration tool will:
1. Analyze your project structure
2. Detect if it's a NADOO Framework project or not
3. Determine required migrations
4. Apply migrations with Git-based version control

### Adding Packages

To add a package to your NADOO Framework project:

```bash
# Using the main command
nadoo add package-name

# Or using the quick command
nadoo-add package-name

# Add as development dependency
nadoo add package-name --dev
```

This will:
1. Add the package to your project's dependencies
2. Update your project configuration
3. Install the package using your package manager

## Quick Start: Adding NADOO to Your Project

1. Install the package:
```bash
pip install nadoo-migration-framework
```

2. Create `.github/workflows/nadoo-check.yml` in your project:
```yaml
name: NADOO Framework Check

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]
  schedule:
    - cron: '0 0 * * *'  # Daily check

jobs:
  check-nadoo-compatibility:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'
      - name: Install NADOO Migration Framework
        run: |
          python -m pip install --upgrade pip
          pip install nadoo-migration-framework
      - name: Check NADOO Framework Compatibility
        id: check
        continue-on-error: true
        run: |
          nadoo check --json > nadoo-check.json
```

That's it! The workflow will now:

1. Check your project daily for NADOO compatibility
2. Create issues if migration is needed
3. Automatically create PRs with migration changes
4. Keep your project up to date with the latest NADOO standards

## What Happens Next?

1. If your project needs migration:
   - An issue will be created explaining what needs to be changed
   - A PR will be created with automatic migrations
   - You can review and merge the changes

2. If your project is compatible:
   - The check will pass silently
   - You'll be notified of any new updates

3. If migration fails:
   - An issue will be created with details
   - You can run `nadoo migrate --debug` locally to investigate

## Command Reference

### Main Command (`nadoo`)

The main command with all functionality:

```bash
nadoo [COMMAND] [OPTIONS]

Commands:
  init      Create a new NADOO Framework project
  migrate   Migrate a project to the latest version
  add       Add a package to the project
```

### Quick Commands

Standalone commands for common operations:

- `nadoo-init`: Create new projects
  ```bash
  nadoo-init PROJECT_NAME [--path PATH]
  ```

- `nadoo-migrate`: Run migrations
  ```bash
  nadoo-migrate [PROJECT_PATH] [--force]
  ```

- `nadoo-add`: Add packages
  ```bash
  nadoo-add PACKAGE_NAME [--dev]
  ```

## Features

- **Intelligent Project Analysis**: Automatically detects project type and structure
- **Git Integration**: All migrations are tracked with Git commits
- **Safe Migrations**: Automatic rollback on failure
- **Package Management**: Integrated with NADOO Framework package management
- **Extensible**: Easy to add new migration strategies
- **Global Commands**: Quick access to common operations

## Development

To contribute to the NADOO Migration Framework:

1. Clone the repository:
```bash
git clone https://github.com/NADOOIT/nadoo-migration-framework.git
cd nadoo-migration-framework
```

2. Install dependencies:
```bash
poetry install
```

3. Run tests:
```bash
poetry run pytest
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
