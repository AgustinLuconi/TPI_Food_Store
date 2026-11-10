from app.modules.usuarios.uow import UsuariosUnitOfWork


def get_usuarios_uow() -> UsuariosUnitOfWork:
    return UsuariosUnitOfWork()
