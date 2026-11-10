"""OrdenProduccion: produce un Producto final O un Ingrediente elaborado (exclusive arc)."""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Column, Numeric
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlmodel import Field, SQLModel

from app.core.db_types import created_at_field, updated_at_field


class EstadoOrden(enum.StrEnum):
    PLANIFICADA = "PLANIFICADA"
    EN_PROCESO = "EN_PROCESO"
    COMPLETADA = "COMPLETADA"
    CANCELADA = "CANCELADA"


class OrdenProduccion(SQLModel, table=True):
    __tablename__ = "orden_produccion"
    __table_args__ = (
        CheckConstraint("cantidad_a_producir > 0", name="ck_orden_cantidad"),
        # Toda orden produce exactamente una cosa.
        CheckConstraint("num_nonnulls(producto_id, ingrediente_id) = 1", name="ck_orden_salida_xor"),
    )

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    producto_id: int | None = Field(sa_type=BigInteger, default=None, foreign_key="producto.id", ondelete="RESTRICT")
    ingrediente_id: int | None = Field(
        sa_type=BigInteger, default=None, foreign_key="ingrediente.id", ondelete="RESTRICT"
    )
    cantidad_a_producir: Decimal = Field(sa_type=Numeric(12, 3), nullable=False)
    estado: EstadoOrden = Field(
        default=EstadoOrden.PLANIFICADA,
        sa_column=Column(
            PGEnum(EstadoOrden, name="estadoordenenum"),
            nullable=False,
            server_default=EstadoOrden.PLANIFICADA.value,
            index=True,
        ),
    )
    motivo_cancelacion: str | None = Field(default=None, max_length=200)
    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()
