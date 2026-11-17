"""Acceso a datos de las órdenes de producción. Sin lógica de negocio."""

from collections.abc import Sequence

from sqlmodel import select

from app.core.repository import BaseRepository
from app.modules.produccion.models import EstadoOrden, OrdenProduccion


class OrdenRepository(BaseRepository[OrdenProduccion]):
    model = OrdenProduccion

    def get_for_update(self, orden_id: int) -> OrdenProduccion | None:
        """Bloquea la fila: dos personas no pueden completar (ni cancelar) la misma orden a la vez."""
        stmt = select(OrdenProduccion).where(OrdenProduccion.id == orden_id).with_for_update()
        return self.session.exec(stmt).first()

    def search(self, *, estado: EstadoOrden | None, page: int, size: int) -> tuple[Sequence[OrdenProduccion], int]:
        filtros = [OrdenProduccion.estado == estado] if estado else []
        return self.list(
            *filtros,
            page=page,
            size=size,
            order_by=[OrdenProduccion.id.desc()],  # type: ignore[attr-defined]
        )
