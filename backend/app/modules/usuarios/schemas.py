"""Schemas del módulo usuarios (la respuesta nunca incluye password_hash)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import validate_password_policy


class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    apellido: str
    email: str
    telefono: str | None = None
    disabled: bool
    roles: list[str]
    created_at: datetime
    deleted_at: datetime | None = None


class UsuarioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    apellido: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None
    telefono: str | None = Field(default=None, max_length=30)

    @field_validator("nombre", "apellido")
    @classmethod
    def sin_espacios_en_los_bordes(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class RolesUpdate(BaseModel):
    """Todo usuario conserva al menos un rol."""

    roles: list[str] = Field(min_length=1)


class EstadoUpdate(BaseModel):
    disabled: bool


class UsuarioCreate(BaseModel):
    """Alta por un administrador (RN-15: ADMIN solo se asigna por seed o por otro administrador)."""

    nombre: str = Field(min_length=1, max_length=80)
    apellido: str = Field(min_length=1, max_length=80)
    email: EmailStr
    telefono: str | None = Field(default=None, max_length=30)
    password: str
    roles: list[str] = Field(min_length=1)

    @field_validator("nombre", "apellido")
    @classmethod
    def sin_espacios_en_los_bordes(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("No puede estar vacío")
        return value

    @field_validator("password")
    @classmethod
    def politica_de_contrasenia(cls, value: str) -> str:
        return validate_password_policy(value)
