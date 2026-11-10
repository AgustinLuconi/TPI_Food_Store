from collections.abc import Sequence

from sqlalchemy import update
from sqlmodel import select

from app.core.repository import BaseRepository
from app.modules.direcciones.models import DireccionEntrega


class DireccionRepository(BaseRepository[DireccionEntrega]):
    model = DireccionEntrega

    def list_by_usuario(self, usuario_id: int) -> Sequence[DireccionEntrega]:
        stmt = (
            select(DireccionEntrega)
            .where(DireccionEntrega.usuario_id == usuario_id, DireccionEntrega.deleted_at.is_(None))  # type: ignore[attr-defined]
            .order_by(DireccionEntrega.es_principal.desc(), DireccionEntrega.id)  # type: ignore[attr-defined]
        )
        return self.session.exec(stmt).all()

    def get_owned(self, usuario_id: int, direccion_id: int) -> DireccionEntrega | None:
        """Devuelve la dirección solo si existe, está activa y es del usuario."""
        direccion = self.get_by_id(direccion_id)
        if direccion is None or direccion.usuario_id != usuario_id:
            return None
        return direccion

    def count_activas(self, usuario_id: int) -> int:
        return self.count(DireccionEntrega.usuario_id == usuario_id)

    def unset_principal(self, usuario_id: int, *, except_id: int | None = None) -> None:
        """Quita la marca de principal a las demás direcciones activas (RN-17: índice único parcial)."""
        stmt = (
            update(DireccionEntrega)
            .where(
                DireccionEntrega.usuario_id == usuario_id,
                DireccionEntrega.es_principal.is_(True),  # type: ignore[attr-defined]
                DireccionEntrega.deleted_at.is_(None),  # type: ignore[attr-defined]
            )
            .values(es_principal=False)
        )
        if except_id is not None:
            stmt = stmt.where(DireccionEntrega.id != except_id)
        self.session.exec(stmt)  # type: ignore[call-overload]
        self.session.flush()
