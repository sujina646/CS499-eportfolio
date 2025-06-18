import sqlite3
from typing import List, Optional, Dict, Any, Tuple
import requests
from dataclasses import dataclass
from datetime import datetime
import json

from pathfinding import Location, PathFinder
from cache import PersistentCache, lru_cache_decorator

@dataclass
class Trip:
    id: Optional[int]
    destination: str
    created_at: datetime
    updated_at: datetime
    locations: List[Location] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Trip to dictionary for serialization."""
        return {
            "id": self.id,
            "destination": self.destination,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "locations": [
                {
                    "id": loc.id,
                    "name": loc.name,
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "description": loc.description
                }
                for loc in (self.locations or [])
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trip':
        """Create Trip from dictionary after deserialization."""
        locations = []
        if "locations" in data and data["locations"]:
            locations = [
                Location(
                    id=loc["id"],
                    name=loc["name"],
                    latitude=loc["latitude"],
                    longitude=loc["longitude"],
                    description=loc.get("description", "")
                )
                for loc in data["locations"]
            ]
        
        return cls(
            id=data["id"],
            destination=data["destination"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            locations=locations
        )


class TripModel:
    def __init__(self, db_name: str):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()
        
        # Initialize API endpoint
        self.api_url = 'http://localhost:3000/api/trips'
        
        # Initialize caches
        self.trip_cache = PersistentCache[Trip](
            capacity=50,
            filename="trip_cache.json",
            serialize_fn=lambda trip: trip.to_dict(),
            deserialize_fn=lambda data: Trip.from_dict(data)
        )
        
        self.location_cache = PersistentCache[Location](
            capacity=100,
            filename="location_cache.json",
            serialize_fn=lambda loc: {
                "id": loc.id,
                "name": loc.name,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "description": loc.description
            },
            deserialize_fn=lambda data: Location(**data)
        )
        
        # Initialize path finder with empty locations (will be populated as needed)
        self.path_finder = PathFinder([])

    def _create_tables(self):
        # Create trips table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY,
                destination TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create locations table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                description TEXT
            )
        ''')
        
        # Create trip_locations join table for many-to-many relationship
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trip_locations (
                trip_id INTEGER,
                location_id INTEGER,
                position INTEGER,
                PRIMARY KEY (trip_id, location_id),
                FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
                FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
            )
        ''')
        
        self.conn.commit()

    @lru_cache_decorator(maxsize=50)
    def add_trip(self, destination: str) -> Trip:
        """Add a new trip with caching."""
        try:
            self.cursor.execute(
                "INSERT INTO trips (destination) VALUES (?)",
                (destination,)
            )
            self.conn.commit()
            
            trip_id = self.cursor.lastrowid
            trip = self.get_trip_by_id(trip_id)
            
            # Add to cache
            if trip:
                self.trip_cache.put(str(trip_id), trip)
            
            # Try to sync with API (non-blocking)
            self._sync_with_api(destination)
            
            return trip
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to add trip: {str(e)}")

    def get_trip_by_id(self, trip_id: int) -> Optional[Trip]:
        """Get a trip by ID with caching."""
        # Try to get from cache first
        cached_trip = self.trip_cache.get(str(trip_id))
        if cached_trip:
            return cached_trip
        
        # Not in cache, query database
        self.cursor.execute(
            "SELECT id, destination, created_at, updated_at FROM trips WHERE id = ?",
            (trip_id,)
        )
        row = self.cursor.fetchone()
        
        if not row:
            return None
        
        # Create trip object
        trip = Trip(
            id=row[0],
            destination=row[1],
            created_at=datetime.fromisoformat(row[2]),
            updated_at=datetime.fromisoformat(row[3])
        )
        
        # Get locations for this trip
        trip.locations = self._get_locations_for_trip(trip_id)
        
        # Add to cache
        self.trip_cache.put(str(trip_id), trip)
        
        return trip

    def get_all_trips(self) -> List[Trip]:
        """Get all trips with efficient querying."""
        self.cursor.execute(
            "SELECT id, destination, created_at, updated_at FROM trips ORDER BY created_at DESC"
        )
        
        trips = []
        for row in self.cursor.fetchall():
            trip_id = row[0]
            
            # Try to get from cache first
            cached_trip = self.trip_cache.get(str(trip_id))
            if cached_trip:
                trips.append(cached_trip)
                continue
            
            # Not in cache, create new trip object
            trip = Trip(
                id=trip_id,
                destination=row[1],
                created_at=datetime.fromisoformat(row[2]),
                updated_at=datetime.fromisoformat(row[3])
            )
            
            # Get locations (will be cached individually)
            trip.locations = self._get_locations_for_trip(trip_id)
            
            # Add to cache
            self.trip_cache.put(str(trip_id), trip)
            trips.append(trip)
        
        return trips

    def update_trip(self, trip_id: int, destination: str) -> Optional[Trip]:
        """Update a trip with cache invalidation."""
        try:
            self.cursor.execute(
                "UPDATE trips SET destination = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (destination, trip_id)
            )
            self.conn.commit()
            
            # Invalidate cache
            self.trip_cache.remove(str(trip_id))
            
            # Get updated trip (will be re-cached)
            return self.get_trip_by_id(trip_id)
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to update trip: {str(e)}")

    def delete_trip(self, trip_id: int) -> bool:
        """Delete a trip with cache invalidation."""
        try:
            # First, remove from cache
            self.trip_cache.remove(str(trip_id))
            
            # Then delete from database
            self.cursor.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
            self.conn.commit()
            
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to delete trip: {str(e)}")

    def add_location(self, name: str, latitude: float, longitude: float, description: str = "") -> Location:
        """Add a new location."""
        try:
            self.cursor.execute(
                "INSERT INTO locations (name, latitude, longitude, description) VALUES (?, ?, ?, ?)",
                (name, latitude, longitude, description)
            )
            self.conn.commit()
            
            location_id = self.cursor.lastrowid
            location = Location(id=location_id, name=name, latitude=latitude, 
                               longitude=longitude, description=description)
            
            # Add to cache
            self.location_cache.put(str(location_id), location)
            
            # Update path finder with new location
            self._update_path_finder()
            
            return location
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to add location: {str(e)}")

    def get_location_by_id(self, location_id: int) -> Optional[Location]:
        """Get a location by ID with caching."""
        # Try to get from cache first
        cached_location = self.location_cache.get(str(location_id))
        if cached_location:
            return cached_location
        
        # Not in cache, query database
        self.cursor.execute(
            "SELECT id, name, latitude, longitude, description FROM locations WHERE id = ?",
            (location_id,)
        )
        row = self.cursor.fetchone()
        
        if not row:
            return None
        
        # Create location object
        location = Location(
            id=row[0],
            name=row[1],
            latitude=row[2],
            longitude=row[3],
            description=row[4] or ""
        )
        
        # Add to cache
        self.location_cache.put(str(location_id), location)
        
        return location

    def add_location_to_trip(self, trip_id: int, location_id: int, position: int = -1) -> bool:
        """Add a location to a trip."""
        try:
            if position < 0:
                # Find the next available position
                self.cursor.execute(
                    "SELECT MAX(position) FROM trip_locations WHERE trip_id = ?",
                    (trip_id,)
                )
                max_pos = self.cursor.fetchone()[0]
                position = 0 if max_pos is None else max_pos + 1
            
            # Add location to trip
            self.cursor.execute(
                "INSERT OR REPLACE INTO trip_locations (trip_id, location_id, position) VALUES (?, ?, ?)",
                (trip_id, location_id, position)
            )
            self.conn.commit()
            
            # Invalidate trip cache
            self.trip_cache.remove(str(trip_id))
            
            return True
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to add location to trip: {str(e)}")

    def remove_location_from_trip(self, trip_id: int, location_id: int) -> bool:
        """Remove a location from a trip."""
        try:
            self.cursor.execute(
                "DELETE FROM trip_locations WHERE trip_id = ? AND location_id = ?",
                (trip_id, location_id)
            )
            self.conn.commit()
            
            # Invalidate trip cache
            self.trip_cache.remove(str(trip_id))
            
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to remove location from trip: {str(e)}")

    def optimize_trip_route(self, trip_id: int) -> Optional[List[Location]]:
        """
        Optimize the route for a trip using the A* pathfinding algorithm.
        Reorders locations to minimize travel distance.
        """
        trip = self.get_trip_by_id(trip_id)
        if not trip or not trip.locations or len(trip.locations) < 2:
            return None
        
        # Ensure path finder is up to date
        self._update_path_finder()
        
        # Simple greedy algorithm for route optimization
        # Start from first location and always go to the nearest unvisited location
        optimized_route = [trip.locations[0]]
        remaining_locations = trip.locations[1:]
        
        current_location = optimized_route[0]
        while remaining_locations:
            # Find nearest location
            nearest_location = min(
                remaining_locations, 
                key=lambda loc: current_location.distance_to(loc)
            )
            
            # Find optimal path to nearest location
            path = self.path_finder.find_path(
                current_location.id,
                nearest_location.id
            )
            
            # Add path (excluding start location which is already in the route)
            optimized_route.extend(path[1:])
            
            # Update current location and remove visited location
            current_location = nearest_location
            remaining_locations.remove(nearest_location)
        
        # Update trip_locations table with new order
        try:
            self.cursor.execute("BEGIN TRANSACTION")
            
            # Delete existing entries
            self.cursor.execute(
                "DELETE FROM trip_locations WHERE trip_id = ?",
                (trip_id,)
            )
            
            # Insert new entries with updated positions
            for position, location in enumerate(optimized_route):
                self.cursor.execute(
                    "INSERT INTO trip_locations (trip_id, location_id, position) VALUES (?, ?, ?)",
                    (trip_id, location.id, position)
                )
            
            self.cursor.execute("COMMIT")
            
            # Invalidate trip cache
            self.trip_cache.remove(str(trip_id))
            
            return optimized_route
        except sqlite3.Error as e:
            self.cursor.execute("ROLLBACK")
            raise DatabaseError(f"Failed to optimize trip route: {str(e)}")

    def _get_locations_for_trip(self, trip_id: int) -> List[Location]:
        """Get all locations for a trip in the correct order."""
        self.cursor.execute(
            """
            SELECT l.id, l.name, l.latitude, l.longitude, l.description, tl.position
            FROM locations l
            JOIN trip_locations tl ON l.id = tl.location_id
            WHERE tl.trip_id = ?
            ORDER BY tl.position
            """,
            (trip_id,)
        )
        
        locations = []
        for row in self.cursor.fetchall():
            location_id = row[0]
            
            # Try to get from cache first
            cached_location = self.location_cache.get(str(location_id))
            if cached_location:
                locations.append(cached_location)
                continue
            
            # Not in cache, create new location object
            location = Location(
                id=location_id,
                name=row[1],
                latitude=row[2],
                longitude=row[3],
                description=row[4] or ""
            )
            
            # Add to cache
            self.location_cache.put(str(location_id), location)
            locations.append(location)
        
        return locations

    def _update_path_finder(self):
        """Update the path finder with all locations from database."""
        self.cursor.execute(
            "SELECT id, name, latitude, longitude, description FROM locations"
        )
        
        locations = []
        for row in self.cursor.fetchall():
            location = Location(
                id=row[0],
                name=row[1],
                latitude=row[2],
                longitude=row[3],
                description=row[4] or ""
            )
            locations.append(location)
        
        # Update path finder with all locations
        self.path_finder = PathFinder(locations)

    def _sync_with_api(self, destination: str) -> None:
        """Sync trip with API server."""
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

    def clear_caches(self):
        """Clear all caches."""
        self.trip_cache.clear()
        self.location_cache.clear()

    def get_cache_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches."""
        return {
            "trip_cache": self.trip_cache.get_stats(),
            "location_cache": self.location_cache.get_stats()
        }

    def __del__(self):
        """Close database connection when object is destroyed."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()


class DatabaseError(Exception):
    """Exception raised for database errors."""
    pass 
