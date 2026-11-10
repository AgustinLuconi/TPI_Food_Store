"""Acceso a datos de usuarios y roles. Sin lógica de negocio."""

from collections.abc import Sequence
from typing import Literal

from sqlalchemy import delete, func, or_
from sqlmodel import select

from app.core.repository import BaseRepository
from app.modules.usuarios.models import Rol, Usuario, UsuarioRol

Estado = Literal["activos", "inactivos", "todos"]


class RolRepository(BaseRepository[Rol]):
    model = Rol

    def get_by_codigo(self, codigo: str) -> Rol | None:
        return self.session.get(Rol, codigo)

    def codigos(self) -> set[str]:
        return set(self.session.exec(select(Rol.codigo)).all())


class UsuarioRepository(BaseRepository[Usuario]):
    model = Usuario

    def get_by_email(self, email: str) -> Usuario | None:
        """Incluye usuarios dados de baja: el email sigue siendo único tras la baja lógica."""
        return self.session.exec(select(Usuario).where(func.lower(Usuario.email) == email.lower())).first()

    def get_roles(self, usuario_id: int) -> list[str]:
        stmt = select(UsuarioRol.rol_codigo).where(UsuarioRol.usuario_id == usuario_id).order_by(UsuarioRol.rol_codigo)
        return list(self.session.exec(stmt).all())

    def get_roles_map(self, usuario_ids: Sequence[int]) -> dict[int, list[str]]:
        """Roles de varios usuarios en una sola consulta (evita N+1 en los listados)."""
        result: dict[int, list[str]] = {uid: [] for uid in usuario_ids}
        if not usuario_ids:
            return result
        stmt = (
            select(UsuarioRol.usuario_id, UsuarioRol.rol_codigo)
            .where(UsuarioRol.usuario_id.in_(usuario_ids))  # type: ignore[attr-defined]
            .order_by(UsuarioRol.rol_codigo)
        )
        for uid, codigo in self.session.exec(stmt).all():
            result[uid].append(codigo)
        return result

    def replace_roles(self, usuario_id: int, roles: Sequence[str], asignado_por_id: int | None) -> None:
        """Reemplaza los roles y registra quién los asignó (auditoría)."""
        self.session.exec(delete(UsuarioRol).where(UsuarioRol.usuario_id == usuario_id))  # type: ignore[call-overload]
        for codigo in dict.fromkeys(roles):
            self.session.add(UsuarioRol(usuario_id=usuario_id, rol_codigo=codigo, asignado_por_id=asignado_por_id))
        self.session.flush()

    def count_activos_con_rol(self, rol_codigo: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Usuario)
            .join(UsuarioRol, UsuarioRol.usuario_id == Usuario.id)  # type: ignore[arg-type]
            .where(UsuarioRol.rol_codigo == rol_codigo, Usuario.deleted_at.is_(None), Usuario.disabled.is_(False))  # type: ignore[attr-defined]
        )
        return self.session.exec(stmt).one()

    def search(
        self,
        *,
        search: str | None,
        rol: str | None,
        estado: Estado,
        page: int,
        size: int,
    ) -> tuple[Sequence[Usuario], int]:
        filters = []
        if search:
            like = f"%{search.strip()}%"
            filters.append(
                or_(Usuario.nombre.ilike(like), Usuario.apellido.ilike(like), Usuario.email.ilike(like))  # type: ignore[attr-defined]
            )
        if rol:
            filters.append(
                Usuario.id.in_(select(UsuarioRol.usuario_id).where(UsuarioRol.rol_codigo == rol))  # type: ignore[attr-defined]
            )
        if estado == "activos":
            filters.append(Usuario.deleted_at.is_(None))  # type: ignore[attr-defined]
        elif estado == "inactivos":
            filters.append(Usuario.deleted_at.is_not(None))  # type: ignore[attr-defined]
        # Los filtros de estado ya se aplicaron: se consulta incluyendo dados de baja.
        return self.list(*filters, page=page, size=size, order_by=Usuario.apellido, include_deleted=True)
