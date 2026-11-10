"""Base PostgreSQL de prueba + UoW inyectado.

- La base de prueba se crea (si falta) y se migra con Alembic: así los tests también validan la migración.
- Cada test corre dentro de una transacción que se revierte al terminar (los commits de los UoW
  son SAVEPOINTs), por lo que los tests no se contaminan entre sí.
- El UoW de prueba se inyecta con `app.dependency_overrides`, como prevé la arquitectura.
"""

import os
import secrets
from collections.abc import Callable, Iterator
from pathlib import Path

import psycopg
import pytest

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://foodstore:foodstore@localhost:5434/foodstore_test"
)
# Debe fijarse ANTES de importar la app: get_settings() se cachea.
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ.setdefault("SECRET_KEY", secrets.token_urlsafe(48))
os.environ["ENVIRONMENT"] = "development"

from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlmodel import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.core.uow import UnitOfWork  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.auth.deps import get_auth_uow  # noqa: E402
from app.modules.auth.uow import AuthUnitOfWork  # noqa: E402
from app.modules.categorias.deps import get_categorias_uow  # noqa: E402
from app.modules.categorias.uow import CategoriasUnitOfWork  # noqa: E402
from app.modules.direcciones.deps import get_direcciones_uow  # noqa: E402
from app.modules.direcciones.uow import DireccionesUnitOfWork  # noqa: E402
from app.modules.usuarios.deps import get_usuarios_uow  # noqa: E402
from app.modules.usuarios.uow import UsuariosUnitOfWork  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Cada get_*_uow de un módulo se registra aquí junto con su clase de UoW.
UOW_DEPENDENCIES: dict[Callable, type[UnitOfWork]] = {
    get_auth_uow: AuthUnitOfWork,
    get_usuarios_uow: UsuariosUnitOfWork,
    get_direcciones_uow: DireccionesUnitOfWork,
    get_categorias_uow: CategoriasUnitOfWork,
}


def _crear_base_si_falta() -> None:
    nombre = TEST_DB_URL.rsplit("/", 1)[1]
    admin_url = TEST_DB_URL.replace("+psycopg", "").rsplit("/", 1)[0] + "/postgres"
    with psycopg.connect(admin_url, autocommit=True) as conn:
        existe = conn.execute("select 1 from pg_database where datname = %s", (nombre,)).fetchone()
        if not existe:
            conn.execute(f'create database "{nombre}"')


@pytest.fixture(scope="session")
def engine():
    _crear_base_si_falta()
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.downgrade(cfg, "base")  # parte siempre de una base limpia
    command.upgrade(cfg, "head")
    eng = create_engine(TEST_DB_URL)
    from app.db.seed import seed

    seed(UnitOfWork(lambda: Session(eng, expire_on_commit=False)))  # datos base permanentes de la sesión
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine) -> Iterator[Callable[[], Session]]:
    connection = engine.connect()
    transaction = connection.begin()

    def factory() -> Session:
        return Session(connection, join_transaction_mode="create_savepoint", expire_on_commit=False)

    yield factory
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(session_factory) -> Iterator[TestClient]:
    for dependency, uow_class in UOW_DEPENDENCIES.items():
        app.dependency_overrides[dependency] = lambda uow_class=uow_class: uow_class(session_factory)
    limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    limiter.reset()


@pytest.fixture
def uow_factory(session_factory) -> Callable[[type[UnitOfWork]], UnitOfWork]:
    """Crea un UoW de cualquier módulo conectado a la base de prueba (para preparar datos)."""
    return lambda uow_class: uow_class(session_factory)
