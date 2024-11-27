import mc_bench.schema.postgres as schema

from ._base import Base


class Comparison(Base):
    __table__ = schema.scoring.comparison


class Metric(Base):
    __table__ = schema.scoring.metric

    def to_dict(self):
        return {
            "id": self.external_id,
            "name": self.name,
            "description": self.description,
        }
