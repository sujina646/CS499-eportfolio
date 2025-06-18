import unittest
import os
from model import TripModel
from database_config import DatabaseManager
import sqlite3

class TestSecurity(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_security.db"
        self.model = TripModel(self.db_name)
        self.db_manager = DatabaseManager(self.db_name)

    def tearDown(self):
        if os.path.exists(self.db_name):
            os.remove(self.db_name)
        if os.path.exists("database_backups"):
            for file in os.listdir("database_backups"):
                os.remove(os.path.join("database_backups", file))
            os.rmdir("database_backups")

    def test_sql_injection_prevention(self):
        # Test that SQL injection attempts are prevented
        malicious_input = "Paris'; DROP TABLE trips; --"
        
        # This should safely handle the malicious input
        trip = self.model.add_trip(malicious_input)
        
        # Verify the input was properly escaped
        retrieved_trip = self.model.get_trip_by_id(trip.id)
        self.assertEqual(retrieved_trip.destination, malicious_input)
        
        # Verify the trips table still exists
        with self.model.pool.get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='trips'"
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_backup_restore(self):
        # Test backup and restore functionality
        # Add some data
        self.model.add_trip("Paris")
        self.model.add_trip("London")
        
        # Create backup
        backup_path = self.db_manager.create_backup()
        self.assertTrue(os.path.exists(backup_path))
        
        # Delete all trips
        with self.model.pool.get_connection() as conn:
            conn.execute("DELETE FROM trips")
            conn.commit()
        
        # Verify trips are gone
        trips = self.model.get_all_trips()
        self.assertEqual(len(trips), 0)
        
        # Restore from backup
        self.db_manager.restore_from_backup(backup_path)
        
        # Verify data is restored
        trips = self.model.get_all_trips()
        self.assertEqual(len(trips), 2)

    def test_transaction_rollback(self):
        # Test that transactions are properly rolled back on error
        try:
            with self.model.pool.get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                conn.execute(
                    "INSERT INTO trips (destination) VALUES (?)",
                    ("Paris",)
                )
                # This should fail and trigger rollback
                conn.execute("INSERT INTO nonexistent_table VALUES (1)")
                conn.commit()
        except sqlite3.Error:
            pass
        
        # Verify no data was committed
        trips = self.model.get_all_trips()
        self.assertEqual(len(trips), 0)

    def test_input_validation(self):
        # Test date validation
        with self.assertRaises(ValueError):
            self.model.add_trip(
                "Paris",
                start_date="2024-06-01",  # Invalid date format
                end_date="2024-06-07"
            )
        
        # Test empty destination
        with self.assertRaises(ValueError):
            self.model.add_trip("")

if __name__ == '__main__':
    unittest.main() 
