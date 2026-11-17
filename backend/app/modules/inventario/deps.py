from app.modules.inventario.uow import InventarioUnitOfWork


def get_inventario_uow() -> InventarioUnitOfWork:
    return InventarioUnitOfWork()
