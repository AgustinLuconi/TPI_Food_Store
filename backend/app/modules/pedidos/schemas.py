from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.direcciones.schemas import DireccionRead
from app.modules.pagos.schemas import PagoRead

EstadoCodigo = Literal["PENDIENTE", "CONFIRMADO", "EN_PREPARACION", "EN_CAMINO", "ENTREGADO", "CANCELADO"]


class LineaCreate(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(ge=1, le=99)
    exclusiones: list[int] = Field(default_factory=list, max_length=30, description="Ingredientes que se quitan")

    @field_validator("exclusiones")
    @classmethod
    def _sin_repetidos(cls, v: list[int]) -> list[int]:
        return list(dict.fromkeys(v))


class PedidoCreate(BaseModel):
    """El carrito. `direccion_id` nulo es retiro en el local (costo de envío 0)."""

    items: list[LineaCreate] = Field(min_length=1, max_length=50)
    forma_pago_codigo: str = Field(min_length=1, max_length=20)
    direccion_id: int | None = Field(default=None, gt=0)
    notas: str | None = Field(default=None, max_length=500)

    @field_validator("forma_pago_codigo")
    @classmethod
    def _mayusculas(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("notas")
    @classmethod
    def _notas(cls, v: str | None) -> str | None:
        return v.strip() or None if v else None


class EstadoUpdate(BaseModel):
    estado: EstadoCodigo


class CancelarPedido(BaseModel):
    motivo: str = Field(max_length=500)

    @field_validator("motivo")
    @classmethod
    def _obligatorio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("RN-05: cancelar un pedido exige un motivo")
        return v


class FiltrosPedidos(BaseModel):
    estado: EstadoCodigo | None = None
    desde: date | None = None
    hasta: date | None = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def _rango(self) -> Self:
        if self.desde and self.hasta and self.desde > self.hasta:
            raise ValueError("`desde` no puede ser posterior a `hasta`")
        return self


class ExclusionRead(BaseModel):
    ingrediente_id: int
    nombre: str


class LineaRead(BaseModel):
    id: int
    producto_id: int
    nombre_snapshot: str
    precio_snapshot: Decimal
    cantidad: int
    subtotal: Decimal
    exclusiones: list[ExclusionRead] = []


class HistorialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estado_desde: str | None
    estado_hasta: str
    usuario_id: int | None
    motivo: str | None
    created_at: datetime


class PedidoItem(BaseModel):
    """Fila de los listados."""

    id: int
    usuario_id: int
    cliente_nombre: str
    estado_codigo: str
    forma_pago_codigo: str
    total: Decimal
    con_envio: bool
    created_at: datetime


class PedidoRead(BaseModel):
    """Detalle con líneas, exclusiones, pago e historial."""

    id: int
    usuario_id: int
    cliente_nombre: str
    estado_codigo: str
    forma_pago_codigo: str
    direccion_id: int | None
    direccion: DireccionRead | None
    subtotal: Decimal
    descuento: Decimal
    costo_envio: Decimal
    total: Decimal
    notas: str | None
    external_reference: str
    created_at: datetime
    updated_at: datetime
    lineas: list[LineaRead]
    pago: PagoRead | None
    historial: list[HistorialRead]
