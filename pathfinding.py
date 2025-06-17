import heapq
from math import sqrt, pow
from typing import Dict, List, Set, Tuple, Callable, Optional
from dataclasses import dataclass, field


@dataclass
class Location:
    """
    Represents a location with latitude and longitude coordinates.
    Used for pathfinding between locations.
    """
    id: int
    name: str
    latitude: float
    longitude: float
    description: str = ""
    
    def distance_to(self, other: 'Location') -> float:
        """Calculate the Euclidean distance between two locations."""
        return sqrt(
            pow(self.latitude - other.latitude, 2) +
            pow(self.longitude - other.longitude, 2)
        )


@dataclass(order=True)
class PathNode:
    """
    Node used in the A* pathfinding algorithm.
    The sort_index field allows the priority queue to compare nodes.
    """
    sort_index: float = field(init=False)
    location: Location = field(compare=False)
    parent: Optional['PathNode'] = field(default=None, compare=False)
    g_score: float = field(default=float('inf'), compare=False)  # Cost from start
    h_score: float = field(default=float('inf'), compare=False)  # Heuristic cost to goal
    
    def __post_init__(self):
        self.sort_index = self.g_score + self.h_score


class PathFinder:
    """
    Implements the A* pathfinding algorithm to find optimal routes between locations.
    Uses a priority queue for efficient node exploration.
    """
    
    def __init__(self, locations: List[Location]):
        """Initialize with a list of available locations."""
        self.locations = locations
        self._build_graph()
    
    def _build_graph(self):
        """
        Build an adjacency list representation of the location graph.
        Each location is connected to all other locations.
        """
        self.graph: Dict[int, List[Tuple[int, float]]] = {}
        
        # Create a graph where each location is connected to all others
        for loc in self.locations:
            self.graph[loc.id] = []
            
            for other in self.locations:
                if loc.id != other.id:
                    distance = loc.distance_to(other)
                    self.graph[loc.id].append((other.id, distance))
    
    def find_path(self, start_id: int, goal_id: int) -> List[Location]:
        """
        Implements A* algorithm to find the shortest path between two locations.
        
        Args:
            start_id: ID of the starting location
            goal_id: ID of the goal location
            
        Returns:
            A list of Location objects representing the path from start to goal
        """
        if start_id == goal_id:
            return [self._get_location_by_id(start_id)]
        
        start_location = self._get_location_by_id(start_id)
        goal_location = self._get_location_by_id(goal_id)
        
        if not start_location or not goal_location:
            return []
        
        # Create start node
        start_node = PathNode(location=start_location)
        start_node.g_score = 0
        start_node.h_score = start_location.distance_to(goal_location)
        
        # Use a priority queue for open set
        open_set = [start_node]
        # Track visited location IDs
        closed_set: Set[int] = set()
        # Map location IDs to their best known path node
        node_map: Dict[int, PathNode] = {start_id: start_node}
        
        while open_set:
            # Get node with lowest f_score (g_score + h_score)
            current = heapq.heappop(open_set)
            current_id = current.location.id
            
            # Check if we reached the goal
            if current_id == goal_id:
                return self._reconstruct_path(current)
            
            # Mark as visited
            closed_set.add(current_id)
            
            # Process neighbors
            for neighbor_id, distance in self.graph[current_id]:
                # Skip already evaluated nodes
                if neighbor_id in closed_set:
                    continue
                
                neighbor_location = self._get_location_by_id(neighbor_id)
                
                # Calculate g_score for this path
                tentative_g_score = current.g_score + distance
                
                # If we already know a better path to this neighbor, skip
                if neighbor_id in node_map and tentative_g_score >= node_map[neighbor_id].g_score:
                    continue
                
                # This is the best path so far, record it
                if neighbor_id in node_map:
                    neighbor_node = node_map[neighbor_id]
                    # Update existing node
                    neighbor_node.parent = current
                    neighbor_node.g_score = tentative_g_score
                    
                    # Re-heapify since the score changed
                    heapq.heapify(open_set)
                else:
                    # Create new node
                    neighbor_node = PathNode(
                        location=neighbor_location,
                        parent=current,
                        g_score=tentative_g_score,
                        h_score=neighbor_location.distance_to(goal_location)
                    )
                    node_map[neighbor_id] = neighbor_node
                    heapq.heappush(open_set, neighbor_node)
        
        # No path found
        return []
    
    def _get_location_by_id(self, location_id: int) -> Optional[Location]:
        """Helper method to get a location by its ID."""
        for location in self.locations:
            if location.id == location_id:
                return location
        return None
    
    def _reconstruct_path(self, end_node: PathNode) -> List[Location]:
        """Reconstruct the path from end node to start by following parent links."""
        path = []
        current = end_node
        
        while current:
            path.append(current.location)
            current = current.parent
        
        # Reverse to get start-to-end path
        return path[::-1]


# Example usage (not part of the module)
if __name__ == "__main__":
    # Sample locations
    locations = [
        Location(id=1, name="New York", latitude=40.7128, longitude=-74.0060),
        Location(id=2, name="Los Angeles", latitude=34.0522, longitude=-118.2437),
        Location(id=3, name="Chicago", latitude=41.8781, longitude=-87.6298),
        Location(id=4, name="Houston", latitude=29.7604, longitude=-95.3698),
        Location(id=5, name="Phoenix", latitude=33.4484, longitude=-112.0740)
    ]
    
    # Create pathfinder
    pathfinder = PathFinder(locations)
    
    # Find path from New York to Phoenix
    path = pathfinder.find_path(1, 5)
    
    # Print the path
    print("Path from New York to Phoenix:")
    for location in path:
        print(f"- {location.name} ({location.latitude}, {location.longitude})") 