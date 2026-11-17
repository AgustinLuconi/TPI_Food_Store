from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.productos.models import TipoMovimiento

Cantidad = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]


class StockRead(BaseModel):
    """stock_real = lo que hay físicamente; stock_disponible = lo que todavía se puede prometer."""

    id: int
    stock_real: Decimal
    stock_disponible: Decimal


class MovimientoCreate(BaseModel):
    """Alta manual (RN-07). El signo lo aporta el tipo; la cantidad siempre es positiva."""

    tipo_movimiento: TipoMovimiento
    cantidad: Cantidad
    motivo: str | None = Field(default=None, max_length=120)

    @field_validator("motivo")
    @classmethod
    def _limpiar_motivo(cls, v: str | None) -> str | None:
        return v.strip() or None if v else None


class MovimientoProductoCreate(MovimientoCreate):
    """En una ENTRADA de producto, `codigo_lote` y `fecha_vencimiento` crean un lote (van juntos)."""

    codigo_lote: str | None = Field(default=None, max_length=50)
    fecha_vencimiento: datetime | None = None

    @field_validator("codigo_lote")
    @classmethod
    def _limpiar_codigo(cls, v: str | None) -> str | None:
        return v.strip() or None if v else None


class MovimientoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo_movimiento: TipoMovimiento
    cantidad: Decimal
    motivo: str | None
    fecha_registro: datetime
    lote_id: int | None = None
    pedido_id: int | None = None
    orden_produccion_id: int | None = None


class FiltrosMovimientos(BaseModel):
    tipo: TipoMovimiento | None = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class LoteRead(BaseModel):
    id: int
    codigo_lote: str
    fecha_vencimiento: datetime
    fecha_ingreso: datetime
    cantidad_inicial: Decimal
    stock_real: Decimal
    stock_disponible: Decimal
    vencido: bool


class LotePorVencer(LoteRead):
    producto_id: int
    producto_nombre: str
    dias_restantes: int
