"""DireccionEntrega: con coordenadas para la cobertura (sección 10.2)."""

from datetime import datetime

from sqlalchemy import BigInteger, Double, Index, Text, text
from sqlmodel import Field, SQLModel

from app.core.db_types import created_at_field, deleted_at_field


class DireccionEntrega(SQLModel, table=True):
    __tablename__ = "direccion_entrega"
    __table_args__ = (
        # RN-17: a lo sumo una dirección principal activa por usuario (índice único parcial).
        Index(
            "uq_direccion_principal_activa",
            "usuario_id",
            unique=True,
            postgresql_where=text("es_principal AND deleted_at IS NULL"),
        ),
    )

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    usuario_id: int = Field(
        sa_type=BigInteger, foreign_key="usuario.id", ondelete="CASCADE", nullable=False, index=True
    )
    alias: str | None = Field(default=None, max_length=50)
    linea1: str = Field(sa_type=Text, nullable=False)
    linea2: str | None = Field(default=None, sa_type=Text)
    ciudad: str | None = Field(default=None, max_length=100)
    provincia: str | None = Field(default=None, max_length=100)
    codigo_postal: str | None = Field(default=None, max_length=20)
    lat: float | None = Field(default=None, sa_type=Double)
    lng: float | None = Field(default=None, sa_type=Double)
    es_principal: bool = Field(default=False, nullable=False, sa_column_kwargs={"server_default": text("false")})
    created_at: datetime = created_at_field()
    deleted_at: datetime | None = deleted_at_field()
