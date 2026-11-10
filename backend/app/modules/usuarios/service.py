"""Lógica de negocio de usuarios (sin estado). Lanza excepciones de dominio, nunca HTTPException."""

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.schemas import Paginated
from app.core.security import hash_password
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.repository import Estado
from app.modules.usuarios.schemas import EstadoUpdate, RolesUpdate, UsuarioCreate, UsuarioRead, UsuarioUpdate
from app.modules.usuarios.uow import UsuariosUnitOfWork


def to_read(usuario: Usuario, roles: list[str]) -> UsuarioRead:
    return UsuarioRead(
        id=usuario.id,  # type: ignore[arg-type]
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        email=usuario.email,
        telefono=usuario.telefono,
        disabled=usuario.disabled,
        roles=roles,
        created_at=usuario.created_at,
        deleted_at=usuario.deleted_at,
    )


def _obtener(uow: UsuariosUnitOfWork, usuario_id: int, *, incluir_baja: bool = False) -> Usuario:
    usuario = uow.usuarios.get_by_id(usuario_id, include_deleted=incluir_baja)
    if usuario is None:
        raise NotFoundError("Usuario no encontrado", code="USER_NOT_FOUND")
    return usuario


def _proteger_ultimo_admin(uow: UsuariosUnitOfWork, usuario: Usuario, accion: str) -> None:
    """Evita dejar el sistema sin ningún administrador activo (bloqueo total)."""
    es_admin_activo = (
        "ADMIN" in uow.usuarios.get_roles(usuario.id)  # type: ignore[arg-type]
        and usuario.deleted_at is None
        and not usuario.disabled
    )
    if es_admin_activo and uow.usuarios.count_activos_con_rol("ADMIN") <= 1:
        raise ConflictError(f"No se puede {accion} al único administrador activo", code="LAST_ADMIN")


def listar(
    uow: UsuariosUnitOfWork,
    *,
    search: str | None,
    rol: str | None,
    estado: Estado,
    page: int,
    size: int,
) -> Paginated[UsuarioRead]:
    with uow:
        if rol and uow.roles.get_by_codigo(rol) is None:
            raise ValidationError("Rol inexistente", code="UNKNOWN_ROLE", field="rol")
        items, total = uow.usuarios.search(search=search, rol=rol, estado=estado, page=page, size=size)
        roles_map = uow.usuarios.get_roles_map([u.id for u in items])  # type: ignore[misc]
        data = [to_read(u, roles_map[u.id]) for u in items]  # type: ignore[index]
    return Paginated.build(data, total, page, size)


def crear(uow: UsuariosUnitOfWork, datos: UsuarioCreate, admin_id: int) -> UsuarioRead:
    """Alta por un administrador, con los roles indicados y auditoría de quién los asignó."""
    with uow:
        if uow.usuarios.get_by_email(datos.email) is not None:
            raise ConflictError("Ya existe un usuario con ese email", code="EMAIL_TAKEN", field="email")
        desconocidos = set(datos.roles) - uow.roles.codigos()
        if desconocidos:
            raise ValidationError(
                f"Roles inexistentes: {', '.join(sorted(desconocidos))}", code="UNKNOWN_ROLE", field="roles"
            )
        usuario = uow.usuarios.create(
            Usuario(
                nombre=datos.nombre,
                apellido=datos.apellido,
                email=datos.email.lower(),
                telefono=datos.telefono,
                password_hash=hash_password(datos.password),
            )
        )
        uow.usuarios.replace_roles(usuario.id, datos.roles, asignado_por_id=admin_id)  # type: ignore[arg-type]
        return to_read(usuario, uow.usuarios.get_roles(usuario.id))  # type: ignore[arg-type]


def obtener(uow: UsuariosUnitOfWork, usuario_id: int) -> UsuarioRead:
    with uow:
        usuario = _obtener(uow, usuario_id, incluir_baja=True)
        return to_read(usuario, uow.usuarios.get_roles(usuario_id))


def actualizar(uow: UsuariosUnitOfWork, usuario_id: int, datos: UsuarioUpdate) -> UsuarioRead:
    cambios = datos.model_dump(exclude_unset=True)
    with uow:
        usuario = _obtener(uow, usuario_id)
        nuevo_email = cambios.get("email")
        if nuevo_email and nuevo_email.lower() != usuario.email.lower():
            # El email sigue siendo único incluso entre usuarios dados de baja.
            if uow.usuarios.get_by_email(nuevo_email) is not None:
                raise ConflictError("Ya existe un usuario con ese email", code="EMAIL_TAKEN", field="email")
            cambios["email"] = nuevo_email.lower()
        if cambios:
            uow.usuarios.update(usuario, cambios)
        return to_read(usuario, uow.usuarios.get_roles(usuario_id))


def asignar_roles(uow: UsuariosUnitOfWork, usuario_id: int, datos: RolesUpdate, admin_id: int) -> UsuarioRead:
    with uow:
        usuario = _obtener(uow, usuario_id)
        desconocidos = set(datos.roles) - uow.roles.codigos()
        if desconocidos:
            raise ValidationError(
                f"Roles inexistentes: {', '.join(sorted(desconocidos))}", code="UNKNOWN_ROLE", field="roles"
            )
        if "ADMIN" not in datos.roles:
            _proteger_ultimo_admin(uow, usuario, "quitar el rol ADMIN a")
        uow.usuarios.replace_roles(usuario_id, datos.roles, asignado_por_id=admin_id)
        return to_read(usuario, uow.usuarios.get_roles(usuario_id))


def cambiar_estado(uow: UsuariosUnitOfWork, usuario_id: int, datos: EstadoUpdate, admin_id: int) -> UsuarioRead:
    with uow:
        usuario = _obtener(uow, usuario_id)
        if datos.disabled:
            if usuario.id == admin_id:
                raise ConflictError("No puede bloquear su propia cuenta", code="SELF_ACTION")
            _proteger_ultimo_admin(uow, usuario, "bloquear")
        uow.usuarios.update(usuario, {"disabled": datos.disabled})
        return to_read(usuario, uow.usuarios.get_roles(usuario_id))


def eliminar(uow: UsuariosUnitOfWork, usuario_id: int, admin_id: int) -> None:
    """Baja lógica (RN-16)."""
    with uow:
        usuario = _obtener(uow, usuario_id)
        if usuario.id == admin_id:
            raise ConflictError("No puede dar de baja su propia cuenta", code="SELF_ACTION")
        _proteger_ultimo_admin(uow, usuario, "dar de baja")
        uow.usuarios.soft_delete(usuario)


def reactivar(uow: UsuariosUnitOfWork, usuario_id: int) -> UsuarioRead:
    """Reactivar limpia deleted_at (sección 11.5)."""
    with uow:
        usuario = _obtener(uow, usuario_id, incluir_baja=True)
        if usuario.deleted_at is None:
            raise ConflictError("El usuario ya está activo", code="ALREADY_ACTIVE")
        uow.usuarios.restore(usuario)
        return to_read(usuario, uow.usuarios.get_roles(usuario_id))
