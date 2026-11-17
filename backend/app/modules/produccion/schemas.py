from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.inventario.schemas import Cantidad
from app.modules.produccion.models import EstadoOrden


class OrdenCreate(BaseModel):
    """Una orden produce exactamente una cosa: un producto o un ingrediente elaborado."""

    producto_id: int | None = Field(default=None, gt=0)
    ingrediente_id: int | None = Field(default=None, gt=0)
    cantidad_a_producir: Cantidad

    @model_validator(mode="after")
    def _exactamente_uno(self) -> Self:
        if (self.producto_id is None) == (self.ingrediente_id is None):
            raise ValueError("Indique producto_id o ingrediente_id, y solo uno de los dos")
        return self


class OrdenCompletar(BaseModel):
    """Lote del producto resultante (opcional; los dos datos van juntos)."""

    codigo_lote: str | None = Field(default=None, max_length=50)
    fecha_vencimiento: datetime | None = None

    @field_validator("codigo_lote")
    @classmethod
    def _limpiar(cls, v: str | None) -> str | None:
        return v.strip() or None if v else None


class OrdenCancelar(BaseModel):
    motivo: str = Field(max_length=200)

    @field_validator("motivo")
    @classmethod
    def _no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El motivo de la cancelación es obligatorio")
        return v


class FiltrosOrdenes(BaseModel):
    estado: EstadoOrden | None = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class ComponenteOrden(BaseModel):
    """Insumo que consume la orden, calculado al planificar (receta × cantidad)."""

    ingrediente_id: int
    nombre: str
    cantidad: Decimal
    unidad_medida: str | None


class OrdenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int | None
    ingrediente_id: int | None
    nombre: str = ""  # del producto o ingrediente que se produce
    cantidad_a_producir: Decimal
    estado: EstadoOrden
    motivo_cancelacion: str | None
    created_at: datetime
    updated_at: datetime
    componentes: list[ComponenteOrden] = []
