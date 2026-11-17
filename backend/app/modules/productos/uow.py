from sqlmodel import Session

from app.core.uow import UnitOfWork
from app.modules.categorias.repository import CategoriaRepository
from app.modules.productos.repository import IngredienteRepository, ProductoRepository, RecetaRepository


class ProductosUnitOfWork(UnitOfWork):
    productos: ProductoRepository
    ingredientes: IngredienteRepository
    recetas: RecetaRepository
    categorias: CategoriaRepository

    def _init_repositories(self, session: Session) -> None:
        self.productos = ProductoRepository(session)
        self.ingredientes = IngredienteRepository(session)
        self.recetas = RecetaRepository(session)
        self.categorias = CategoriaRepository(session)
