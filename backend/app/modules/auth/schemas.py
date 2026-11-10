from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import validate_password_policy


class RegisterRequest(BaseModel):
    """El registro público NO acepta roles: siempre se asigna CLIENT (RN-15)."""

    nombre: str = Field(min_length=1, max_length=80)
    apellido: str = Field(min_length=1, max_length=80)
    email: EmailStr
    telefono: str | None = Field(default=None, max_length=30)
    password: str

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


class ChangePasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str

    @field_validator("password_nueva")
    @classmethod
    def politica_de_contrasenia(cls, value: str) -> str:
        return validate_password_policy(value)
