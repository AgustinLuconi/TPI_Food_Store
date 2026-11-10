"""Helpers de columnas compartidos por los modelos (timestamps con zona horaria, soft delete)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlmodel import Field


def utcnow() -> datetime:
    return datetime.now(UTC)


def created_at_field(*, index: bool = False) -> Any:
    return Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now()},
        nullable=False,
        index=index,
    )


def updated_at_field() -> Any:
    return Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now(), "onupdate": utcnow},
        nullable=False,
    )


def deleted_at_field() -> Any:
    """Baja lógica (RN-16): nula = activo."""
    return Field(default=None, sa_type=DateTime(timezone=True), nullable=True, index=True)


def timestamptz_field(*, nullable: bool = False, index: bool = False, default_now: bool = False) -> Any:
    kwargs: dict[str, Any] = {"sa_type": DateTime(timezone=True), "nullable": nullable, "index": index}
    if default_now:
        kwargs["default_factory"] = utcnow
        kwargs["sa_column_kwargs"] = {"server_default": func.now()}
    elif nullable:
        kwargs["default"] = None
    return Field(**kwargs)
