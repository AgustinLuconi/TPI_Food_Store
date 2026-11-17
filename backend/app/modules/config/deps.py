from app.modules.config.uow import ConfigUnitOfWork


def get_config_uow() -> ConfigUnitOfWork:
    return ConfigUnitOfWork()
