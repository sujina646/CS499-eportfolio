from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, date
import sqlite3
from database_config import DatabasePool
import logging

logger = logging.getLogger(__name__)

@dataclass
class Trip:
    id: Optional[int]
    destination: str
    created_at: datetime
    updated_at: datetime
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    categories: List[str] = None
    tags: List[str] = None
    deleted_at: Optional[datetime] = None

class TripModel:
    def __init__(self, db_name: str):
        self.pool = DatabasePool(db_name)
        self._initialize_tables()

    def _initialize_tables(self):
        with self.pool.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trips (
                    id INTEGER PRIMARY KEY,
                    destination TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    start_date DATE,
                    end_date DATE,
                    deleted_at TIMESTAMP
                )
            ''')
            conn.commit()

    def add_trip(self, destination: str, start_date: date = None, end_date: date = None,
                 categories: List[str] = None, tags: List[str] = None) -> Trip:
        if not destination:
            raise ValueError("Destination cannot be empty")

        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date must be before end date")

        with self.pool.get_connection() as conn:
            try:
                conn.execute("BEGIN TRANSACTION")
                
                # Insert trip
                cursor = conn.execute(
                    """
                    INSERT INTO trips (destination, start_date, end_date)
                    VALUES (?, ?, ?)
                    """,
                    (destination, start_date, end_date)
                )
                trip_id = cursor.lastrowid

                # Add categories
                if categories:
                    for category in categories:
                        self._add_category(conn, trip_id, category)

                # Add tags
                if tags:
                    for tag in tags:
                        self._add_tag(conn, trip_id, tag)

                conn.commit()
                logger.info(f"Added trip: {destination}")
                return self.get_trip_by_id(trip_id)

            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Failed to add trip: {str(e)}")
                raise

    def _add_category(self, conn: sqlite3.Connection, trip_id: int, category_name: str):
        # Insert category if not exists
        conn.execute(
            """
            INSERT OR IGNORE INTO categories (name)
            VALUES (?)
            """,
            (category_name,)
        )
        
        # Get category ID
        cursor = conn.execute(
            "SELECT id FROM categories WHERE name = ?",
            (category_name,)
        )
        category_id = cursor.fetchone()[0]
        
        # Link trip to category
        conn.execute(
            """
            INSERT OR IGNORE INTO trip_categories (trip_id, category_id)
            VALUES (?, ?)
            """,
            (trip_id, category_id)
        )

    def _add_tag(self, conn: sqlite3.Connection, trip_id: int, tag_name: str):
        # Insert tag if not exists
        conn.execute(
            """
            INSERT OR IGNORE INTO tags (name)
            VALUES (?)
            """,
            (tag_name,)
        )
        
        # Get tag ID
        cursor = conn.execute(
            "SELECT id FROM tags WHERE name = ?",
            (tag_name,)
        )
        tag_id = cursor.fetchone()[0]
        
        # Link trip to tag
        conn.execute(
            """
            INSERT OR IGNORE INTO trip_tags (trip_id, tag_id)
            VALUES (?, ?)
            """,
            (trip_id, tag_id)
        )

    def get_trip_by_id(self, trip_id: int) -> Optional[Trip]:
        with self.pool.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT t.*, 
                       GROUP_CONCAT(DISTINCT c.name) as categories,
                       GROUP_CONCAT(DISTINCT tg.name) as tags
                FROM trips t
                LEFT JOIN trip_categories tc ON t.id = tc.trip_id
                LEFT JOIN categories c ON tc.category_id = c.id
                LEFT JOIN trip_tags tt ON t.id = tt.trip_id
                LEFT JOIN tags tg ON tt.tag_id = tg.id
                WHERE t.id = ?
                GROUP BY t.id
                """,
                (trip_id,)
            )
            row = cursor.fetchone()
            if row:
                categories = row['categories'].split(',') if row['categories'] else []
                tags = row['tags'].split(',') if row['tags'] else []
                return Trip(
                    id=row['id'],
                    destination=row['destination'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    start_date=date.fromisoformat(row['start_date']) if row['start_date'] else None,
                    end_date=date.fromisoformat(row['end_date']) if row['end_date'] else None,
                    categories=categories,
                    tags=tags,
                    deleted_at=datetime.fromisoformat(row['deleted_at']) if row['deleted_at'] else None
                )
            return None

    def get_all_trips(self, include_deleted: bool = False) -> List[Trip]:
        with self.pool.get_connection() as conn:
            query = """
                SELECT t.*, 
                       GROUP_CONCAT(DISTINCT c.name) as categories,
                       GROUP_CONCAT(DISTINCT tg.name) as tags
                FROM trips t
                LEFT JOIN trip_categories tc ON t.id = tc.trip_id
                LEFT JOIN categories c ON tc.category_id = c.id
                LEFT JOIN trip_tags tt ON t.id = tt.trip_id
                LEFT JOIN tags tg ON tt.tag_id = tg.id
            """
            if not include_deleted:
                query += " WHERE t.deleted_at IS NULL"
            query += " GROUP BY t.id ORDER BY t.created_at DESC"
            
            cursor = conn.execute(query)
            return [
                Trip(
                    id=row['id'],
                    destination=row['destination'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    start_date=date.fromisoformat(row['start_date']) if row['start_date'] else None,
                    end_date=date.fromisoformat(row['end_date']) if row['end_date'] else None,
                    categories=row['categories'].split(',') if row['categories'] else [],
                    tags=row['tags'].split(',') if row['tags'] else [],
                    deleted_at=datetime.fromisoformat(row['deleted_at']) if row['deleted_at'] else None
                )
                for row in cursor.fetchall()
            ]

    def search_trips(self, query: str) -> List[Trip]:
        with self.pool.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT t.id
                FROM trips_fts fts
                JOIN trips t ON t.id = fts.rowid
                WHERE trips_fts MATCH ? AND t.deleted_at IS NULL
                ORDER BY rank
                """,
                (query,)
            )
            trip_ids = [row['id'] for row in cursor.fetchall()]
            return [self.get_trip_by_id(trip_id) for trip_id in trip_ids]

    def get_trips_by_date_range(self, start: date, end: date) -> List[Trip]:
        if start > end:
            raise ValueError("Start date must be before end date")

        with self.pool.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id FROM trips
                WHERE deleted_at IS NULL
                AND (
                    (start_date BETWEEN ? AND ?) OR
                    (end_date BETWEEN ? AND ?) OR
                    (start_date <= ? AND end_date >= ?)
                )
                """,
                (start, end, start, end, start, end)
            )
            trip_ids = [row['id'] for row in cursor.fetchall()]
            return [self.get_trip_by_id(trip_id) for trip_id in trip_ids]

    def update_trip(self, trip_id: int, destination: str = None, start_date: date = None,
                   end_date: date = None, categories: List[str] = None, tags: List[str] = None) -> Optional[Trip]:
        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date must be before end date")

        with self.pool.get_connection() as conn:
            try:
                conn.execute("BEGIN TRANSACTION")
                
                # Update trip details
                updates = []
                params = []
                if destination:
                    updates.append("destination = ?")
                    params.append(destination)
                if start_date is not None:
                    updates.append("start_date = ?")
                    params.append(start_date)
                if end_date is not None:
                    updates.append("end_date = ?")
                    params.append(end_date)
                
                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    query = f"UPDATE trips SET {', '.join(updates)} WHERE id = ?"
                    params.append(trip_id)
                    conn.execute(query, params)

                # Update categories if provided
                if categories is not None:
                    conn.execute(
                        "DELETE FROM trip_categories WHERE trip_id = ?",
                        (trip_id,)
                    )
                    for category in categories:
                        self._add_category(conn, trip_id, category)

                # Update tags if provided
                if tags is not None:
                    conn.execute(
                        "DELETE FROM trip_tags WHERE trip_id = ?",
                        (trip_id,)
                    )
                    for tag in tags:
                        self._add_tag(conn, trip_id, tag)

                conn.commit()
                logger.info(f"Updated trip {trip_id}")
                return self.get_trip_by_id(trip_id)

            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Failed to update trip: {str(e)}")
                raise

    def delete_trip(self, trip_id: int, soft_delete: bool = True) -> bool:
        with self.pool.get_connection() as conn:
            try:
                if soft_delete:
                    conn.execute(
                        "UPDATE trips SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (trip_id,)
                    )
                else:
                    conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
                conn.commit()
                logger.info(f"{'Soft' if soft_delete else 'Hard'} deleted trip {trip_id}")
                return True
            except sqlite3.Error as e:
                logger.error(f"Failed to delete trip: {str(e)}")
                return False

    def __del__(self):
        self.pool.close_all() 
