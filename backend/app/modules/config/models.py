"""Dominio 4 · Configuración operativa. Sin FK hacia Pedido: son reglas de validación al crear el pedido."""

from datetime import datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, Double, Numeric, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.core.db_types import created_at_field, timestamptz_field


class ConfiguracionLocal(SQLModel, table=True):
    """Registro único (el Service no permite crear un segundo)."""

    __tablename__ = "configuracion_local"

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    nombre: str = Field(max_length=120, nullable=False)
    zona_horaria: str = Field(max_length=60, nullable=False)
    direccion_origen: str | None = Field(default=None, sa_type=Text)
    lat_origen: float | None = Field(default=None, sa_type=Double)
    lng_origen: float | None = Field(default=None, sa_type=Double)


class HorarioOperativo(SQLModel, table=True):
    """Admite varias franjas por día. dia_semana: 0 = lunes ... 6 = domingo."""

    __tablename__ = "horario_operativo"
    __table_args__ = (CheckConstraint("dia_semana BETWEEN 0 AND 6", name="ck_horario_dia_semana"),)

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    dia_semana: int = Field(sa_type=SmallInteger, nullable=False)
    hora_apertura: time = Field(nullable=False)
    hora_cierre: time = Field(nullable=False)
    activo: bool = Field(default=True, nullable=False, sa_column_kwargs={"server_default": text("true")})


class DiaBloqueado(SQLModel, table=True):
    """Feriados y cierres totales o parciales. Si todo_el_dia es falso, el Service exige hora_desde y hora_hasta."""

    __tablename__ = "dia_bloqueado"

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    fecha: datetime = timestamptz_field()
    motivo: str | None = Field(default=None, max_length=120)
    todo_el_dia: bool = Field(default=True, nullable=False, sa_column_kwargs={"server_default": text("true")})
    hora_desde: time | None = Field(default=None)
    hora_hasta: time | None = Field(default=None)


class ZonaCobertura(SQLModel, table=True):
    """Geocerca con tarifa de envío propia. Se anula con activo = false (sin deleted_at, según el ERD)."""

    __tablename__ = "zona_cobertura"

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    nombre: str = Field(max_length=120, nullable=False)
    poligono: Any = Field(sa_type=JSONB, nullable=False)
    tarifa_base: Decimal = Field(
        default=Decimal("0"), sa_type=Numeric(10, 2), nullable=False, sa_column_kwargs={"server_default": text("0")}
    )
    tarifa_por_km: Decimal = Field(
        default=Decimal("0"), sa_type=Numeric(10, 2), nullable=False, sa_column_kwargs={"server_default": text("0")}
    )
    pedido_minimo: Decimal = Field(
        default=Decimal("0"), sa_type=Numeric(10, 2), nullable=False, sa_column_kwargs={"server_default": text("0")}
    )
    activo: bool = Field(default=True, nullable=False, sa_column_kwargs={"server_default": text("true")})
    created_at: datetime = created_at_field()
