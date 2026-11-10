from sqlmodel import Session

from app.core.uow import UnitOfWork
from app.modules.categorias.repository import CategoriaRepository


class CategoriasUnitOfWork(UnitOfWork):
    categorias: CategoriaRepository

    def _init_repositories(self, session: Session) -> None:
        self.categorias = CategoriaRepository(session)
