"""Schemas transversales: paginación, filtros de los listados y formato de error."""

import math
from collections.abc import Sequence
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

# Filtro de estado de las pantallas de maestros (sección 11.5): Activos por defecto.
Estado = Literal["activos", "inactivos", "todos"]


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


class FiltrosDeListado(BaseModel):
    """Query params comunes de los listados de maestros: búsqueda, estado y paginación.

    Cada módulo lo extiende con su agrupación y sus columnas de orden, y el router lo recibe con
    `Annotated[Filtros, Query()]`.
    """

    search: str | None = Field(default=None, description="Búsqueda parcial por nombre")
    estado: Estado = "activos"
    incluir_inactivos: bool = Field(default=False, description="Equivale a estado=todos (sección 6)")
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

    @property
    def estado_efectivo(self) -> Estado:
        return "todos" if self.incluir_inactivos else self.estado
