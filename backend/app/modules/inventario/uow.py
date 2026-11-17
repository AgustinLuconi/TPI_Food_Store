from sqlmodel import Session

from app.core.uow import UnitOfWork
from app.modules.inventario.repository import (
    LoteRepository,
    MovimientoIngredienteRepository,
    MovimientoStockRepository,
)
from app.modules.productos.repository import IngredienteRepository, ProductoRepository


class InventarioUnitOfWork(UnitOfWork):
    productos: ProductoRepository
    ingredientes: IngredienteRepository
    lotes: LoteRepository
    mov_productos: MovimientoStockRepository
    mov_ingredientes: MovimientoIngredienteRepository

    def _init_repositories(self, session: Session) -> None:
        self.productos = ProductoRepository(session)
        self.ingredientes = IngredienteRepository(session)
        self.lotes = LoteRepository(session)
        self.mov_productos = MovimientoStockRepository(session)
        self.mov_ingredientes = MovimientoIngredienteRepository(session)
