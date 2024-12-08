"""Tests for database migrations."""

import pytest
import sqlite3
from pathlib import Path

from nadoo_migration_framework.migrations.database_migrations import (
    AddColumnMigration,
    CreateIndexMigration,
    ModifyForeignKeyMigration,
)


@pytest.fixture
def test_db(tmp_path):
    """Create a test database with a sample table."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # Create test tables
    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            user_id INTEGER
        )
    """
    )

    # Add some test data
    cursor.execute("INSERT INTO users (username) VALUES (?)", ("testuser",))
    cursor.execute("INSERT INTO posts (title, user_id) VALUES (?, ?)", ("Test Post", 1))

    conn.commit()
    conn.close()

    return db_path


def test_add_column_migration(test_db):
    """Test adding a new column to a table."""
    migration = AddColumnMigration(
        table_name="users",
        column_name="email",
        column_type="TEXT",
        default_value="'user@example.com'",
    )
    migration._connect_db(str(test_db))

    # Verify migration is needed
    assert migration.check_if_needed()

    # Apply migration
    migration._up()

    # Verify column was added
    cursor = migration._cursor
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    assert "email" in columns

    # Verify default value
    cursor.execute("SELECT email FROM users WHERE id=1")
    assert cursor.fetchone()[0] == "user@example.com"

    # Test rollback
    migration._down()

    # Verify column was removed
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    assert "email" not in columns

    migration._close_db()


def test_create_index_migration(test_db):
    """Test creating an index on a table."""
    migration = CreateIndexMigration(
        table_name="users", index_name="idx_username", columns=["username"], unique=True
    )
    migration._connect_db(str(test_db))

    # Verify migration is needed
    assert migration.check_if_needed()

    # Apply migration
    migration._up()

    # Verify index was created
    cursor = migration._cursor
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?", ("idx_username",)
    )
    assert cursor.fetchone() is not None

    # Test rollback
    migration._down()

    # Verify index was removed
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?", ("idx_username",)
    )
    assert cursor.fetchone() is None

    migration._close_db()


def test_modify_foreign_key_migration(test_db):
    """Test modifying foreign key relationships."""
    migration = ModifyForeignKeyMigration(
        table_name="posts",
        foreign_key={"user_id": "INTEGER"},
        referenced_table="users",
        referenced_column="id",
        on_delete="CASCADE",
    )
    migration._connect_db(str(test_db))

    # Verify migration is needed
    assert migration.check_if_needed()

    # Apply migration
    migration._up()

    # Verify foreign key was added
    cursor = migration._cursor
    cursor.execute("PRAGMA foreign_key_list(posts)")
    foreign_keys = cursor.fetchall()
    assert any(
        fk[2] == "users" and fk[3] == "user_id" and fk[4] == "id" and fk[6] == "CASCADE"
        for fk in foreign_keys
    )

    # Test data integrity
    cursor.execute("SELECT title FROM posts WHERE user_id=1")
    assert cursor.fetchone()[0] == "Test Post"

    # Test rollback
    migration._down()

    # Verify original schema was restored
    cursor.execute("PRAGMA foreign_key_list(posts)")
    foreign_keys = cursor.fetchall()
    assert not any(fk[2] == "users" and fk[3] == "user_id" for fk in foreign_keys)

    migration._close_db()


def test_database_backup_restore(test_db):
    """Test database backup and restore functionality."""
    migration = AddColumnMigration(table_name="users", column_name="email", column_type="TEXT")

    # Create backup
    migration._backup_database(str(test_db))
    assert Path(str(test_db) + '.bak').exists()

    # Modify database
    conn = sqlite3.connect(str(test_db))
    cursor = conn.cursor()
    cursor.execute("DROP TABLE users")
    conn.commit()
    conn.close()

    # Restore backup
    migration._restore_backup(str(test_db))

    # Verify database was restored
    conn = sqlite3.connect(str(test_db))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    assert cursor.fetchone() is not None
    conn.close()

    # Cleanup
    backup_file = Path(str(test_db) + '.bak')
    if backup_file.exists():
        backup_file.unlink()
