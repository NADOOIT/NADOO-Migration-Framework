#!/bin/bash

# Config file for default Python version
CONFIG_FILE=".nadoo_config"
DEFAULT_PYTHON_VERSION="3.12"
DRY_RUN=false

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

# Install or update bats-core for shell script testing
if ! command -v bats &> /dev/null; then
    echo " Installing bats-core for shell script testing..."
    brew install bats-core
else
    echo " Updating bats-core..."
    brew upgrade bats-core
fi

# Read default Python version from config if it exists
if [ -f "$CONFIG_FILE" ]; then
    PYTHON_VERSION=$(grep "^PYTHON_VERSION=" "$CONFIG_FILE" | cut -d'=' -f2)
else
    PYTHON_VERSION="$DEFAULT_PYTHON_VERSION"
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
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [-reinstall] [-python-version X.Y] [-set-default-python X.Y] [--dry-run]"
            exit 1
            ;;
    esac
done

# If dry run, exit here for testing
if [ "$DRY_RUN" = "true" ]; then
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
        echo " Updating uv to latest version..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi

    # Ensure uv is in PATH after installation
    if [ -f "$HOME/.profile" ]; then
        source "$HOME/.profile"
    fi
    
    # Create virtual environment with specified Python version
    echo " Creating virtual environment with Python $PYTHON_VERSION..."
    
    # Install Python version using uv
    uv python install "$PYTHON_VERSION"
    
    # Create the virtual environment
    uv venv .venv
    
    echo " Virtual environment created with Python $PYTHON_VERSION"
fi

# Install project dependencies
echo " Installing project dependencies..."
source .venv/bin/activate

# Install all dependencies using uv and pyproject.toml
echo " Installing dependencies..."
uv pip install -e ".[dev]"  # This installs both main and dev dependencies from pyproject.toml

echo " Installation complete! Your development environment is ready."
echo " You can now run tests with: pytest"
echo " To activate the environment in a new terminal, run: source .venv/bin/activate"
