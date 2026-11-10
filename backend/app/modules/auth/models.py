"""Sesiones: RefreshToken (se guarda solo el hash SHA-256 del token)."""

from datetime import datetime

from sqlalchemy import CHAR, BigInteger
from sqlmodel import Field, SQLModel

from app.core.db_types import created_at_field, timestamptz_field


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_token"

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    usuario_id: int = Field(
        sa_type=BigInteger, foreign_key="usuario.id", ondelete="CASCADE", nullable=False, index=True
    )
    token_hash: str = Field(sa_type=CHAR(64), nullable=False, unique=True, index=True)
    expires_at: datetime = timestamptz_field()
    # Nulo = sesión activa.
    revoked_at: datetime | None = timestamptz_field(nullable=True)
    created_at: datetime = created_at_field()
