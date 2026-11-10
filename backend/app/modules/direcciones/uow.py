from sqlmodel import Session

from app.core.uow import UnitOfWork
from app.modules.direcciones.repository import DireccionRepository


class DireccionesUnitOfWork(UnitOfWork):
    direcciones: DireccionRepository

    def _init_repositories(self, session: Session) -> None:
        self.direcciones = DireccionRepository(session)
