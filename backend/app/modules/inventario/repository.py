"""Acceso a datos del inventario: ledgers append-only y lotes. Sin lógica de negocio.

El stock nunca se guarda: se obtiene sumando los movimientos con el signo de cada tipo (sección 8.2).
"""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar

from sqlalchemy import case, func
from sqlmodel import select

from app.core.repository import AppendOnlyRepository, BaseRepository
from app.modules.inventario.stock import SIGNO_DISPONIBLE, SIGNO_REAL, SIGNO_RESERVADO
from app.modules.productos.models import (
    Ingrediente,
    Lote,
    MovimientoIngrediente,
    MovimientoStock,
    Producto,
    TipoMovimiento,
)

M = TypeVar("M", MovimientoStock, MovimientoIngrediente)
CERO = Decimal(0)


def _aporte(modelo: Any, signos: dict[str, int]) -> Any:
    """cantidad × signo según el tipo de movimiento."""
    signo = case(*[(modelo.tipo_movimiento == tipo, s) for tipo, s in signos.items()], else_=0)
    return modelo.cantidad * signo


class _Ledger(AppendOnlyRepository[M], Generic[M]):
    """Lo común a ambos ledgers: stock derivado, listado paginado y bloqueo del dueño del stock."""

    owner_model: Any  # Producto o Ingrediente
    owner_attr: str  # "producto_id" / "ingrediente_id"

    @property
    def owner_column(self) -> Any:
        # No puede ser atributo de clase: un InstrumentedAttribute falla al leerse desde una instancia ajena al ORM.
        return getattr(self.model, self.owner_attr)

    def bloquear(self, owner_id: int) -> None:
        """Serializa los movimientos concurrentes del mismo producto/insumo (evita sobreventa)."""
        self.session.exec(select(self.owner_model.id).where(self.owner_model.id == owner_id).with_for_update())  # type: ignore[call-overload]

    def stock(self, owner_id: int, signos: dict[str, int], *, lote_id: int | None = None) -> Decimal:
        stmt = select(func.coalesce(func.sum(_aporte(self.model, signos)), 0)).where(self.owner_column == owner_id)
        if lote_id is not None:
            stmt = stmt.where(self.model.lote_id == lote_id)  # type: ignore[attr-defined]
        return self.session.exec(stmt).one()

    def stock_real(self, owner_id: int) -> Decimal:
        return self.stock(owner_id, SIGNO_REAL)

    def stock_disponible(self, owner_id: int) -> Decimal:
        return self.stock(owner_id, SIGNO_DISPONIBLE)

    def stocks(self, owner_ids: Sequence[int]) -> dict[int, tuple[Decimal, Decimal]]:
        """(stock_real, stock_disponible) de varios en una sola consulta."""
        resultado = {oid: (CERO, CERO) for oid in owner_ids}
        if not owner_ids:
            return resultado
        stmt = (
            select(
                self.owner_column,
                func.coalesce(func.sum(_aporte(self.model, SIGNO_REAL)), 0),
                func.coalesce(func.sum(_aporte(self.model, SIGNO_DISPONIBLE)), 0),
            )
            .where(self.owner_column.in_(owner_ids))
            .group_by(self.owner_column)
        )
        for oid, real, disponible in self.session.exec(stmt).all():
            resultado[oid] = (real, disponible)
        return resultado

    def listar(self, owner_id: int, *, tipo: TipoMovimiento | None, page: int, size: int) -> tuple[Sequence[M], int]:
        filtros = [self.owner_column == owner_id]
        if tipo is not None:
            filtros.append(self.model.tipo_movimiento == tipo)  # type: ignore[attr-defined]
        total = self.session.exec(select(func.count()).select_from(self.model).where(*filtros)).one()
        stmt = (
            select(self.model)
            .where(*filtros)
            .order_by(self.model.fecha_registro.desc(), self.model.id.desc())  # type: ignore[attr-defined]
            .offset((page - 1) * size)
            .limit(size)
        )
        return self.session.exec(stmt).all(), total


