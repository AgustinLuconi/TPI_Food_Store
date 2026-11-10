from app.modules.auth.uow import AuthUnitOfWork


def get_auth_uow() -> AuthUnitOfWork:
    return AuthUnitOfWork()
