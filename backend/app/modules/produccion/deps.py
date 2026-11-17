from app.modules.produccion.uow import ProduccionUnitOfWork


def get_produccion_uow() -> ProduccionUnitOfWork:
    return ProduccionUnitOfWork()
