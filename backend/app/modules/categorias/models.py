"""Categoria: árbol jerárquico por autorreferencia, con baja lógica."""

from datetime import datetime

from sqlalchemy import BigInteger, Text
from sqlmodel import Field, SQLModel

from app.core.db_types import created_at_field, deleted_at_field


class Categoria(SQLModel, table=True):
    __tablename__ = "categoria"

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    # Nula en la raíz.
    parent_id: int | None = Field(
        sa_type=BigInteger, default=None, foreign_key="categoria.id", ondelete="RESTRICT", index=True
    )
    nombre: str = Field(max_length=100, nullable=False, index=True)
    descripcion: str | None = Field(default=None, sa_type=Text)
    created_at: datetime = created_at_field()
    deleted_at: datetime | None = deleted_at_field()
