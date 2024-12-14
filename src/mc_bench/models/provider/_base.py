import json

from sqlalchemy.orm import Mapped, relationship

import mc_bench.schema.postgres as schema

from .._base import Base


class Provider(Base):
    __table__ = schema.specification.provider

    model: Mapped["Model"] = relationship(  # noqa: F821
        "Model", lazy="joined", back_populates="providers"
    )

    def to_dict(self):
        return {
            "id": self.external_id,
            "name": self.name,
            "provider_class": self.provider_class,
            "config": json.loads(self.config)
            if isinstance(self.config, str)
            else self.config,
            "is_default": bool(self.is_default),
        }

    __mapper_args__ = {
        "polymorphic_on": "provider_class",
    }

    def execute_prompt(self, prompt):
        client = self.get_client()
        kwargs = (
            json.loads(self.config) if isinstance(self.config, str) else self.config
        ).copy()
        kwargs["prompt"] = prompt
        print(kwargs)
        return client.send_prompt(**kwargs)
