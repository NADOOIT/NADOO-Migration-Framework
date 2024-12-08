"""Tests for the NADOO Brain migration."""

import pytest
from pathlib import Path
import tempfile
import shutil
import json

from nadoo_migration_framework.migrations.nadoo_brain_migration import NADOOBrainMigration


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a sample Toga app
        app_dir = Path(temp_dir) / "sample_app"
        app_dir.mkdir()

        # Create main.py with a sample Toga app
        main_py = app_dir / "src" / "sample_app" / "main.py"
        main_py.parent.mkdir(parents=True)
        main_py.write_text(
            """
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class SampleApp(toga.App):
    def __init__(self):
        super().__init__()

    def startup(self):
        main_box = toga.Box()
        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

def main():
    return SampleApp()
"""
        )

        yield app_dir


def test_brain_migration_basic(temp_project):
    """Test basic Brain migration functionality."""
    migration = NADOOBrainMigration()
    migration.set_project_dir(temp_project)

    # Run migration
    migration._up()

    # Check if brain_config.json was created
    config_path = temp_project / "brain_config.json"
    assert config_path.exists()

    # Verify config content
    with open(config_path) as f:
        config = json.load(f)
        assert "brain" in config
        assert "process_manager" in config["brain"]
        assert "feed_manager" in config["brain"]

    # Check if main.py was transformed
    main_py = temp_project / "src" / "sample_app" / "main.py"
    content = main_py.read_text()

    # Verify Brain imports
    assert "from nadoo.brain import Brain, ProcessManager, FeedManager" in content
    assert "from nadoo.brain.feed import Feed" in content

    # Verify Brain integration
    assert "class SampleApp(toga.App, Brain):" in content
    assert "process_manager = ProcessManager()" in content
    assert "feed_manager = FeedManager()" in content

    # Verify feed methods
    assert "def create_feed" in content
    assert "def send_to_feed" in content


def test_brain_migration_rollback(temp_project):
    """Test Brain migration rollback functionality."""
    migration = NADOOBrainMigration()
    migration.set_project_dir(temp_project)

    # Store original content
    main_py = temp_project / "src" / "sample_app" / "main.py"
    original_content = main_py.read_text()

    # Run migration
    migration._up()

    # Verify changes were made
    assert main_py.read_text() != original_content

    # Rollback migration
    migration._down()

    # Verify content was restored
    assert main_py.read_text() == original_content

    # Verify config was removed
    config_path = temp_project / "brain_config.json"
    assert not config_path.exists()


def test_brain_migration_multiple_files(temp_project):
    """Test Brain migration with multiple Python files."""
    # Create additional files
    utils_py = temp_project / "src" / "sample_app" / "utils.py"
    utils_py.write_text(
        """
def helper_function():
    return "Helper"
"""
    )

    migration = NADOOBrainMigration()
    migration.set_project_dir(temp_project)

    # Run migration
    migration._up()

    # Verify only main app file was transformed
    utils_content = utils_py.read_text()
    assert "from nadoo.brain" not in utils_content
    assert "Brain" not in utils_content


def test_brain_migration_error_handling(temp_project):
    """Test Brain migration error handling."""
    # Create invalid Python file
    main_py = temp_project / "src" / "sample_app" / "main.py"
    main_py.write_text("invalid python code {")

    migration = NADOOBrainMigration()
    migration.set_project_dir(temp_project)

    # Verify migration raises error
    with pytest.raises(Exception):
        migration._up()


def test_brain_migration_existing_brain(temp_project):
    """Test Brain migration with existing Brain integration."""
    # Create app with existing Brain integration
    main_py = temp_project / "src" / "sample_app" / "main.py"
    main_py.write_text(
        """
from nadoo.brain import Brain
import toga

class SampleApp(toga.App, Brain):
    def __init__(self):
        super().__init__()
"""
    )

    migration = NADOOBrainMigration()
    migration.set_project_dir(temp_project)

    # Run migration
    migration._up()

    # Verify no duplicate Brain inheritance
    content = main_py.read_text()
    assert content.count("Brain") == 2  # Import and class definition


def test_brain_migration_config_customization(temp_project):
    """Test Brain migration config customization."""
    migration = NADOOBrainMigration()
    migration.set_project_dir(temp_project)

    # Run migration
    migration._up()

    # Modify config
    config_path = temp_project / "brain_config.json"
    with open(config_path) as f:
        config = json.load(f)

    config["brain"]["process_manager"]["max_processes"] = 20

    with open(config_path, "w") as f:
        json.dump(config, f)

    # Run migration again
    migration._up()

    # Verify custom config was preserved
    with open(config_path) as f:
        new_config = json.load(f)
    assert new_config["brain"]["process_manager"]["max_processes"] == 20


def test_brain_migration_feed_functionality(temp_project):
    """Test Brain migration feed functionality."""
    migration = NADOOBrainMigration()
    migration.set_project_dir(temp_project)

    # Run migration
    migration._up()

    # Check feed-related code
    main_py = temp_project / "src" / "sample_app" / "main.py"
    content = main_py.read_text()

    # Verify feed manager setup
    assert "feed_manager = FeedManager()" in content

    # Verify feed methods
    assert "def create_feed(self, name: str, data: Any) -> Feed:" in content
    assert "def send_to_feed(self, feed_name: str, data: Any):" in content

    # Verify feed manager initialization in __init__
    assert "feed_manager" in content.split("def __init__")[1].split("def")[0]
