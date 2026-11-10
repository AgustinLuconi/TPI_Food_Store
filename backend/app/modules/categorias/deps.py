from app.modules.categorias.uow import CategoriasUnitOfWork


def get_categorias_uow() -> CategoriasUnitOfWork:
    return CategoriasUnitOfWork()
