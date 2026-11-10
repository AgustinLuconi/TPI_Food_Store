"""Dependencias de FastAPI: usuario autenticado y autorización por rol.

Invariante de seguridad (sección 5.3): el rol se verifica en CADA request contra la base de datos,
no contra el token. Si un usuario pierde un rol, el cambio rige en su siguiente request.
"""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Request

from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import ACCESS_COOKIE, decode_access_token
from app.modules.usuarios.deps import get_usuarios_uow
from app.modules.usuarios.uow import UsuariosUnitOfWork


@dataclass(frozen=True)
class CurrentUser:
    id: int
    email: str
    nombre: str
    apellido: str
    roles: frozenset[str]


def get_current_user(request: Request, uow: UsuariosUnitOfWork = Depends(get_usuarios_uow)) -> CurrentUser:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise UnauthorizedError("No autenticado", code="NOT_AUTHENTICATED")
    user_id = decode_access_token(token)

    with uow:
        usuario = uow.usuarios.get_by_id(user_id)  # excluye usuarios dados de baja
        if usuario is None or usuario.disabled:
            raise UnauthorizedError("Cuenta inexistente o bloqueada", code="INVALID_TOKEN")
        roles = frozenset(uow.usuarios.get_roles(user_id))
        return CurrentUser(
            id=usuario.id,  # type: ignore[arg-type]
            email=usuario.email,
            nombre=usuario.nombre,
            apellido=usuario.apellido,
            roles=roles,
        )


def require_roles(*allowed: str) -> Callable[[CurrentUser], CurrentUser]:
    """Dependencia que exige al menos uno de los roles indicados (403 si no)."""
    allowed_set = frozenset(allowed)

    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not (user.roles & allowed_set):
            raise ForbiddenError("No tiene permisos para realizar esta acción", code="INSUFFICIENT_ROLE")
        return user

    return dependency