class MovimientoStockRepository(_Ledger[MovimientoStock]):
    model = MovimientoStock
    owner_model = Producto
    owner_attr = "producto_id"

    def stock_por_lote(self, producto_id: int) -> dict[int, tuple[Decimal, Decimal]]:
        """(real, disponible) de cada lote del producto. Lo que no tiene lote no aparece."""
        return self._por_lote(MovimientoStock.producto_id == producto_id)

    def stock_de_lotes(self, lote_ids: Sequence[int]) -> dict[int, tuple[Decimal, Decimal]]:
        if not lote_ids:
            return {}
        return self._por_lote(MovimientoStock.lote_id.in_(lote_ids))  # type: ignore[union-attr]

    def reservado_por_pedido(self, pedido_id: int) -> list[tuple[int, int | None, Decimal]]:
        """(producto_id, lote_id, cantidad) que el pedido todavía tiene reservada, agrupado por lote.

        Sirve para liberar o consumir exactamente los mismos lotes que se reservaron (FEFO al crear)."""
        stmt = (
            select(
                MovimientoStock.producto_id,
                MovimientoStock.lote_id,
                func.coalesce(func.sum(_aporte(MovimientoStock, SIGNO_RESERVADO)), 0),
            )
            .where(MovimientoStock.pedido_id == pedido_id)
            .group_by(MovimientoStock.producto_id, MovimientoStock.lote_id)
            .order_by(MovimientoStock.producto_id, MovimientoStock.lote_id.asc().nulls_last())  # type: ignore[union-attr]
        )
        return [(p, lote, total) for p, lote, total in self.session.exec(stmt).all() if total != 0]

    def _por_lote(self, filtro: Any) -> dict[int, tuple[Decimal, Decimal]]:
        stmt = (
            select(
                MovimientoStock.lote_id,
                func.coalesce(func.sum(_aporte(MovimientoStock, SIGNO_REAL)), 0),
                func.coalesce(func.sum(_aporte(MovimientoStock, SIGNO_DISPONIBLE)), 0),
            )
            .where(filtro, MovimientoStock.lote_id.is_not(None))  # type: ignore[union-attr]
            .group_by(MovimientoStock.lote_id)
        )
        return {lote_id: (real, disp) for lote_id, real, disp in self.session.exec(stmt).all()}


class MovimientoIngredienteRepository(_Ledger[MovimientoIngrediente]):
    model = MovimientoIngrediente
    owner_model = Ingrediente
    owner_attr = "ingrediente_id"

    def por_orden(self, orden_id: int, signos: dict[str, int]) -> dict[int, Decimal]:
        """Cantidad con signo de cada insumo en los movimientos de una orden de producción.

        Con {RESERVA: 1} es lo que la orden planificó; con {RESERVA: 1, LIBERACION_RESERVA: -1}, lo que
        sigue reservado.
        """
        stmt = (
            select(
                MovimientoIngrediente.ingrediente_id, func.coalesce(func.sum(_aporte(MovimientoIngrediente, signos)), 0)
            )
            .where(MovimientoIngrediente.orden_produccion_id == orden_id)
            .group_by(MovimientoIngrediente.ingrediente_id)
        )
        return {ing_id: total for ing_id, total in self.session.exec(stmt).all() if total != 0}


class LoteRepository(BaseRepository[Lote]):
    model = Lote

    def de_producto(self, producto_id: int) -> Sequence[Lote]:
        stmt = (
            select(Lote).where(Lote.producto_id == producto_id).order_by(Lote.fecha_vencimiento, Lote.id)  # type: ignore[arg-type]
        )
        return self.session.exec(stmt).all()

    def por_codigo(self, producto_id: int, codigo_lote: str) -> Lote | None:
        stmt = select(Lote).where(Lote.producto_id == producto_id, func.lower(Lote.codigo_lote) == codigo_lote.lower())
        return self.session.exec(stmt).first()

    def vencen_antes_de(self, limite: datetime) -> Sequence[tuple[Lote, str]]:
        """Lotes con vencimiento hasta `limite` (incluye los ya vencidos) y el nombre de su producto."""
        stmt = (
            select(Lote, Producto.nombre)
            .join(Producto, Producto.id == Lote.producto_id)  # type: ignore[arg-type]
            .where(Lote.fecha_vencimiento <= limite, Producto.deleted_at.is_(None))  # type: ignore[attr-defined]
            .order_by(Lote.fecha_vencimiento, Lote.id)  # type: ignore[arg-type]
        )
        return self.session.exec(stmt).all()
