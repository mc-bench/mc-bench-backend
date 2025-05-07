"""
Object store schema for MC-Bench runs and samples.

This module defines the hierarchical structure for storing run data, samples, and artifacts
in the object store. It provides Prototype definitions that map logical object kinds to
physical storage paths following a consistent pattern.

The schema follows a hierarchical pattern:
- 'runs': Contains all run data organized by run_id
  - Each run contains samples identified by sample_id
    - Each sample has an artifacts directory with various output files
- 'comparison_samples': Stores comparison data for evaluation purposes

Each logical object kind maps to a physical storage path through Prototype definitions,
making it easy to locate and organize benchmark-related files.
"""

from mc_bench.util.object_store import Prototype


class KINDS:
    """
    Defines the logical object kinds used in the MC-Bench object store schema.
    
    These constants represent different types of data and artifacts that can be
    stored in the object store, providing a consistent naming convention for
    all benchmark-related objects.
    """
    RUN = "RUN"
    SAMPLE = "SAMPLE"
    ARTIFACTS = "ARTIFACTS"
    COMPARISON_SAMPLES = "COMPARISON_SAMPLES"

    # leaf nodes
    NBT_STRUCTURE_FILE = "NBT_STRUCTURE_FILE"
    PROMPT = "PROMPT"
    ORIGINAL_BUILD_SCRIPT_JS = "ORIGINAL_BUILD_SCRIPT_JS"
    ORIGINAL_BUILD_SCRIPT_PY = "ORIGINAL_BUILD_SCRIPT_PY"
    RAW_RESPONSE = "RAW_RESPONSE"
    BUILD_SCHEMATIC = "BUILD_SCHEMATIC"
    BUILD_COMMAND_LIST = "BUILD_COMMAND_LIST"
    BUILD_SUMMARY = "BUILD_SUMMARY"
    COMMAND_LIST_BUILD_SCRIPT_JS = "COMMAND_LIST_BUILD_SCRIPT_JS"
    COMMAND_LIST_BUILD_SCRIPT_PY = "COMMAND_LIST_BUILD_SCRIPT_PY"
    CONTENT_EXPORT_BUILD_SCRIPT_JS = "CONTENT_EXPORT_BUILD_SCRIPT_JS"
    CONTENT_EXPORT_BUILD_SCRIPT_PY = "CONTENT_EXPORT_BUILD_SCRIPT_PY"
    NORTHSIDE_CAPTURE_PNG = "NORTHSIDE_CAPTURE_PNG"
    EASTSIDE_CAPTURE_PNG = "EASTSIDE_CAPTURE_PNG"
    SOUTHSIDE_CAPTURE_PNG = "SOUTHSIDE_CAPTURE_PNG"
    WESTSIDE_CAPTURE_PNG = "WESTSIDE_CAPTURE_PNG"
    BUILD_CINEMATIC_MP4 = "BUILD_CINEMATIC_MP4"
    RENDERED_MODEL_GLB = "RENDERED_MODEL_GLB"
    RENDERED_MODEL_GLB_COMPARISON_SAMPLE = "RENDERED_MODEL_GLB_COMPARISON_SAMPLE"


runs = Prototype(
    comment="The main run data storage prototype defining the hierarchical structure for all benchmark run data and artifacts.",
    children=[
        Prototype(
            kind=KINDS.RUN,
            pattern="run/{run_id}",
            children=[
                Prototype(
                    kind=KINDS.SAMPLE,
                    pattern="sample/{sample_id}",
                    children=[
                        Prototype(
                            kind=KINDS.ARTIFACTS,
                            pattern="artifacts",
                            children=[
                                Prototype(
                                    kind=KINDS.BUILD_SCHEMATIC,
                                    pattern="{name}-build.schem",
                                ),
                                Prototype(
                                    kind=KINDS.PROMPT,
                                    pattern="{name}-prompt.txt",
                                ),
                                Prototype(
                                    kind=KINDS.ORIGINAL_BUILD_SCRIPT_PY,
                                    pattern="{name}-script.py",
                                ),
                                Prototype(
                                    kind=KINDS.ORIGINAL_BUILD_SCRIPT_JS,
                                    pattern="{name}-script.js",
                                ),
                                Prototype(
                                    kind=KINDS.BUILD_COMMAND_LIST,
                                    pattern="{name}-command-list.json",
                                ),
                                Prototype(
                                    kind=KINDS.BUILD_SUMMARY,
                                    pattern="{name}-summary.json",
                                ),
                                Prototype(
                                    kind=KINDS.COMMAND_LIST_BUILD_SCRIPT_PY,
                                    pattern="{name}-command-list-script.py",
                                ),
                                Prototype(
                                    kind=KINDS.COMMAND_LIST_BUILD_SCRIPT_JS,
                                    pattern="{name}-command-list-script.js",
                                ),
                                Prototype(
                                    kind=KINDS.NORTHSIDE_CAPTURE_PNG,
                                    pattern="{name}-northside-capture.png",
                                ),
                                Prototype(
                                    kind=KINDS.EASTSIDE_CAPTURE_PNG,
                                    pattern="{name}-eastside-capture.png",
                                ),
                                Prototype(
                                    kind=KINDS.SOUTHSIDE_CAPTURE_PNG,
                                    pattern="{name}-southside-capture.png",
                                ),
                                Prototype(
                                    kind=KINDS.WESTSIDE_CAPTURE_PNG,
                                    pattern="{name}-west-capture.png",
                                ),
                                Prototype(
                                    kind=KINDS.BUILD_CINEMATIC_MP4,
                                    pattern="{name}-build-timelapse.mp4",
                                ),
                                Prototype(
                                    kind=KINDS.RENDERED_MODEL_GLB,
                                    pattern="{name}-rendered-model.glb",
                                ),
                            ],
                        )
                    ],
                )
            ],
        )
    ]
)

comparison_samples = Prototype(
    comment="Storage prototype for comparison samples used for evaluation purposes.",
    kind=KINDS.COMPARISON_SAMPLES,
    pattern="comparison_samples",
    children=[
        Prototype(
            kind=KINDS.RENDERED_MODEL_GLB_COMPARISON_SAMPLE,
            pattern="sample-{sample_id}.glb",
        ),
    ],
)
