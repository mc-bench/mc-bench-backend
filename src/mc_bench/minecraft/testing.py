from typing import List

from .resources import PlacedMinecraftBlock


def test_scene(resource_loader) -> List[PlacedMinecraftBlock]:
    """Create a test scene with various Minecraft blocks to demonstrate rendering capabilities.

    The scene includes:
    - 10x10 grass block floor
    - 2x2 glass block structure
    - A simple tree (wood + leaves)
    - Torch
    - Glowstone block for emission testing

    Args:
        resource_loader: ResourceLoader instance to fetch block models

    Returns:
        List of PlacedBlock instances representing the test scene
    """
    blocks = []

    # Create 10x10 grass floor
    for x in range(10):
        for z in range(10):
            blocks.append(get_placed_block(resource_loader, "grass_block", x, 0, z))

    # Create 2x2 glass structure at (2,1,2)
    for x in range(2):
        for z in range(2):
            blocks.append(get_placed_block(resource_loader, "glass", x + 2, 1, z + 2))

    # Create tree at (5,1,5)
    # Tree trunk (3 blocks high)
    for y in range(1, 4):
        blocks.append(get_placed_block(resource_loader, "oak_log[axis=y]", 5, y, 5))

    # Tree leaves (3x3x3 cube, excluding corners and center)
    for x in range(4, 7):
        for y in range(3, 6):
            for z in range(4, 7):
                # Skip corners and center trunk
                if (x == 5 and z == 5) or (x in (4, 6) and z in (4, 6)):
                    continue
                blocks.append(get_placed_block(resource_loader, "oak_leaves", x, y, z))

    # Add torch at (7,1,7)
    blocks.append(get_placed_block(resource_loader, "torch", 7, 1, 7))

    # Add glowstone block at (7,1,3)
    blocks.append(get_placed_block(resource_loader, "glowstone", 7, 1, 3))

    return blocks


def test_scene_2(resource_loader) -> List[PlacedMinecraftBlock]:
    blocks = []

    blocks.append(get_placed_block(resource_loader, "grass_block", 0, 0, 0))
    blocks.append(get_placed_block(resource_loader, "grass_block", 0, 0, 1))
    blocks.append(get_placed_block(resource_loader, "grass_block", 1, 0, 0))
    blocks.append(get_placed_block(resource_loader, "grass_block", 1, 0, 1))

    return blocks


def get_placed_block(resource_loader, block_type, x, y, z):
    """Helper function to create a PlacedBlock instance.

    Args:
        rl: ResourceLoader instance
        block_type: String name of the block type
        x: X coordinate
        y: Y coordinate
        z: Z coordinate

    Returns:
        PlacedBlock instance at the specified location
    """
    block = resource_loader.get_block(block_type).to_minecraft_block()
    return PlacedMinecraftBlock(
        block, x=x, y=y, z=z, biome="plains", adjacent_biomes=[]
    )
