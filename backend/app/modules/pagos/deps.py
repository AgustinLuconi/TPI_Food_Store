from app.modules.pedidos.uow import PedidosUnitOfWork


def get_pagos_uow() -> PedidosUnitOfWork:
    """Registrar un pago cambia el estado del pedido en la misma transacción: usa el UoW de pedidos."""
    return PedidosUnitOfWork()
