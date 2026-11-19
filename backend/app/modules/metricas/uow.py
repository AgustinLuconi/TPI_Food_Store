from sqlmodel import Session

from app.modules.config.uow import ConfigUnitOfWork
from app.modules.inventario.uow import InventarioUnitOfWork
from app.modules.metricas.repository import MetricasRepository


class MetricasUnitOfWork(InventarioUnitOfWork, ConfigUnitOfWork):
    """Solo lectura: las consultas de agregación, el local (zona horaria) y los lotes por vencer del inventario."""

    metricas: MetricasRepository

    def _init_repositories(self, session: Session) -> None:
        super()._init_repositories(session)
        self.metricas = MetricasRepository(session)
