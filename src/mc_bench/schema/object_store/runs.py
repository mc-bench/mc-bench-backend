from mc_bench.util.object_store import Prototype


class KINDS:
    RUN = "run"
    SAMPLE = "sample"
    ARTIFACTS = "artifacts"
    NBT_STRUCTURE_FILE = "nbt-structure-file"
    PROMPT = "prompt"
    SCRIPT = "script"
    RAW_RESPONSE = "raw-response"
    BUILD_SCHEMATIC = "build-schematic"


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
                                    kind=KINDS.SCRIPT,
                                    pattern="{name}-script.py",
                                ),
                            ],
                        )
                    ],
                )
            ],
        )
    ]
)
