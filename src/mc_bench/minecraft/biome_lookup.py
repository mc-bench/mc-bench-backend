from dataclasses import dataclass
from typing import List, Dict, Set, Tuple, Optional
import math

DEFAULT_BIOME = "plains"


@dataclass
class Point3D:
    x: int
    y: int
    z: int
    
    def distance_to(self, other: 'Point3D') -> float:
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 + 
            (self.z - other.z) ** 2
        )


@dataclass
class BiomeRegion:
    start: Point3D
    end: Point3D
    biome: str
    
    def contains_point(self, point: Point3D) -> bool:
        """Check if a point lies within this biome region."""
        return (
            self.start.x <= point.x <= self.end.x and
            self.start.y <= point.y <= self.end.y and
            self.start.z <= point.z <= self.end.z
        )
    
    def min_distance_to_point(self, point: Point3D) -> float:
        """Calculate the minimum distance from a point to this region's boundary."""
        # For each dimension, find the closest point that lies within the region's bounds
        closest_x = max(self.start.x, min(point.x, self.end.x))
        closest_y = max(self.start.y, min(point.y, self.end.y))
        closest_z = max(self.start.z, min(point.z, self.end.z))
        
        # Create a point representing the closest position
        closest_point = Point3D(closest_x, closest_y, closest_z)
        return point.distance_to(closest_point)


class BiomeLookup:
    def __init__(self, biome_data: List[Dict], bounding_box: Dict):
        """
        Initialize the BiomeLookup with biome command data and bounding box information.
        
        Args:
            biome_data: List of biome commands with coordinates
            bounding_box: Dictionary containing min/max coordinates of the export region
        """
        self.regions: List[BiomeRegion] = []
        
        # Get the minimum coordinates from bounding box for normalization
        min_x = bounding_box['min']['x']
        min_y = bounding_box['min']['y']
        min_z = bounding_box['min']['z']
        
        # Process commands in reverse order since later commands override earlier ones
        for command in reversed(biome_data):
            coords = command['coordinates']
            
            # Normalize coordinates relative to the bounding box minimum
            start = Point3D(
                coords[0]['x'] - min_x,
                coords[0]['y'] - min_y,
                coords[0]['z'] - min_z
            )
            end = Point3D(
                coords[1]['x'] - min_x,
                coords[1]['y'] - min_y,
                coords[1]['z'] - min_z
            )
            
            # Extract biome name from command string
            biome = command['command'].split()[-1].split(':')[-1]
            
            self.regions.append(BiomeRegion(start, end, biome))
    
    def get_biome_at(self, x: int, y: int, z: int) -> Optional[str]:
        """Get the biome at a specific point."""
        point = Point3D(x, y, z)
        
        # Check regions in order (remember they're already in reverse priority)
        for region in self.regions:
            if region.contains_point(point):
                return region.biome

        return DEFAULT_BIOME
    
    def get_nearby_biomes(self, x: int, y: int, z: int, proximity: float = 10.0) -> List[Tuple[str, float]]:
        """Get all biomes within the specified proximity of a point, with their distances."""
        point = Point3D(x, y, z)
        nearby_biomes: List[Tuple[str, float]] = []
        
        # Check each region
        for region in self.regions:
            distance = region.min_distance_to_point(point)
            if distance <= proximity:
                nearby_biomes.append((region.biome, distance))
        
        # Sort by distance
        return sorted(nearby_biomes, key=lambda x: x[1])
