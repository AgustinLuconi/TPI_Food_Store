from sqlmodel import Session

from app.core.uow import UnitOfWork
from app.modules.usuarios.repository import RolRepository, UsuarioRepository


class UsuariosUnitOfWork(UnitOfWork):
    usuarios: UsuarioRepository
    roles: RolRepository

    def _init_repositories(self, session: Session) -> None:
        self.usuarios = UsuarioRepository(session)
        self.roles = RolRepository(session)
