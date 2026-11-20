from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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


class PagoMercadoPago(BaseModel):
    """Lo que manda CardPayment al confirmar. El monto NO viaja: lo fija el servidor con el total del pedido."""

    pedido_id: int
    token: str = Field(min_length=1, max_length=200)
    payment_method_id: str = Field(min_length=1, max_length=40)
    installments: int = Field(default=1, ge=1, le=36)
    issuer_id: str | None = Field(default=None, max_length=40)
    email: EmailStr
    identification_type: str | None = Field(default=None, max_length=20)
    identification_number: str | None = Field(default=None, max_length=30)


class MercadoPagoConfig(BaseModel):
    """La clave pública es pública por diseño: el SDK del navegador la necesita para tokenizar la tarjeta."""

    public_key: str
