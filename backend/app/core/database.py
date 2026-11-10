"""Engine y fábrica de sesiones."""

from collections.abc import Callable
from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from app.core.config import get_settings

SessionFactory = Callable[[], Session]


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().DATABASE_URL, pool_pre_ping=True)


def default_session_factory() -> Session:
    # expire_on_commit=False: el Service puede devolver entidades después del commit del UoW
    # y el Router serializarlas sin volver a consultar la base.
    return Session(get_engine(), expire_on_commit=False)
