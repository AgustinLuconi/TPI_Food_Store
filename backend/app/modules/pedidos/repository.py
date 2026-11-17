"""Acceso a datos de pedidos, líneas e historial. Sin lógica de negocio."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func
from sqlmodel import select

from app.core.repository import AppendOnlyRepository, BaseRepository
from app.modules.pagos.models import FormaPago
from app.modules.pedidos.models import DetallePedido, DetallePedidoExclusion, HistorialEstadoPedido, Pedido
from app.modules.productos.models import Ingrediente


class PedidoRepository(BaseRepository[Pedido]):
    model = Pedido

    def get_for_update(self, pedido_id: int) -> Pedido | None:
        """Bloquea la fila: dos cambios de estado (o dos pagos) del mismo pedido no pueden cruzarse."""
        return self.session.exec(select(Pedido).where(Pedido.id == pedido_id).with_for_update()).first()

    def get_by_referencia(self, referencia: str) -> Pedido | None:
        return self.session.exec(select(Pedido).where(Pedido.external_reference == referencia)).first()

    def bloquear_clave(self, clave: str) -> None:
        """Serializa dos requests simultáneos con la misma Idempotency-Key: el segundo espera a que el primero
        confirme y entonces encuentra el pedido ya creado, en lugar de chocar con el UNIQUE."""
        self.session.exec(select(func.pg_advisory_xact_lock(func.hashtext(clave))))  # type: ignore[call-overload]

    def search(
        self,
        *,
        usuario_id: int | None,
        estado: str | None,
        desde: datetime | None,
        hasta_exclusivo: datetime | None,
        page: int,
        size: int,
    ) -> tuple[Sequence[Pedido], int]:
        filtros = []
        if usuario_id is not None:
            filtros.append(Pedido.usuario_id == usuario_id)
        if estado is not None:
            filtros.append(Pedido.estado_codigo == estado)
        if desde is not None:
            filtros.append(Pedido.created_at >= desde)  # type: ignore[arg-type]
        if hasta_exclusivo is not None:
            filtros.append(Pedido.created_at < hasta_exclusivo)  # type: ignore[arg-type]
        return self.list(*filtros, page=page, size=size, order_by=[Pedido.created_at.desc(), Pedido.id.desc()])  # type: ignore[attr-defined]


class DetalleRepository(BaseRepository[DetallePedido]):
    model = DetallePedido

    def de_pedido(self, pedido_id: int) -> Sequence[DetallePedido]:
        stmt = select(DetallePedido).where(DetallePedido.pedido_id == pedido_id).order_by(DetallePedido.id)  # type: ignore[arg-type]
        return self.session.exec(stmt).all()

    def agregar_exclusion(self, detalle_id: int, ingrediente_id: int) -> None:
        self.session.add(DetallePedidoExclusion(detalle_pedido_id=detalle_id, ingrediente_id=ingrediente_id))
        self.session.flush()

    def exclusiones_de(self, detalle_ids: Sequence[int]) -> dict[int, list[tuple[int, str]]]:
        """(ingrediente_id, nombre) de lo que se quitó en cada línea."""
        resultado: dict[int, list[tuple[int, str]]] = {d: [] for d in detalle_ids}
        if not detalle_ids:
            return resultado
        stmt = (
            select(DetallePedidoExclusion.detalle_pedido_id, Ingrediente.id, Ingrediente.nombre)
            .join(Ingrediente, Ingrediente.id == DetallePedidoExclusion.ingrediente_id)  # type: ignore[arg-type]
            .where(DetallePedidoExclusion.detalle_pedido_id.in_(detalle_ids))  # type: ignore[attr-defined]
            .order_by(Ingrediente.nombre)
        )
        for detalle_id, ing_id, nombre in self.session.exec(stmt).all():
            resultado[detalle_id].append((ing_id, nombre))
        return resultado


class HistorialRepository(AppendOnlyRepository[HistorialEstadoPedido]):
    """Ledger de estados: solo se agrega (RN-02, RN-03)."""

    model = HistorialEstadoPedido

    def de_pedido(self, pedido_id: int) -> Sequence[HistorialEstadoPedido]:
        stmt = (
            select(HistorialEstadoPedido)
            .where(HistorialEstadoPedido.pedido_id == pedido_id)
            .order_by(HistorialEstadoPedido.created_at, HistorialEstadoPedido.id)  # type: ignore[arg-type]
        )
        return self.session.exec(stmt).all()


class FormaPagoRepository(BaseRepository[FormaPago]):
    model = FormaPago
