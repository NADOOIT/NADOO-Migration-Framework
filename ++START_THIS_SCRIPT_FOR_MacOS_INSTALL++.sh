#!/bin/bash

# Config file for default Python version
CONFIG_FILE=".nadoo_config"
DEFAULT_PYTHON_VERSION="3.12"
DRY_RUN=false
RUN_TESTS=false

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Error: This script is only for macOS systems"
    exit 1
fi

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -reinstall)
            REINSTALL=true
            shift
            ;;
        -python-version)
            if [ -n "$2" ]; then
                PYTHON_VERSION="$2"
                shift 2
            else
                echo "Error: Python version argument is missing"
                exit 1
            fi
            ;;
        -set-default-python)
            if [ -n "$2" ]; then
                echo "PYTHON_VERSION=$2" > "$CONFIG_FILE"
                echo "Default Python version has been set to $2"
                PYTHON_VERSION="$2"
                shift 2
            else
                echo "Error: Python version argument is missing"
                exit 1
            fi
            ;;
        -run-tests)
            RUN_TESTS=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [-reinstall] [-python-version X.Y] [-set-default-python X.Y] [-run-tests] [--dry-run]"
            exit 1
            ;;
    esac
done

# Install or update bats-core for shell script testing if running tests
if [ "$RUN_TESTS" = "true" ]; then
    if ! command -v bats &> /dev/null; then
        echo " Installing bats-core for shell script testing..."
        brew install bats-core
    else
        echo " Updating bats-core..."
        brew upgrade bats-core
    fi
fi

# If dry run, simulate actions and exit
if [ "$DRY_RUN" = "true" ]; then
    echo "[Dry Run] Checking if Homebrew is installed..."
    if ! command -v brew &> /dev/null; then
        echo "[Dry Run] Homebrew would be installed."
    else
        echo "[Dry Run] Homebrew is already installed."
    fi

    echo "[Dry Run] Checking if bats-core is installed..."
    if ! command -v bats &> /dev/null; then
        echo "[Dry Run] bats-core would be installed."
    else
        echo "[Dry Run] bats-core is already installed."
    fi

    echo "[Dry Run] Would check for existing virtual environment..."
    if [ ! -d ".venv" ]; then
        echo "[Dry Run] Virtual environment would be created."
    else
        echo "[Dry Run] Virtual environment already exists."
    fi

    echo "[Dry Run] Would check for pyproject.toml in nadoo_migration_framework directory..."
    if [ -f "$(dirname "$0")/nadoo_migration_framework/pyproject.toml" ]; then
        echo "[Dry Run] pyproject.toml exists."
    else
        echo "[Dry Run] pyproject.toml is missing."
    fi

    exit 0
fi

# Check for reinstall flag
if [ "$REINSTALL" = "true" ]; then
    echo " Reinstallation requested. Cleaning up existing environment..."
    rm -rf .venv
    echo " Virtual environment cleaned."
fi

# Check if .venv already exists
if [ -d ".venv" ]; then
    echo " Virtual environment exists. Activating..."
    source .venv/bin/activate
    python_version=$(python3 -V | cut -d' ' -f2)
    echo " Active Python Version: $python_version"
else
    # INSTALLATION
    echo " Setting up NADOO Migration Framework development environment..."
    
    # Install or update uv
    if ! command -v uv &> /dev/null; then
        echo " Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    else
        echo " uv is already installed, updating to latest version..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi

    # Create virtual environment with specified Python version
    echo " Creating virtual environment with Python $PYTHON_VERSION..."
    uv python install "$PYTHON_VERSION"
    uv venv .venv
    echo " Virtual environment created with Python $PYTHON_VERSION"
fi

# Activate the virtual environment
source .venv/bin/activate

# Change to the directory containing the original pyproject.toml
cd "$(dirname "$0")/nadoo_migration_framework"

# Install project dependencies
echo "Installing project dependencies..."
uv pip install -e ".[dev]"  # This installs both main and dev dependencies from pyproject.toml

# Change back to the original directory for running tests
cd -

# Run bats tests if the flag is set
if [ "$RUN_TESTS" = "true" ]; then
    if [ -f "tests/test_install_script.bats" ]; then
        echo "Running bats tests..."
        bats tests/test_install_script.bats
        exit 0
    else
        echo "Bats test file not found."
        exit 1
    fi
fi

# Ensure we are in the nadoo_migration_framework directory for briefcase
cd "$(dirname "$0")/nadoo_migration_framework"

# Debug: Print current directory and list contents
pwd
ls -la

# Briefcase dev ausführen
briefcase dev
