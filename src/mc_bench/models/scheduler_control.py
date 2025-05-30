import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

import mc_bench.schema.postgres as schema
from mc_bench.models._base import Base


class SchedulerControl(Base):
    __table__ = schema.specification.scheduler_control

    @staticmethod
    def get_value(db: Session, key: str) -> Optional[Any]:
        """Get a control value by key with JSON deserialization.

        Args:
            db: Database session
            key: The control key to retrieve

        Returns:
            The deserialized value or None if not found
        """
        result = db.scalar(
            select(schema.specification.scheduler_control.c.value).where(
                schema.specification.scheduler_control.c.key == key
            )
        )
        if result is None:
            return None
        return json.loads(result)

    @staticmethod
    def get_all_controls(db: Session) -> Dict[str, Any]:
        """Get all control values as a dictionary.

        Args:
            db: Database session

        Returns:
            Dictionary of key-value pairs with deserialized values
        """
        results = db.execute(
            select(
                schema.specification.scheduler_control.c.key,
                schema.specification.scheduler_control.c.value,
            )
        ).all()

        return {key: json.loads(value) for key, value in results}

    @staticmethod
    def set_value(
        db: Session, key: str, value: Any, description: Optional[str] = None
    ) -> None:
        """Set a control value by key with JSON serialization.

        Args:
            db: Database session
            key: The control key to set
            value: The value to set (will be JSON serialized)
            description: Optional description for the control
        """
        # Serialize the value to JSON
        serialized_value = json.dumps(value)

        # Check if the key already exists
        existing = db.scalar(
            select(schema.specification.scheduler_control.c.id).where(
                schema.specification.scheduler_control.c.key == key
            )
        )

        if existing:
            # Update existing record
            db.execute(
                update(schema.specification.scheduler_control)
                .where(schema.specification.scheduler_control.c.key == key)
                .values(
                    value=serialized_value,
                    description=description
                    if description is not None
                    else schema.specification.scheduler_control.c.description,
                    last_modified=datetime.utcnow(),
                )
            )
        else:
            # Insert new record
            db.execute(
                insert(schema.specification.scheduler_control).values(
                    key=key,
                    value=serialized_value,
                    description=description,
                )
            )

        db.flush()
