"""FormaPago (catálogo) y Pago. Un solo registro de Pago por pedido: los reintentos lo actualizan."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Numeric, text
from sqlmodel import Field, SQLModel

from app.core.db_types import created_at_field, updated_at_field


class FormaPago(SQLModel, table=True):
    """Catálogo con clave semántica (seed): EFECTIVO, TRANSFERENCIA, MERCADOPAGO."""

    __tablename__ = "forma_pago"

    codigo: str = Field(primary_key=True, max_length=20)
    nombre: str = Field(max_length=80, nullable=False)
    habilitado: bool = Field(default=True, nullable=False, sa_column_kwargs={"server_default": text("true")})


class Pago(SQLModel, table=True):
    __tablename__ = "pago"

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    pedido_id: int = Field(sa_type=BigInteger, foreign_key="pedido.id", ondelete="RESTRICT", nullable=False, index=True)
    forma_pago_codigo: str = Field(max_length=20, foreign_key="forma_pago.codigo", ondelete="RESTRICT", nullable=False)
    monto: Decimal = Field(sa_type=Numeric(10, 2), nullable=False)
    # Campos de MercadoPago (Anexo B). mp_status usa el vocabulario de MercadoPago.
    mp_payment_id: int | None = Field(default=None, sa_type=BigInteger, unique=True)
    mp_status: str = Field(
        default="pending", max_length=30, nullable=False, sa_column_kwargs={"server_default": "pending"}
    )
    mp_status_detail: str | None = Field(default=None, max_length=120)
    external_reference: str = Field(max_length=100, nullable=False, unique=True, index=True)
    idempotency_key: str = Field(max_length=100, nullable=False, unique=True)
    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()
