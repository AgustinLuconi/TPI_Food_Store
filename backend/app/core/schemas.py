"""Schemas transversales: paginación y formato de error."""

import math
from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    detail: str
    code: str
    field: str | None = None


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def build(cls, items: Sequence[T], total: int, page: int, size: int) -> "Paginated[T]":
        return cls(items=list(items), total=total, page=page, size=size, pages=math.ceil(total / size) if size else 0)


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
