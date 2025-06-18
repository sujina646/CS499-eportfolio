import sqlite3
from sqlite3 import Connection
from typing import List, Optional
from contextlib import contextmanager
from queue import Queue
import threading
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabasePool:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(DatabasePool, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_name: str, max_connections: int = 5):
        if not hasattr(self, 'initialized'):
            self.db_name = db_name
            self.max_connections = max_connections
            self.connections: Queue[Connection] = Queue(maxsize=max_connections)
            self.initialized = True
            self._initialize_pool()

    def _initialize_pool(self):
        for _ in range(self.max_connections):
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.connections.put(conn)

    @contextmanager
    def get_connection(self) -> Connection:
        connection = self.connections.get()
        try:
            yield connection
        finally:
            self.connections.put(connection)

    def close_all(self):
        while not self.connections.empty():
            conn = self.connections.get()
            conn.close()

class DatabaseManager:
    def __init__(self, db_name: str):
        self.pool = DatabasePool(db_name)
        self.backup_dir = 'database_backups'
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_backup(self) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(self.backup_dir, f'trips_backup_{timestamp}.db')
        
        with self.pool.get_connection() as source_conn:
            backup_conn = sqlite3.connect(backup_path)
            source_conn.backup(backup_conn)
            backup_conn.close()
        
        logger.info(f"Database backup created at {backup_path}")
        return backup_path

    def restore_from_backup(self, backup_path: str):
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        with self.pool.get_connection() as dest_conn:
            backup_conn = sqlite3.connect(backup_path)
            backup_conn.backup(dest_conn)
            backup_conn.close()
        
        logger.info(f"Database restored from backup: {backup_path}")

    def execute_migration(self, migration_sql: str):
        with self.pool.get_connection() as conn:
            try:
                conn.executescript(migration_sql)
                conn.commit()
                logger.info("Migration executed successfully")
            except sqlite3.Error as e:
                logger.error(f"Migration failed: {str(e)}")
                conn.rollback()
                raise

    def __del__(self):
        self.pool.close_all() 
