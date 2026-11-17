from sqlmodel import Session

from app.core.uow import UnitOfWork
from app.modules.config.repository import (
    CoberturaRepository,
    DiaBloqueadoRepository,
    HorarioRepository,
    LocalRepository,
    ZonaRepository,
)


class ConfigUnitOfWork(UnitOfWork):
    local: LocalRepository
    horarios: HorarioRepository
    bloqueos: DiaBloqueadoRepository
    zonas: ZonaRepository
    cobertura: CoberturaRepository

    def _init_repositories(self, session: Session) -> None:
        self.local = LocalRepository(session)
        self.horarios = HorarioRepository(session)
        self.bloqueos = DiaBloqueadoRepository(session)
        self.zonas = ZonaRepository(session)
        self.cobertura = CoberturaRepository(self.zonas)
