from app.modules.metricas.uow import MetricasUnitOfWork


def get_metricas_uow() -> MetricasUnitOfWork:
    return MetricasUnitOfWork()
