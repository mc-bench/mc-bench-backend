from sqlalchemy.orm import relationship

import mc_bench.schema.postgres as schema

from ._base import Base


class Sample(Base):
    __table__ = schema.sample.sample

    creator = relationship("User", foreign_keys=[schema.sample.sample.c.created_by])

    most_recent_editor = relationship(
        "User", foreign_keys=[schema.sample.sample.c.last_modified_by]
    )
