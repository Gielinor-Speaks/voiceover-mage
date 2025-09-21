# ABOUTME: TypeAdapter utilities for JSON serialization in persistence layer
# ABOUTME: Enables seamless Pydantic model ↔ SQLModel JSON column integration

from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.engine import Dialect


class PydanticJson(TypeDecorator[Any]):
    """
    A SQLAlchemy TypeDecorator that uses Pydantic's TypeAdapter for JSON serialization
    and deserialization. This allows for complex Pydantic models to be stored in JSON
    columns with automatic validation and conversion.

    See: https://github.com/fastapi/sqlmodel/issues/63#issuecomment-2727480036
    """

    impl = JSON()
    cache_ok = True

    def __init__(self, pydantic_type: type) -> None:
        super().__init__(self.impl)
        self.type_adapter = TypeAdapter(pydantic_type)

    def coerce_compared_value(self, op: Any, value: Any) -> Any:
        return self.impl.coerce_compared_value(op, value)  # type: ignore[misc]

    def bind_processor(self, dialect: Dialect) -> Any:
        def process(value: Any) -> bytes | None:
            return self.type_adapter.dump_json(value) if value is not None else None

        return process

    def result_processor(self, dialect: Dialect, coltype: Any) -> Any:
        def process(value: Any) -> Any:
            return self.type_adapter.validate_json(value) if value is not None else None

        return process
