from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.repository import Sentido
from app.core.schemas import FiltrosDeListado

OrdenCategorias = Literal["nombre", "padre"]


class FiltrosCategorias(FiltrosDeListado):
    """Query params de GET /categorias/lista. `parent_id` y `raiz` son el combo de agrupación."""

    parent_id: int | None = Field(default=None, description="Solo las subcategorías directas de esta categoría")
    raiz: bool = Field(default=False, description="Solo las categorías raíz (sin padre)")
    orden: OrdenCategorias = "nombre"
    sentido: Sentido = "asc"


class CategoriaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    descripcion: str | None = None
    parent_id: int | None = None

    @field_validator("nombre")
    @classmethod
    def nombre_sin_espacios(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre no puede estar vacío")
        return value


class CategoriaUpdate(BaseModel):
    """Edición parcial. Para mover a la raíz se envía `parent_id: null` explícito."""

    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    descripcion: str | None = None
    parent_id: int | None = None

    @field_validator("nombre")
    @classmethod
    def nombre_sin_espacios(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("El nombre no puede estar vacío")
        return value


class CategoriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None
    nombre: str
    descripcion: str | None
    created_at: datetime
    deleted_at: datetime | None = None
    # Se completa en los listados para no obligar al cliente a buscar al padre en otra página.
    parent_nombre: str | None = None


class CategoriaNode(BaseModel):
    id: int
    parent_id: int | None
    nombre: str
    descripcion: str | None
    children: list["CategoriaNode"] = []
