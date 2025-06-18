from typing import Dict, TypeVar, Generic, Optional, Callable, Any, List, Tuple
from collections import OrderedDict
import time
from functools import wraps
import json
import os

# Type variable for cache values
T = TypeVar('T')

class LRUCache(Generic[T]):
    """
    Least Recently Used (LRU) cache implementation.
    Automatically evicts least recently used items when capacity is reached.
    
    This implementation uses an OrderedDict to track insertion/access order.
    """
    
    def __init__(self, capacity: int):
        """
        Initialize LRU cache with a maximum capacity.
        
        Args:
            capacity: Maximum number of items to store in the cache
        """
        if capacity <= 0:
            raise ValueError("Cache capacity must be positive")
        
        self.capacity = capacity
        self.cache: OrderedDict[str, Tuple[T, float]] = OrderedDict()
    
    def get(self, key: str) -> Optional[T]:
        """
        Get an item from the cache.
        
        Args:
            key: Cache key to lookup
            
        Returns:
            The cached value or None if not in cache
        """
        if key not in self.cache:
            return None
        
        # Move accessed item to the end to mark as most recently used
        value, _ = self.cache.pop(key)
        self.cache[key] = (value, time.time())
        return value
    
    def put(self, key: str, value: T) -> None:
        """
        Add an item to the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        # If key exists, update it and move to end
        if key in self.cache:
            self.cache.pop(key)
        
        # If at capacity, remove least recently used item (first item)
        elif len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)
        
        # Add new item
        self.cache[key] = (value, time.time())
    
    def remove(self, key: str) -> bool:
        """
        Remove an item from the cache.
        
        Args:
            key: Cache key to remove
            
        Returns:
            True if key was in cache and removed, False otherwise
        """
        if key in self.cache:
            self.cache.pop(key)
            return True
        return False
    
    def clear(self) -> None:
        """Clear all items from the cache."""
        self.cache.clear()
    
    def get_all_items(self) -> List[Tuple[str, T]]:
        """
        Get all cached items.
        
        Returns:
            List of tuples containing (key, value) pairs
        """
        return [(key, value) for key, (value, _) in self.cache.items()]
    
    def size(self) -> int:
        """
        Get the current size of the cache.
        
        Returns:
            Number of items in cache
        """
        return len(self.cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with stats including size, capacity, and age of oldest item
        """
        stats = {
            "size": len(self.cache),
            "capacity": self.capacity,
            "utilization": len(self.cache) / self.capacity if self.capacity > 0 else 0
        }
        
        if self.cache:
            oldest_time = min(timestamp for _, timestamp in self.cache.values())
            stats["oldest_item_age"] = time.time() - oldest_time
        
        return stats


class PersistentCache(LRUCache[T]):
    """
    Extension of LRUCache that persists cache to disk.
    """
    
    def __init__(self, capacity: int, filename: str, serialize_fn: Callable[[T], Any] = None, 
                 deserialize_fn: Callable[[Any], T] = None):
        """
        Initialize a persistent LRU cache.
        
        Args:
            capacity: Maximum number of items to store
            filename: File path to store cache
            serialize_fn: Optional function to serialize values before storing
            deserialize_fn: Optional function to deserialize values after loading
        """
        super().__init__(capacity)
        self.filename = filename
        self.serialize_fn = serialize_fn or (lambda x: x)
        self.deserialize_fn = deserialize_fn or (lambda x: x)
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from disk file if it exists."""
        if not os.path.exists(self.filename):
            return
        
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
                
            # Rebuild cache with loaded data
            for key, (serialized_value, timestamp) in data.items():
                value = self.deserialize_fn(serialized_value)
                # Add directly to OrderedDict to preserve order
                self.cache[key] = (value, timestamp)
                
            # Trim to capacity
            while len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
                
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading cache from {self.filename}: {e}")
    
    def _save_cache(self) -> None:
        """Save cache to disk file."""
        try:
            # Convert cache to serializable format
            serializable_cache = {
                key: (self.serialize_fn(value), timestamp)
                for key, (value, timestamp) in self.cache.items()
            }
            
            with open(self.filename, 'w') as f:
                json.dump(serializable_cache, f)
                
        except (TypeError, IOError) as e:
            print(f"Error saving cache to {self.filename}: {e}")
    
    def put(self, key: str, value: T) -> None:
        """Add or update item and save cache to disk."""
        super().put(key, value)
        self._save_cache()
    
    def remove(self, key: str) -> bool:
        """Remove item and save cache to disk if changed."""
        result = super().remove(key)
        if result:
            self._save_cache()
        return result
    
    def clear(self) -> None:
        """Clear cache and save to disk."""
        super().clear()
        self._save_cache()


def lru_cache_decorator(maxsize: int = 128):
    """
    Decorator that applies LRU caching to a function.
    Similar to functools.lru_cache but with more features.
    
    Args:
        maxsize: Maximum cache size
    
    Returns:
        Decorated function with caching
    """
    cache = LRUCache(maxsize)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a key from function arguments
            key = str(args) + str(sorted(kwargs.items()))
            result = cache.get(key)
            
            if result is None:
                # Cache miss - call function and cache result
                result = func(*args, **kwargs)
                cache.put(key, result)
            
            return result
        
        # Add cache statistics to function
        wrapper.cache_info = lambda: cache.get_stats()
        wrapper.cache_clear = lambda: cache.clear()
        
        return wrapper
    
    return decorator


# Example usage (not part of the module)
if __name__ == "__main__":
    # Create LRU cache with capacity of 2
    cache = LRUCache[str](2)
    
    # Add items
    cache.put("key1", "value1")
    cache.put("key2", "value2")
    
    # This should evict key1
    cache.put("key3", "value3")
    
    # key1 should be gone, key2 and key3 should exist
    print(f"key1: {cache.get('key1')}")  # None
    print(f"key2: {cache.get('key2')}")  # value2
    print(f"key3: {cache.get('key3')}")  # value3
    
    # Accessing key2 makes it most recently used
    cache.get("key2")
    
    # Adding key4 should now evict key3
    cache.put("key4", "value4")
    
    print(f"key3: {cache.get('key3')}")  # None
    print(f"key2: {cache.get('key2')}")  # value2
    print(f"key4: {cache.get('key4')}")  # value4
    
    # Example with decorator
    @lru_cache_decorator(maxsize=2)
    def fibonacci(n):
        if n <= 1:
            return n
        return fibonacci(n-1) + fibonacci(n-2)
    
    # This will use the cache
    print(f"fibonacci(10): {fibonacci(10)}")
    print(f"Cache stats: {fibonacci.cache_info()}") 
