from typing import Any, Dict

from nbt import nbt

from .resources import PlacedMinecraftBlock, ResourceLoader, MinecraftWorld

from .biome_lookup import BiomeLookup


def load_schematic(filename, biome_lookup: BiomeLookup):
    # Load NBT file
    nbt_file = nbt.NBTFile(filename, "rb")
    schematic = nbt_file["Schematic"]

    # Get dimensions
    width = schematic["Width"].value
    height = schematic["Height"].value
    length = schematic["Length"].value

    # Get palette
    palette = {k: v.value for k, v in schematic["Blocks"]["Palette"].items()}

    # Get block data
    block_data = list(schematic["Blocks"]["Data"].value)

    # Parse into blocks array
    return parse_minecraft_schematic(width, height, length, palette, block_data, biome_lookup)


def parse_minecraft_schematic(width, height, length, palette, block_data, biome_lookup: BiomeLookup):
    blocks = []

    # Convert palette to a lookup dictionary
    block_types = {v: k for k, v in palette.items()}

    # Iterate through each position
    for y in range(height):
        for z in range(length):
            for x in range(width):
                # Calculate index in the block_data array
                index = y * (length * width) + z * width + x

                # Get block type from palette using the block ID
                block_id = block_data[index]
                block_type = block_types[block_id]
                if block_type == "minecraft:air":
                    continue

                # Create block entry with position and type
                block = {
                    "position": (x, y, z),
                    "type": block_type.removeprefix("minecraft:"),
                    "biome": biome_lookup.get_biome_at(x, y, z),
                    "adjacent_biomes": biome_lookup.get_nearby_biomes(x, y, z),
                }
                blocks.append(block)

    return blocks


def to_minecraft_world(
    blocks: list[Dict[str, Any]], resource_loader: ResourceLoader
) -> MinecraftWorld:
    placed_blocks = []

    for block in blocks:
        minecraft_block = resource_loader.get_block(block["type"]).to_minecraft_block()
        placed_blocks.append(
            PlacedMinecraftBlock(
                block=minecraft_block,
                x=block["position"][0],
                y=block["position"][1],
                z=block["position"][2],
                biome=block["biome"],
                adjacent_biomes=block["adjacent_biomes"],
            )
        )

    return MinecraftWorld(placed_blocks)
