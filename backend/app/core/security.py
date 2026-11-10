"""Seguridad: bcrypt, JWT en cookie HttpOnly, refresh tokens y política de contraseñas."""

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import bcrypt
import jwt
from fastapi import Response

from app.core.config import get_settings
from app.core.errors import UnauthorizedError

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
# El refresh token solo viaja a los endpoints de auth: menor superficie de exposición.
REFRESH_COOKIE_PATH = "/api/v1/auth"

_BCRYPT_MAX_BYTES = 72


# --- Contraseñas -----------------------------------------------------------------------------


def validate_password_policy(password: str) -> str:
    """Mínimo 12 caracteres, al menos una mayúscula, un dígito y un carácter especial (sección 5.2).
    Pensado para usarse dentro de un `field_validator` de Pydantic."""
    if len(password) < 12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres")
    if not re.search(r"[A-Z]", password):
        raise ValueError("La contraseña debe incluir al menos una mayúscula")
    if not re.search(r"\d", password):
        raise ValueError("La contraseña debe incluir al menos un dígito")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("La contraseña debe incluir al menos un carácter especial")
    if len(password.encode()) > _BCRYPT_MAX_BYTES:
        raise ValueError("La contraseña no puede superar los 72 bytes")
    return password


def hash_password(password: str) -> str:
    rounds = get_settings().BCRYPT_ROUNDS
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:_BCRYPT_MAX_BYTES], password_hash.encode())
    except ValueError:
        return False


@lru_cache
def _dummy_hash() -> str:
    return hash_password("dummy-password-for-timing")


def verify_password_or_dummy(password: str, password_hash: str | None) -> bool:
    """Si el usuario no existe se compara contra un hash falso: el tiempo de respuesta no revela
    si el email está registrado."""
    if password_hash is None:
        verify_password(password, _dummy_hash())
        return False
    return verify_password(password, password_hash)


# --- Tokens ----------------------------------------------------------------------------------


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "type": "access", "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> int:
    """Verifica firma, expiración y tipo. Devuelve el id de usuario o lanza 401."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Token inválido o expirado", code="INVALID_TOKEN") from exc
    if payload.get("type") != "access":
        raise UnauthorizedError("Tipo de token inválido", code="INVALID_TOKEN")
    try:
        return int(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Token inválido", code="INVALID_TOKEN") from exc


def generate_refresh_token() -> tuple[str, str]:
    """Devuelve (token en claro para la cookie, hash SHA-256 para la base)."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=get_settings().REFRESH_TOKEN_EXPIRE_DAYS)


# --- Cookies ---------------------------------------------------------------------------------


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    common = {"httponly": True, "samesite": "lax", "secure": settings.COOKIE_SECURE}
    response.set_cookie(
        ACCESS_COOKIE, access_token, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/", **common
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=REFRESH_COOKIE_PATH,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)
