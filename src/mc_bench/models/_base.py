from ..schema.postgres import metadata
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base(
    metadata=metadata,
)
