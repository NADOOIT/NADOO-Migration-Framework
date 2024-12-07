"""Database migrations for common operations."""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from nadoo_migration_framework.base import Migration


class DatabaseMigration(Migration):
    """Base class for database migrations."""

    def __init__(self):
        """Initialize database migration."""
        super().__init__()
        self._connection: Optional[sqlite3.Connection] = None
        self._cursor: Optional[sqlite3.Cursor] = None
        self._backup_file: Optional[Path] = None

    def _connect_db(self, db_path: str) -> None:
        """Connect to the database."""
        self._connection = sqlite3.connect(db_path)
        # Enable foreign key support
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._cursor = self._connection.cursor()

    def _close_db(self) -> None:
        """Close database connection."""
        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()
            self._connection = None
            self._cursor = None

    def _backup_database(self, db_path: str) -> None:
        """Create a backup of the database."""
        source = sqlite3.connect(db_path)
        self._backup_file = Path(db_path + '.bak')
        backup = sqlite3.connect(str(self._backup_file))
        source.backup(backup)
        source.close()
        backup.close()

    def _restore_backup(self, db_path: str) -> None:
        """Restore database from backup."""
        if self._backup_file and self._backup_file.exists():
            self._close_db()
            backup = sqlite3.connect(str(self._backup_file))
            target = sqlite3.connect(db_path)
            backup.backup(target)
            backup.close()
            target.close()
            self._backup_file.unlink()


class AddColumnMigration(DatabaseMigration):
    """Migration to add a new column to a table."""

    def __init__(self, table_name: str, column_name: str, column_type: str, default_value: Any = None):
        """Initialize column addition migration."""
        super().__init__()
        self.version = "0.4.0"
        self.description = f"Add column {column_name} to table {table_name}"
        self.table_name = table_name
        self.column_name = column_name
        self.column_type = column_type
        self.default_value = default_value

    def check_version_compatibility(self) -> tuple[bool, list[str]]:
        """Check if the current version is compatible with this migration."""
        if not self.project_dir:
            return False, ["Project directory not set"]
        return True, []

    def check_if_needed(self) -> bool:
        """Check if migration is needed."""
        try:
            self._cursor.execute(f"PRAGMA table_info({self.table_name})")
            columns = [info[1] for info in self._cursor.fetchall()]
            return self.column_name not in columns
        except Exception:
            return False

    def _up(self) -> None:
        """Add the new column."""
        alter_sql = f"ALTER TABLE {self.table_name} ADD COLUMN {self.column_name} {self.column_type}"
        if self.default_value is not None:
            alter_sql += f" DEFAULT {self.default_value}"
        self._cursor.execute(alter_sql)
        self._connection.commit()

    def _down(self) -> None:
        """Remove the added column (if supported)."""
        # SQLite doesn't support dropping columns directly
        # We need to:
        # 1. Create a new table without the column
        # 2. Copy data from old table
        # 3. Drop old table
        # 4. Rename new table
        self._cursor.execute(f"PRAGMA table_info({self.table_name})")
        columns = [info[1] for info in self._cursor.fetchall() if info[1] != self.column_name]
        columns_str = ", ".join(columns)
        
        self._cursor.execute(f"""
            CREATE TABLE {self.table_name}_temp AS 
            SELECT {columns_str} 
            FROM {self.table_name}
        """)
        self._cursor.execute(f"DROP TABLE {self.table_name}")
        self._cursor.execute(f"ALTER TABLE {self.table_name}_temp RENAME TO {self.table_name}")
        self._connection.commit()


