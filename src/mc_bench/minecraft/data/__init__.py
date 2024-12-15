def get_block_types(version: str) -> list:
    if version == "1.20.1":
        import mc_bench.minecraft.data.versions.version_1_20_1
        blocks = mc_bench.minecraft.data.versions.version_1_20_1.blocks
    else:
        raise ValueError(f"Unsupported version: {version}")

    return [
        block["name"] for block in blocks
    ]
