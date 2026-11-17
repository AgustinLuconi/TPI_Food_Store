from app.modules.productos.uow import ProductosUnitOfWork


def get_productos_uow() -> ProductosUnitOfWork:
    return ProductosUnitOfWork()