class CreateIndexMigration(DatabaseMigration):
    """Migration to create an index on specified columns."""

    def __init__(self, table_name: str, index_name: str, columns: List[str], unique: bool = False):
        """Initialize index creation migration."""
        super().__init__()
        self.version = "0.4.0"
        self.description = f"Create {'unique ' if unique else ''}index {index_name} on {table_name}"
        self.table_name = table_name
        self.index_name = index_name
        self.columns = columns
        self.unique = unique

    def check_version_compatibility(self) -> tuple[bool, list[str]]:
        """Check if the current version is compatible with this migration."""
        if not self.project_dir:
            return False, ["Project directory not set"]
        return True, []

    def check_if_needed(self) -> bool:
        """Check if migration is needed."""
        try:
            self._cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name=?", 
                               (self.index_name,))
            return not bool(self._cursor.fetchone())
        except Exception:
            return False

    def _up(self) -> None:
        """Create the index."""
        unique_str = "UNIQUE" if self.unique else ""
        columns_str = ", ".join(self.columns)
        self._cursor.execute(
            f"CREATE {unique_str} INDEX {self.index_name} ON {self.table_name} ({columns_str})"
        )
        self._connection.commit()

    def _down(self) -> None:
        """Remove the index."""
        self._cursor.execute(f"DROP INDEX IF EXISTS {self.index_name}")
        self._connection.commit()


class ModifyForeignKeyMigration(DatabaseMigration):
    """Migration to modify foreign key relationships."""

    def __init__(self, table_name: str, foreign_key: Dict[str, str], referenced_table: str,
                 referenced_column: str = "id", on_delete: str = "CASCADE"):
        """Initialize foreign key modification migration."""
        super().__init__()
        self.version = "0.4.0"
        self.description = f"Modify foreign key in {table_name}"
        self.table_name = table_name
        self.foreign_key = foreign_key
        self.referenced_table = referenced_table
        self.referenced_column = referenced_column
        self.on_delete = on_delete
        self._original_schema = None

    def check_version_compatibility(self) -> tuple[bool, list[str]]:
        """Check if the current version is compatible with this migration."""
        if not self.project_dir:
            return False, ["Project directory not set"]
        return True, []

    def check_if_needed(self) -> bool:
        """Check if migration is needed."""
        try:
            self._cursor.execute(f"PRAGMA foreign_key_list({self.table_name})")
            foreign_keys = self._cursor.fetchall()
            for fk in foreign_keys:
                if (fk[2] == self.referenced_table and 
                    fk[3] == list(self.foreign_key.keys())[0] and
                    fk[4] == self.referenced_column):
                    return False
            return True
        except Exception:
            return False

    def _up(self) -> None:
        """Modify the foreign key relationship."""
        # Get current table schema
        self._cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                           (self.table_name,))
        self._original_schema = self._cursor.fetchone()[0]

        # Get current table info
        self._cursor.execute(f"PRAGMA table_info({self.table_name})")
        columns = []
        primary_key = None
        for col in self._cursor.fetchall():
            name = col[1]
            type_ = col[2]
            notnull = "NOT NULL" if col[3] else ""
            pk = col[5]
            if pk > 0:
                primary_key = name
            columns.append(f"{name} {type_} {notnull}")

        # Create new table with modified foreign key
        create_sql = f"""
            CREATE TABLE {self.table_name}_new (
                {', '.join(columns)},
                PRIMARY KEY ({primary_key}),
                FOREIGN KEY ({list(self.foreign_key.keys())[0]}) 
                REFERENCES {self.referenced_table}({self.referenced_column})
                ON DELETE {self.on_delete}
            )
        """
        
        # Create new table and copy data
        self._cursor.execute(create_sql)
        self._cursor.execute(f"INSERT INTO {self.table_name}_new SELECT * FROM {self.table_name}")
        self._cursor.execute(f"DROP TABLE {self.table_name}")
        self._cursor.execute(f"ALTER TABLE {self.table_name}_new RENAME TO {self.table_name}")
        self._connection.commit()

    def _down(self) -> None:
        """Restore the original schema."""
        if self._original_schema:
            # Save current data
            self._cursor.execute(f"CREATE TABLE {self.table_name}_backup AS SELECT * FROM {self.table_name}")
            
            # Restore original schema
            self._cursor.execute(f"DROP TABLE {self.table_name}")
            self._cursor.execute(self._original_schema)
            
            # Restore data
            self._cursor.execute(f"INSERT INTO {self.table_name} SELECT * FROM {self.table_name}_backup")
            self._cursor.execute(f"DROP TABLE {self.table_name}_backup")
            self._connection.commit()
