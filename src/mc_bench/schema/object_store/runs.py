from mc_bench.util.object_store import Prototype


class KINDS:
    RUN = "RUN"
    SAMPLE = "SAMPLE"
    ARTIFACTS = "ARTIFACTS"

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


runs = Prototype(
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
                            ],
                        )
                    ],
                )
            ],
        )
    ]
)
