from app.modules.pedidos.uow import PedidosUnitOfWork


def get_pedidos_uow() -> PedidosUnitOfWork:
    return PedidosUnitOfWork()
