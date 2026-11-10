from sqlmodel import Session

from app.core.uow import UnitOfWork
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.usuarios.repository import RolRepository, UsuarioRepository


class AuthUnitOfWork(UnitOfWork):
    usuarios: UsuarioRepository
    roles: RolRepository
    refresh_tokens: RefreshTokenRepository

    def _init_repositories(self, session: Session) -> None:
        self.usuarios = UsuarioRepository(session)
        self.roles = RolRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
