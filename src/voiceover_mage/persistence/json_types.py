# ABOUTME: TypeAdapter utilities for JSON serialization in persistence layer
# ABOUTME: Enables seamless Pydantic model ↔ SQLModel JSON column integration

from pydantic import TypeAdapter
from sqlalchemy import TypeDecorator
from sqlmodel import JSON


class PydanticJson(TypeDecorator):
    """
    A SQLAlchemy TypeDecorator that uses Pydantic's TypeAdapter for JSON serialization
    and deserialization. This allows for complex Pydantic models to be stored in JSON
    columns with automatic validation and conversion.

    See: https://github.com/fastapi/sqlmodel/issues/63#issuecomment-2727480036
    """

    impl = JSON()
    cache_ok = True

    def __init__(self, pt):
        super().__init__()
        self.pt = TypeAdapter(pt)

    def coerce_compared_value(self, op, value):
        return super().coerce_compared_value(op, value)

    def bind_processor(self, dialect):
        return lambda value: self.pt.dump_json(value) if value is not None else None

    def result_processor(self, dialect, coltype):
        return lambda value: self.pt.validate_json(value) if value is not None else None
