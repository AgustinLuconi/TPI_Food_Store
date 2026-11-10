"""HTTP puro: valida con schemas, verifica el rol y delega en el Service."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.core.deps import CurrentUser, require_roles
from app.core.schemas import Paginated
from app.modules.usuarios import service
from app.modules.usuarios.deps import get_usuarios_uow
from app.modules.usuarios.repository import Estado
from app.modules.usuarios.schemas import EstadoUpdate, RolesUpdate, UsuarioCreate, UsuarioRead, UsuarioUpdate
from app.modules.usuarios.uow import UsuariosUnitOfWork

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

AdminUser = Annotated[CurrentUser, Depends(require_roles("ADMIN"))]
Uow = Annotated[UsuariosUnitOfWork, Depends(get_usuarios_uow)]


@router.get("", response_model=Paginated[UsuarioRead])
def listar_usuarios(
    _: AdminUser,
    uow: Uow,
    search: str | None = None,
    rol: str | None = None,
    estado: Estado = "activos",
    incluir_inactivos: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """`estado` = activos (por defecto) | inactivos | todos. `incluir_inactivos=true` equivale a `todos`."""
    if incluir_inactivos:
        estado = "todos"
    return service.listar(uow, search=search, rol=rol, estado=estado, page=page, size=size)


@router.post("", status_code=201, response_model=UsuarioRead)
def crear_usuario(body: UsuarioCreate, admin: AdminUser, uow: Uow):
    return service.crear(uow, body, admin.id)


@router.get("/{usuario_id}", response_model=UsuarioRead)
def obtener_usuario(usuario_id: int, _: AdminUser, uow: Uow):
    return service.obtener(uow, usuario_id)


@router.put("/{usuario_id}", response_model=UsuarioRead)
def actualizar_usuario(usuario_id: int, body: UsuarioUpdate, _: AdminUser, uow: Uow):
    return service.actualizar(uow, usuario_id, body)


@router.put("/{usuario_id}/roles", response_model=UsuarioRead)
def asignar_roles(usuario_id: int, body: RolesUpdate, admin: AdminUser, uow: Uow):
    return service.asignar_roles(uow, usuario_id, body, admin.id)


@router.patch("/{usuario_id}/estado", response_model=UsuarioRead)
def cambiar_estado(usuario_id: int, body: EstadoUpdate, admin: AdminUser, uow: Uow):
    return service.cambiar_estado(uow, usuario_id, body, admin.id)


@router.patch("/{usuario_id}/reactivar", response_model=UsuarioRead)
def reactivar_usuario(usuario_id: int, _: AdminUser, uow: Uow):
    return service.reactivar(uow, usuario_id)


@router.delete("/{usuario_id}", status_code=204)
def eliminar_usuario(usuario_id: int, admin: AdminUser, uow: Uow):
    service.eliminar(uow, usuario_id, admin.id)
    return Response(status_code=204)
