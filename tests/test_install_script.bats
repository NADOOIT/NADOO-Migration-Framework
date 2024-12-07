#!/usr/bin/env bats

setup() {
    # Create a temporary directory for testing
    export TEST_DIR="$(mktemp -d)"
    export ORIGINAL_DIR="$PWD"
    cp "++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh" "$TEST_DIR/"
    cp "src/nadoo_migration_framework/pyproject.toml" "$TEST_DIR/"
    cd "$TEST_DIR"
}

teardown() {
    # Clean up after tests
    cd "$ORIGINAL_DIR"
    rm -rf "$TEST_DIR"
}

@test "script exists and is executable" {
    [ -f "./++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh" ]
    [ -x "./++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh" ]
}

@test "default Python version is 3.12" {
    DEFAULT_PYTHON_VERSION=$(grep "DEFAULT_PYTHON_VERSION=" "./++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh" | cut -d'"' -f2)
    [ "$DEFAULT_PYTHON_VERSION" = "3.12" ]
}

@test "can set custom Python version" {
    run ./++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh -python-version 3.11 --dry-run
    [ "$status" -eq 0 ]
}

@test "can set default Python version" {
    run ./++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh -set-default-python 3.11 --dry-run
    [ "$status" -eq 0 ]
    [ -f ".nadoo_config" ]
    grep "PYTHON_VERSION=3.11" ".nadoo_config"
}

@test "reinstall flag cleans existing environment" {
    # Create a dummy virtual environment
    mkdir .venv
    touch .venv/dummy_file
    
    # Run with reinstall flag
    ./++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh -reinstall --dry-run
    
    # Check if .venv still exists (it should in dry-run mode)
    [ -d ".venv" ]
}

@test "script handles invalid arguments" {
    run ./++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh -invalid-arg
    [ "$status" -eq 1 ]
    echo "output: ${lines[@]}"
    [[ "${output}" =~ "Unknown option: -invalid-arg" ]]
}

@test "script requires Python version with -python-version flag" {
    run ./++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh -python-version
    [ "$status" -eq 1 ]
    [[ "${output}" =~ "Error: Python version argument is missing" ]]
}

@test "script requires Python version with -set-default-python flag" {
    run ./++START_THIS_SCRIPT_FOR_MacOS_INSTALL++.sh -set-default-python
    [ "$status" -eq 1 ]
    [[ "${output}" =~ "Error: Python version argument is missing" ]]
}

@test "script verifies macOS environment" {
    # This test will pass on macOS and fail on other systems
    [[ "$OSTYPE" == "darwin"* ]]
}
