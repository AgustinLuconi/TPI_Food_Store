"""Schemas del catálogo: productos, ingredientes y recetas."""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.repository import Sentido
from app.core.schemas import FiltrosDeListado

OrdenProductos = Literal["nombre", "precio"]
OrdenIngredientes = Literal["nombre"]

Dinero = Decimal  # DECIMAL(10,2): 8 enteros y 2 decimales
Cantidad = Decimal  # DECIMAL(10,3)


def _sin_espacios(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor = valor.strip()
    if not valor:
        raise ValueError("No puede estar vacío")
    return valor


# ----------------------------------------------------------------------------------------------
# Productos
# ----------------------------------------------------------------------------------------------


class FiltrosProductos(FiltrosDeListado):
    """Query params de GET /productos. `categoria_id` incluye las subcategorías."""

    categoria_id: int | None = Field(default=None, description="Productos de esta categoría y sus subcategorías")
    disponible: bool | None = Field(default=None, description="Visibilidad comercial")
    orden: OrdenProductos = "nombre"
    sentido: Sentido = "asc"


class _CategoriasDelProducto(BaseModel):
    categoria_ids: list[int] = Field(default_factory=list)
    categoria_principal_id: int | None = Field(
        default=None, description="Debe estar entre las categorías. Si se omite, es la primera."
    )

    @model_validator(mode="after")
    def principal_entre_las_categorias(self) -> Self:
        self.categoria_ids = list(dict.fromkeys(self.categoria_ids))
        if self.categoria_principal_id is not None and self.categoria_principal_id not in self.categoria_ids:
            raise ValueError("La categoría principal debe estar entre las categorías del producto")
        return self


class ProductoCreate(_CategoriasDelProducto):
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str | None = None
    precio_base: Dinero = Field(ge=0, max_digits=10, decimal_places=2)
    disponible: bool = True
    stock_minimo: int = Field(default=0, ge=0)

    @field_validator("nombre")
    @classmethod
    def nombre_sin_espacios(cls, valor: str) -> str:
        return _sin_espacios(valor)  # type: ignore[return-value]


class ProductoUpdate(BaseModel):
    """Edición parcial. Si se envían `categoria_ids`, reemplazan a las anteriores."""

    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = None
    precio_base: Dinero | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    disponible: bool | None = None
    stock_minimo: int | None = Field(default=None, ge=0)
    categoria_ids: list[int] | None = None
    categoria_principal_id: int | None = None

    @field_validator("nombre")
    @classmethod
    def nombre_sin_espacios(cls, valor: str | None) -> str | None:
        return _sin_espacios(valor)

    @model_validator(mode="after")
    def principal_entre_las_categorias(self) -> Self:
        if self.categoria_ids is not None:
            self.categoria_ids = list(dict.fromkeys(self.categoria_ids))
            principal = self.categoria_principal_id
            if principal is not None and principal not in self.categoria_ids:
                raise ValueError("La categoría principal debe estar entre las categorías del producto")
        return self


class DisponibilidadUpdate(BaseModel):
    disponible: bool


class CategoriaDelProducto(BaseModel):
    id: int
    nombre: str
    es_principal: bool


class IngredienteDelProducto(BaseModel):
    ingrediente_id: int
    nombre: str
    es_alergeno: bool
    cantidad_requerida: Decimal
    unidad_medida: str
    es_removible: bool


class ProductoRead(BaseModel):
    """Detalle con categorías, receta y alérgenos."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    imagen_url: str | None
    precio_base: Decimal
    disponible: bool
    stock_minimo: int
    categorias: list[CategoriaDelProducto] = []
    ingredientes: list[IngredienteDelProducto] = []
    alergenos: list[str] = []
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class ProductoItem(BaseModel):
    """Fila de los listados (sin receta, para no cargar de más)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    imagen_url: str | None
    precio_base: Decimal
    disponible: bool
    stock_minimo: int
    categorias: list[CategoriaDelProducto] = []
    deleted_at: datetime | None = None


# ----------------------------------------------------------------------------------------------
# Ingredientes
# ----------------------------------------------------------------------------------------------


class FiltrosIngredientes(FiltrosDeListado):
    es_alergeno: bool | None = None
    es_elaborado: bool | None = None
    orden: OrdenIngredientes = "nombre"
    sentido: Sentido = "asc"


class IngredienteCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    es_alergeno: bool = False
    es_elaborado: bool = Field(default=False, description="Sub-ensamble con receta propia")
    stock_minimo: int = Field(default=0, ge=0)

    @field_validator("nombre")
    @classmethod
    def nombre_sin_espacios(cls, valor: str) -> str:
        return _sin_espacios(valor)  # type: ignore[return-value]


class IngredienteUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    es_alergeno: bool | None = None
    es_elaborado: bool | None = None
    stock_minimo: int | None = Field(default=None, ge=0)

    @field_validator("nombre")
    @classmethod
    def nombre_sin_espacios(cls, valor: str | None) -> str | None:
        return _sin_espacios(valor)


class IngredienteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    es_alergeno: bool
    es_elaborado: bool
    stock_minimo: int
    deleted_at: datetime | None = None


# ----------------------------------------------------------------------------------------------
# Recetas
# ----------------------------------------------------------------------------------------------


def _unidad(valor: str) -> str:
    valor = valor.strip().upper()
    if not valor:
        raise ValueError("La unidad de medida no puede estar vacía")
    return valor


class RecetaProductoItem(BaseModel):
    ingrediente_id: int
    cantidad_requerida: Cantidad = Field(gt=0, max_digits=10, decimal_places=3)
    unidad_medida: str = Field(default="UN", min_length=1, max_length=10)
    es_removible: bool = True

    @field_validator("unidad_medida")
    @classmethod
    def unidad_en_mayusculas(cls, valor: str) -> str:
        return _unidad(valor)


class RecetaProductoUpdate(BaseModel):
    """Reemplaza la receta de venta completa."""

    items: list[RecetaProductoItem]


class RecetaIngredienteItem(BaseModel):
    componente_id: int
    cantidad_requerida: Cantidad = Field(gt=0, max_digits=10, decimal_places=3)
    unidad_medida: str = Field(default="UN", min_length=1, max_length=10)

    @field_validator("unidad_medida")
    @classmethod
    def unidad_en_mayusculas(cls, valor: str) -> str:
        return _unidad(valor)


class RecetaIngredienteUpdate(BaseModel):
    """Reemplaza la receta completa de un ingrediente elaborado."""

    items: list[RecetaIngredienteItem]


class RecetaIngredienteRead(BaseModel):
    componente_id: int
    nombre: str
    cantidad_requerida: Decimal
    unidad_medida: str
