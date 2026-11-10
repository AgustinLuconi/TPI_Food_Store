"""Lógica de autenticación (sin estado). Lanza excepciones de dominio, nunca HTTPException."""

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from app.core.db_types import utcnow
from app.core.errors import AccountStateError, ConflictError, UnauthorizedError, ValidationError
from app.core.rate_limit import clear_failed_logins, ensure_login_allowed, register_failed_login
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
    verify_password_or_dummy,
)
from app.modules.auth.schemas import ChangePasswordRequest, RegisterRequest
from app.modules.auth.uow import AuthUnitOfWork
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import UsuarioRead
from app.modules.usuarios.service import to_read

ROL_REGISTRO_PUBLICO = "CLIENT"


@dataclass(frozen=True)
class Sesion:
    """Resultado de un login/refresh. Los tokens van SOLO en cookies, nunca en el cuerpo."""

    usuario: UsuarioRead
    access_token: str
    refresh_token: str


def _emitir_tokens(uow: AuthUnitOfWork, usuario: Usuario) -> tuple[str, str]:
    access = create_access_token(usuario.id)  # type: ignore[arg-type]
    raw_refresh, refresh_hash = generate_refresh_token()
    uow.refresh_tokens.issue(usuario.id, refresh_hash, refresh_token_expiry())  # type: ignore[arg-type]
    return access, raw_refresh


def _cuenta_activa(usuario: Usuario | None) -> bool:
    return usuario is not None and not usuario.disabled and usuario.deleted_at is None


def registrar(uow: AuthUnitOfWork, datos: RegisterRequest) -> UsuarioRead:
    with uow:
        # El email es único incluso entre usuarios dados de baja.
        if uow.usuarios.get_by_email(datos.email) is not None:
            raise ConflictError("Ya existe un usuario con ese email", code="EMAIL_TAKEN", field="email")
        usuario = Usuario(
            nombre=datos.nombre,
            apellido=datos.apellido,
            email=datos.email.lower(),
            telefono=datos.telefono,
            password_hash=hash_password(datos.password),
        )
        try:
            uow.usuarios.create(usuario)
        except IntegrityError as exc:
            raise ConflictError("Ya existe un usuario con ese email", code="EMAIL_TAKEN", field="email") from exc
        # RN-15: el registro público SIEMPRE asigna CLIENT.
        uow.usuarios.replace_roles(usuario.id, [ROL_REGISTRO_PUBLICO], asignado_por_id=None)  # type: ignore[arg-type]
        return to_read(usuario, [ROL_REGISTRO_PUBLICO])


def login(uow: AuthUnitOfWork, email: str, password: str, ip: str) -> Sesion:
    ensure_login_allowed(ip)
    with uow:
        usuario = uow.usuarios.get_by_email(email)
        # Se compara siempre (aun si el usuario no existe) para no revelar qué emails están registrados.
        credenciales_ok = verify_password_or_dummy(password, usuario.password_hash if usuario else None)
        if not credenciales_ok:
            register_failed_login(ip)
            raise UnauthorizedError("Credenciales inválidas", code="INVALID_CREDENTIALS")
        if not _cuenta_activa(usuario):
            # Problema de estado de la cuenta, no de credenciales (400). Solo se revela con la contraseña correcta.
            raise AccountStateError("La cuenta está bloqueada o dada de baja")
        assert usuario is not None
        clear_failed_logins(ip)
        access, refresh = _emitir_tokens(uow, usuario)
        return Sesion(to_read(usuario, uow.usuarios.get_roles(usuario.id)), access, refresh)  # type: ignore[arg-type]


def refrescar(uow: AuthUnitOfWork, refresh_token: str | None) -> Sesion:
    """Emite un nuevo access token y ROTA el refresh token (revoca el anterior)."""
    if not refresh_token:
        raise UnauthorizedError("Sesión no iniciada", code="NOT_AUTHENTICATED")
    with uow:
        registro = uow.refresh_tokens.get_by_hash(hash_refresh_token(refresh_token))
        if registro is None or registro.revoked_at is not None or registro.expires_at <= utcnow():
            raise UnauthorizedError("Refresh token inválido o expirado", code="INVALID_TOKEN")
        usuario = uow.usuarios.get_by_id(registro.usuario_id)
        if not _cuenta_activa(usuario):
            raise UnauthorizedError("Cuenta inexistente o bloqueada", code="INVALID_TOKEN")
        assert usuario is not None
        uow.refresh_tokens.revoke(registro)
        access, refresh = _emitir_tokens(uow, usuario)
        return Sesion(to_read(usuario, uow.usuarios.get_roles(usuario.id)), access, refresh)  # type: ignore[arg-type]


def cerrar_sesion(uow: AuthUnitOfWork, usuario_id: int, refresh_token: str | None) -> None:
    """Completa revoked_at del refresh token. Las cookies las borra el router."""
    if not refresh_token:
        return
    with uow:
        registro = uow.refresh_tokens.get_by_hash(hash_refresh_token(refresh_token))
        if registro is not None and registro.usuario_id == usuario_id:
            uow.refresh_tokens.revoke(registro)


def usuario_actual(uow: AuthUnitOfWork, usuario_id: int) -> UsuarioRead:
    with uow:
        usuario = uow.usuarios.get_by_id(usuario_id)
        if not _cuenta_activa(usuario):
            raise UnauthorizedError("Cuenta inexistente o bloqueada", code="INVALID_TOKEN")
        assert usuario is not None
        return to_read(usuario, uow.usuarios.get_roles(usuario_id))


def cambiar_password(uow: AuthUnitOfWork, usuario_id: int, datos: ChangePasswordRequest) -> Sesion:
    """Valida la contraseña actual, aplica la nueva y revoca TODAS las sesiones.
    Devuelve una sesión nueva para que quien cambió la contraseña no quede deslogueado."""
    with uow:
        usuario = uow.usuarios.get_by_id(usuario_id)
        if not _cuenta_activa(usuario):
            raise UnauthorizedError("Cuenta inexistente o bloqueada", code="INVALID_TOKEN")
        assert usuario is not None
        if not verify_password(datos.password_actual, usuario.password_hash):
            raise ValidationError("La contraseña actual es incorrecta", code="WRONG_PASSWORD", field="password_actual")
        if verify_password(datos.password_nueva, usuario.password_hash):
            raise ValidationError(
                "La nueva contraseña debe ser distinta de la actual", code="SAME_PASSWORD", field="password_nueva"
            )
        uow.usuarios.update(usuario, {"password_hash": hash_password(datos.password_nueva)})
        uow.refresh_tokens.revoke_all_for_user(usuario_id)
        access, refresh = _emitir_tokens(uow, usuario)
        return Sesion(to_read(usuario, uow.usuarios.get_roles(usuario_id)), access, refresh)
