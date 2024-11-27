import mc_bench.schema.postgres as schema

from ._base import Base


class Comparison(Base):
    __table__ = schema.scoring.comparison


class Metric(Base):
    __table__ = schema.scoring.metric
