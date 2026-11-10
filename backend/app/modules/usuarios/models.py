"""Dominio 1 · Identidad y acceso: Usuario, Rol y UsuarioRol."""

from datetime import datetime

from sqlalchemy import CHAR, BigInteger, Text, text
from sqlmodel import Field, SQLModel

from app.core.db_types import (
    created_at_field,
    deleted_at_field,
    timestamptz_field,
    updated_at_field,
)


class Rol(SQLModel, table=True):
    """Catálogo con clave semántica (seed): ADMIN, STOCK, PEDIDOS, CLIENT."""

    __tablename__ = "rol"

    codigo: str = Field(primary_key=True, max_length=20)
    nombre: str = Field(max_length=80, nullable=False)
    descripcion: str | None = Field(default=None, sa_type=Text)


class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    nombre: str = Field(max_length=80, nullable=False)
    apellido: str = Field(max_length=80, nullable=False)
    # unique + index => un único índice único (ix_usuario_email). Sigue siendo único tras la baja lógica.
    email: str = Field(max_length=254, nullable=False, unique=True, index=True)
    telefono: str | None = Field(default=None, max_length=30)
    password_hash: str = Field(sa_type=CHAR(60), nullable=False)
    # Bloqueo administrativo, independiente de la baja lógica.
    disabled: bool = Field(default=False, nullable=False, sa_column_kwargs={"server_default": text("false")})
    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()
    deleted_at: datetime | None = deleted_at_field()


class UsuarioRol(SQLModel, table=True):
    __tablename__ = "usuario_rol"

    usuario_id: int = Field(sa_type=BigInteger, primary_key=True, foreign_key="usuario.id", ondelete="CASCADE")
    rol_codigo: str = Field(primary_key=True, max_length=20, foreign_key="rol.codigo", ondelete="RESTRICT")
    # Auditoría de la asignación.
    asignado_por_id: int | None = Field(sa_type=BigInteger, default=None, foreign_key="usuario.id", ondelete="SET NULL")
    asignado_at: datetime = timestamptz_field(default_now=True)
