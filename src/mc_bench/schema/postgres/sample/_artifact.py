"""
Represents a file artifact associated with experimental runs and samples.

Artifacts are files or data assets generated during experiment execution, such as:
- Model outputs
- Generated images
- Evaluation metrics
- Raw data

Each artifact is categorized by its kind (artifact_kind_id) and linked to either
a specific run, a sample, or both. Artifacts are stored externally with bucket/key
references following an object storage pattern. The external_id provides a UUID
for public reference without exposing the internal ID.
"""

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    func,
    text,
)

from .._metadata import metadata

artifact = Table(
    "artifact",
    metadata,
    comment=__doc__.strip(),
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=True
    ),
    Column(
        "artifact_kind_id",
        Integer,
        ForeignKey("sample.artifact_kind.id"),
        nullable=False,
    ),
    Column(
        "run_id",
        Integer,
        ForeignKey("specification.run.id"),
        nullable=False,
    ),
    Column(
        "sample_id",
        Integer,
        ForeignKey("sample.sample.id"),
        nullable=True,
    ),
    Column("bucket", String, unique=False, nullable=False),
    Column("key", String, unique=False, nullable=False),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    # Add index for (sample_id, artifact_kind_id)
    Index("ix_artifact_sample_id_kind_id", "sample_id", "artifact_kind_id"),
    schema="sample",
)
