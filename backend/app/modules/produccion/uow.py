from sqlmodel import Session

from app.modules.inventario.uow import InventarioUnitOfWork
from app.modules.produccion.repository import OrdenRepository
from app.modules.productos.repository import RecetaRepository


class ProduccionUnitOfWork(InventarioUnitOfWork):
    """El inventario (ledgers, lotes) más las órdenes y las recetas: producir toca todo en una transacción."""

    ordenes: OrdenRepository
    recetas: RecetaRepository

    def _init_repositories(self, session: Session) -> None:
        super()._init_repositories(session)
        self.ordenes = OrdenRepository(session)
        self.recetas = RecetaRepository(session)
