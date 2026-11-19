from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Monto = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


class PagoCreate(BaseModel):
    """El pago manual (efectivo o transferencia) debe coincidir con el total del pedido."""

    monto: Monto


class PagoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pedido_id: int
    forma_pago_codigo: str
    monto: Decimal
    mp_status: str
    mp_status_detail: str | None
    external_reference: str
    created_at: datetime


class FormaPagoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    nombre: str
