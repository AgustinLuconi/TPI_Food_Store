from app.modules.direcciones.uow import DireccionesUnitOfWork


def get_direcciones_uow() -> DireccionesUnitOfWork:
    return DireccionesUnitOfWork()
