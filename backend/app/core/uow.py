"""Unit of Work base: abre la sesión, expone los repositorios y hace commit o rollback al salir.

    with uow:                # commit al salir sin errores; rollback ante cualquier excepción
        uow.usuarios.create(...)

Ningún service llama a `session.commit()`. En los tests se inyecta un `session_factory` conectado
a la base de prueba (ver tests/conftest.py).
"""

from types import TracebackType
from typing import Self

from sqlmodel import Session

from app.core.database import SessionFactory, default_session_factory


class UnitOfWork:
    session: Session

    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or default_session_factory
        self._session: Session | None = None

    def __enter__(self) -> Self:
        self._session = self._session_factory()
        self.session = self._session
        self._init_repositories(self._session)
        return self

    def _init_repositories(self, session: Session) -> None:
        """Las subclases crean aquí los repositorios de su módulo."""

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        try:
            if exc_type is None:
                self._session.commit()
            else:
                self._session.rollback()
        finally:
            self._session.close()
            self._session = None
