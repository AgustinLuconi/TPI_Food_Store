"""Configuración de la aplicación (pydantic-settings). Sin valores por defecto para SECRET_KEY."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    # Obligatoria y sin valor por defecto: la app no arranca sin una clave de 32+ caracteres.
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    MEDIA_DIR: str = "./media"
    ENVIRONMENT: str = "development"

    # Coste de bcrypt: la especificación exige >= 12.
    BCRYPT_ROUNDS: int = Field(default=12, ge=12)

    # Rate limiting del login (sección 5.4): más de 5 intentos fallidos por IP en 15 minutos.
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_WINDOW_MINUTES: int = 15

    @field_validator("DATABASE_URL")
    @classmethod
    def usar_driver_psycopg(cls, value: str) -> str:
        """Acepta `postgresql://...` (como en la spec) y fuerza el driver psycopg 3."""
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def COOKIE_SECURE(self) -> bool:
        """`ENVIRONMENT=production` activa la bandera Secure de las cookies."""
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
