"""HTTP puro de autenticación. Los tokens viajan solo en cookies HttpOnly, nunca en el cuerpo."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.core.deps import CurrentUser, get_current_user
from app.core.security import REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies
from app.modules.auth import service
from app.modules.auth.deps import get_auth_uow
from app.modules.auth.schemas import ChangePasswordRequest, RegisterRequest
from app.modules.auth.uow import AuthUnitOfWork
from app.modules.usuarios.schemas import UsuarioRead

router = APIRouter(prefix="/auth", tags=["auth"])

Uow = Annotated[AuthUnitOfWork, Depends(get_auth_uow)]
Authenticated = Annotated[CurrentUser, Depends(get_current_user)]


def _client_ip(request: Request) -> str:
    # Con uvicorn --proxy-headers detrás de Nginx, request.client ya es la IP real del cliente.
    return request.client.host if request.client else "unknown"


@router.post("/register", status_code=201, response_model=UsuarioRead)
def registrar(body: RegisterRequest, uow: Uow):
    return service.registrar(uow, body)


@router.post("/token", response_model=UsuarioRead)
def login(
    request: Request,
    response: Response,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    uow: Uow,
):
    """OAuth2 Password Flow (x-www-form-urlencoded: username = email, password)."""
    sesion = service.login(uow, form.username, form.password, _client_ip(request))
    set_auth_cookies(response, sesion.access_token, sesion.refresh_token)
    return sesion.usuario


@router.post("/refresh", response_model=UsuarioRead)
def refresh(request: Request, response: Response, uow: Uow):
    sesion = service.refrescar(uow, request.cookies.get(REFRESH_COOKIE))
    set_auth_cookies(response, sesion.access_token, sesion.refresh_token)
    return sesion.usuario


@router.post("/logout", status_code=204)
def logout(request: Request, user: Authenticated, uow: Uow):
    service.cerrar_sesion(uow, user.id, request.cookies.get(REFRESH_COOKIE))
    response = Response(status_code=204)
    clear_auth_cookies(response)
    return response


@router.get("/me", response_model=UsuarioRead)
def me(user: Authenticated, uow: Uow):
    return service.usuario_actual(uow, user.id)


@router.put("/password", response_model=UsuarioRead)
def cambiar_password(body: ChangePasswordRequest, response: Response, user: Authenticated, uow: Uow):
    sesion = service.cambiar_password(uow, user.id, body)
    set_auth_cookies(response, sesion.access_token, sesion.refresh_token)
    return sesion.usuario
