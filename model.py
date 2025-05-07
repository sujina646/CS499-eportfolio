import sqlite3
from typing import List, Optional
import requests
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Trip:
    id: Optional[int]
    destination: str
    created_at: datetime
    updated_at: datetime

class TripModel:
    def __init__(self, db_name: str):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()
        self.api_url = 'http://localhost:3000/api/trips'

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY,
                destination TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def add_trip(self, destination: str) -> Trip:
        try:
            self.cursor.execute(
                "INSERT INTO trips (destination) VALUES (?)",
                (destination,)
            )
            self.conn.commit()
            
            # Sync with API
            self._sync_with_api(destination)
            
            return self.get_trip_by_id(self.cursor.lastrowid)
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to add trip: {str(e)}")

    def get_trip_by_id(self, trip_id: int) -> Optional[Trip]:
        self.cursor.execute(
            "SELECT id, destination, created_at, updated_at FROM trips WHERE id = ?",
            (trip_id,)
        )
        row = self.cursor.fetchone()
        if row:
            return Trip(
                id=row[0],
                destination=row[1],
                created_at=datetime.fromisoformat(row[2]),
                updated_at=datetime.fromisoformat(row[3])
            )
        return None

    def get_all_trips(self) -> List[Trip]:
        self.cursor.execute(
            "SELECT id, destination, created_at, updated_at FROM trips ORDER BY created_at DESC"
        )
        return [
            Trip(
                id=row[0],
                destination=row[1],
                created_at=datetime.fromisoformat(row[2]),
                updated_at=datetime.fromisoformat(row[3])
            )
            for row in self.cursor.fetchall()
        ]

    def update_trip(self, trip_id: int, destination: str) -> Optional[Trip]:
        try:
            self.cursor.execute(
                "UPDATE trips SET destination = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (destination, trip_id)
            )
            self.conn.commit()
            return self.get_trip_by_id(trip_id)
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to update trip: {str(e)}")

    def delete_trip(self, trip_id: int) -> bool:
        try:
            self.cursor.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to delete trip: {str(e)}")

    def _sync_with_api(self, destination: str) -> None:
        try:
            response = requests.post(
                self.api_url,
                json={'destination': destination},
                timeout=5
            )
            response.raise_for_status()
        except requests.RequestException as e:
            # Log the error but don't fail the operation
            print(f"API sync failed: {str(e)}")

    def __del__(self):
        self.conn.close()

class DatabaseError(Exception):
    pass 