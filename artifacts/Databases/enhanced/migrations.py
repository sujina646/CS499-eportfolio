from typing import List, Dict
import sqlite3
from datetime import datetime

class Migration:
    def __init__(self, version: int, description: str, up_sql: str, down_sql: str):
        self.version = version
        self.description = description
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.applied_at = None

MIGRATIONS: List[Migration] = [
    Migration(
        version=1,
        description="Initial schema",
        up_sql='''
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY,
                destination TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''',
        down_sql='''
            DROP TABLE IF EXISTS trips;
            DROP TABLE IF EXISTS schema_migrations;
        '''
    ),
    Migration(
        version=2,
        description="Add categories and tags",
        up_sql='''
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE tags (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE trip_categories (
                trip_id INTEGER,
                category_id INTEGER,
                PRIMARY KEY (trip_id, category_id),
                FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            );
            
            CREATE TABLE trip_tags (
                trip_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (trip_id, tag_id),
                FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            );
            
            -- Add date range columns to trips
            ALTER TABLE trips ADD COLUMN start_date DATE;
            ALTER TABLE trips ADD COLUMN end_date DATE;
            
            -- Add soft delete support
            ALTER TABLE trips ADD COLUMN deleted_at TIMESTAMP;
            
            -- Add full-text search
            CREATE VIRTUAL TABLE trips_fts USING fts5(
                destination,
                content='trips',
                content_rowid='id'
            );
            
            -- Trigger to keep FTS index up to date
            CREATE TRIGGER trips_ai AFTER INSERT ON trips BEGIN
                INSERT INTO trips_fts(rowid, destination)
                VALUES (new.id, new.destination);
            END;
            
            CREATE TRIGGER trips_ad AFTER DELETE ON trips BEGIN
                INSERT INTO trips_fts(trips_fts, rowid, destination)
                VALUES('delete', old.id, old.destination);
            END;
            
            CREATE TRIGGER trips_au AFTER UPDATE ON trips BEGIN
                INSERT INTO trips_fts(trips_fts, rowid, destination)
                VALUES('delete', old.id, old.destination);
                INSERT INTO trips_fts(rowid, destination)
                VALUES (new.id, new.destination);
            END;
        ''',
        down_sql='''
            DROP TRIGGER IF EXISTS trips_au;
            DROP TRIGGER IF EXISTS trips_ad;
            DROP TRIGGER IF EXISTS trips_ai;
            DROP TABLE IF EXISTS trips_fts;
            DROP TABLE IF EXISTS trip_tags;
            DROP TABLE IF EXISTS trip_categories;
            DROP TABLE IF EXISTS tags;
            DROP TABLE IF EXISTS categories;
            
            CREATE TABLE trips_temp AS 
            SELECT id, destination, created_at, updated_at 
            FROM trips;
            
            DROP TABLE trips;
            
            CREATE TABLE trips (
                id INTEGER PRIMARY KEY,
                destination TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            INSERT INTO trips 
            SELECT id, destination, created_at, updated_at 
            FROM trips_temp;
            
            DROP TABLE trips_temp;
        '''
    )
]

class MigrationManager:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._ensure_migrations_table()

    def _ensure_migrations_table(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def get_current_version(self) -> int:
        cursor = self.conn.execute(
            "SELECT MAX(version) FROM schema_migrations"
        )
        result = cursor.fetchone()
        return result[0] if result[0] is not None else 0

    def get_pending_migrations(self) -> List[Migration]:
        current_version = self.get_current_version()
        return [m for m in MIGRATIONS if m.version > current_version]

    def apply_migration(self, migration: Migration):
        try:
            self.conn.executescript(migration.up_sql)
            self.conn.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                (migration.version, migration.description)
            )
            self.conn.commit()
            migration.applied_at = datetime.now()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise Exception(f"Failed to apply migration {migration.version}: {str(e)}")

    def rollback_migration(self, migration: Migration):
        try:
            self.conn.executescript(migration.down_sql)
            self.conn.execute(
                "DELETE FROM schema_migrations WHERE version = ?",
                (migration.version,)
            )
            self.conn.commit()
            migration.applied_at = None
        except sqlite3.Error as e:
            self.conn.rollback()
            raise Exception(f"Failed to rollback migration {migration.version}: {str(e)}")

    def migrate(self, target_version: int = None):
        pending = self.get_pending_migrations()
        if target_version is not None:
            pending = [m for m in pending if m.version <= target_version]
        
        for migration in pending:
            self.apply_migration(migration)

    def rollback(self, steps: int = 1):
        current_version = self.get_current_version()
        applicable_migrations = [
            m for m in reversed(MIGRATIONS)
            if m.version <= current_version
        ][:steps]
        
        for migration in applicable_migrations:
            self.rollback_migration(migration) 
