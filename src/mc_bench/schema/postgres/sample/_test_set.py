"""
A test set is a collection of samples that can be voted on in structured evaluation workflows.

Test sets provide a comprehensive framework to organize samples for systematic assessment by human evaluators.
They enable administrators to strategically group related samples for targeted evaluation campaigns,
track voting progress at individual and aggregate levels, and generate detailed statistical analyses
on evaluator preferences and consensus patterns. Each test set maintains bidirectional relationships
with the samples it contains and all votes cast on those samples, creating a complete evaluation ecosystem.

Key characteristics of test sets include:
- Unique identification through name, description, and UUID
- User attribution via created_by tracking
- Flexible organization allowing any sample to belong to multiple test sets
- Hierarchical structure supporting the primary organizational unit for evaluation campaigns
- Scalable design accommodating any number of samples and votes across multiple criteria

Test sets serve as the foundation for various evaluation activities:

1. Systematic evaluation of AI-generated outputs against specific quality metrics
2. Comparative assessment of different model versions, prompts, or system configurations
3. Collection of fine-grained human preferences for training reward models and alignment research
4. Quantitative measurement of output quality across multiple evaluation dimensions
5. Aggregation of evaluator consensus to identify patterns in subjective preferences
6. Longitudinal tracking of model improvements through consistent evaluation frameworks
7. Controlled A/B testing of different generation approaches against the same prompts

The test_set table forms the core of the evaluation database schema, with relationships
to samples, votes, criteria, and users, enabling comprehensive evaluation workflows.
"""

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    func,
    text,
)

from .._metadata import metadata

test_set = Table(
    "test_set",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column("name", String, unique=True, nullable=False),
    Column("description", String, nullable=False),
    comment=__doc__.strip(),
    schema="sample",
)
