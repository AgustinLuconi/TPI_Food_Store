"""Repositorios base. Acceso a datos sin lógica de negocio y sin `commit()` (lo hace el UoW)."""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import func
from sqlmodel import Session, SQLModel, select

from app.core.db_types import utcnow

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    model: type[T]

    def __init__(self, session: Session):
        self.session = session

    @property
    def _soft(self) -> bool:
        return hasattr(self.model, "deleted_at")

    def _scoped(self, stmt: Any, include_deleted: bool) -> Any:
        if self._soft and not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return stmt

    def get_by_id(self, entity_id: Any, *, include_deleted: bool = False) -> T | None:
        obj = self.session.get(self.model, entity_id)
        if obj is None:
            return None
        if self._soft and not include_deleted and obj.deleted_at is not None:  # type: ignore[attr-defined]
            return None
        return obj

    def list(
        self,
        *filters: Any,
        page: int = 1,
        size: int = 20,
        order_by: Any = None,
        include_deleted: bool = False,
    ) -> tuple[Sequence[T], int]:
        """Devuelve (items de la página, total sin paginar)."""
        total = self.count(*filters, include_deleted=include_deleted)
        stmt = self._scoped(select(self.model).where(*filters), include_deleted)
        stmt = stmt.order_by(order_by if order_by is not None else self.model.id)  # type: ignore[attr-defined]
        items = self.session.exec(stmt.offset((page - 1) * size).limit(size)).all()
        return items, total

    def count(self, *filters: Any, include_deleted: bool = False) -> int:
        stmt = self._scoped(select(func.count()).select_from(self.model).where(*filters), include_deleted)
        return self.session.exec(stmt).one()

    def create(self, obj: T) -> T:
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)
        return obj

    def update(self, obj: T, data: dict[str, Any]) -> T:
        for key, value in data.items():
            setattr(obj, key, value)
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)
        return obj

    def soft_delete(self, obj: T) -> T:
        if not self._soft:
            raise TypeError(f"{self.model.__name__} no tiene baja lógica")
        obj.deleted_at = utcnow()  # type: ignore[attr-defined]
        self.session.add(obj)
        self.session.flush()
        return obj

    def restore(self, obj: T) -> T:
        """Reactivar limpia deleted_at (sección 11.5)."""
        if not self._soft:
            raise TypeError(f"{self.model.__name__} no tiene baja lógica")
        obj.deleted_at = None  # type: ignore[attr-defined]
        self.session.add(obj)
        self.session.flush()
        return obj

    def hard_delete(self, obj: T) -> None:
        """Solo para entidades SIN baja lógica (RN-16)."""
        if self._soft:
            raise TypeError(f"{self.model.__name__} solo admite baja lógica")
        self.session.delete(obj)
        self.session.flush()


class AppendOnlyRepository(Generic[T]):
    """Solo `create` y lecturas: nunca UPDATE ni DELETE (RN-03, RN-06)."""

    model: type[T]

    def __init__(self, session: Session):
        self.session = session

    def create(self, obj: T) -> T:
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)
        return obj

    def get_by_id(self, entity_id: Any) -> T | None:
        return self.session.get(self.model, entity_id)

    def list(self, *filters: Any, order_by: Any = None) -> Sequence[T]:
        stmt = select(self.model).where(*filters)
        stmt = stmt.order_by(order_by if order_by is not None else self.model.id)  # type: ignore[attr-defined]
        return self.session.exec(stmt).all()
