from sqlmodel import Session

from app.core.uow import UnitOfWork
from app.modules.categorias.repository import CategoriaRepository
from app.modules.inventario.repository import MovimientoIngredienteRepository, MovimientoStockRepository
from app.modules.productos.repository import IngredienteRepository, ProductoRepository, RecetaRepository


class ProductosUnitOfWork(UnitOfWork):
    productos: ProductoRepository
    ingredientes: IngredienteRepository
    recetas: RecetaRepository
    categorias: CategoriaRepository
    # Solo lectura: el stock se muestra en el catálogo para gestión, pero se mueve desde el módulo inventario.
    mov_productos: MovimientoStockRepository
    mov_ingredientes: MovimientoIngredienteRepository

    def _init_repositories(self, session: Session) -> None:
        self.productos = ProductoRepository(session)
        self.ingredientes = IngredienteRepository(session)
        self.recetas = RecetaRepository(session)
        self.categorias = CategoriaRepository(session)
        self.mov_productos = MovimientoStockRepository(session)
        self.mov_ingredientes = MovimientoIngredienteRepository(session)
