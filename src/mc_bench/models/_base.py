from sqlalchemy.ext.declarative import declarative_base

from mc_bench.schema.postgres import metadata

Base = declarative_base(
    metadata=metadata,
)
