"""Consultas de agregación de las métricas (sección 6.8): todo se calcula en la base con sum, count y group by,
nunca en el cliente. Sin lógica de negocio."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, case, cast, func, null
from sqlmodel import Session, select

from app.modules.inventario.repository import aporte
from app.modules.inventario.stock import SIGNO_DISPONIBLE, SIGNO_REAL
from app.modules.pagos.models import Pago
from app.modules.pedidos.models import DetallePedido, Pedido
from app.modules.productos.models import (
    Ingrediente,
    MovimientoIngrediente,
    MovimientoStock,
    Producto,
    TipoMovimiento,
)

CERO = Decimal(0)

# Una VENTA es un pedido con pago aprobado que no se canceló después: un pedido cancelado no es ingreso.
_ES_VENTA = (Pago.mp_status == "approved", Pedido.estado_codigo != "CANCELADO")


class MetricasRepository:
    def __init__(self, session: Session):
        self.session = session

    def ventas_en(self, desde: datetime, hasta: datetime) -> tuple[Decimal, int]:
        """(suma de Pedido.total, cantidad) de las ventas cuyo pago se aprobó en [desde, hasta)."""
        stmt = (
            select(func.coalesce(func.sum(Pedido.total), 0), func.count(Pedido.id))  # type: ignore[arg-type]
            .join(Pago, Pago.pedido_id == Pedido.id)  # type: ignore[arg-type]
            .where(*_ES_VENTA, Pago.created_at >= desde, Pago.created_at < hasta)  # type: ignore[arg-type]
        )
        total, cantidad = self.session.exec(stmt).one()
        return total, cantidad

    def pedidos_creados_en(self, desde: datetime, hasta: datetime) -> int:
        stmt = select(func.count()).select_from(Pedido).where(Pedido.created_at >= desde, Pedido.created_at < hasta)  # type: ignore[arg-type]
        return self.session.exec(stmt).one()

    def pedidos_por_estado(self) -> dict[str, int]:
        stmt = select(Pedido.estado_codigo, func.count()).group_by(Pedido.estado_codigo)
        return {estado: n for estado, n in self.session.exec(stmt).all()}

    def pagos_por_estado(self) -> dict[str, int]:
        stmt = select(Pago.mp_status, func.count()).group_by(Pago.mp_status)
        return {estado: n for estado, n in self.session.exec(stmt).all()}

    def serie_de_ventas(self, desde: datetime, hasta: datetime, zona: str) -> dict[date, tuple[Decimal, int]]:
        """Ventas por día calendario DEL LOCAL (se convierte el instante a la zona antes de truncar a fecha)."""
        dia = cast(func.timezone(zona, Pago.created_at), Date)
        stmt = (
            select(dia, func.sum(Pedido.total), func.count(Pedido.id))  # type: ignore[arg-type]
            .join(Pago, Pago.pedido_id == Pedido.id)  # type: ignore[arg-type]
            .where(*_ES_VENTA, Pago.created_at >= desde, Pago.created_at < hasta)  # type: ignore[arg-type]
            .group_by(dia)
        )
        return {d: (total, n) for d, total, n in self.session.exec(stmt).all()}

    def top_productos(self, limite: int) -> list[tuple[int, str, int, Decimal]]:
        """(producto_id, nombre, unidades, ingresos) de lo más vendido: suma de DetallePedido.cantidad."""
        unidades = func.sum(DetallePedido.cantidad)
        stmt = (
            select(
                Producto.id,
                Producto.nombre,
                unidades,
                func.sum(DetallePedido.precio_snapshot * DetallePedido.cantidad),
            )
            .join(DetallePedido, DetallePedido.producto_id == Producto.id)  # type: ignore[arg-type]
            .join(Pedido, Pedido.id == DetallePedido.pedido_id)  # type: ignore[arg-type]
            .join(Pago, Pago.pedido_id == Pedido.id)  # type: ignore[arg-type]
            .where(*_ES_VENTA)
            .group_by(Producto.id, Producto.nombre)
            .order_by(unidades.desc(), Producto.nombre)
            .limit(limite)
        )
        return list(self.session.exec(stmt).all())  # type: ignore[arg-type]

    def _stock_bajo(
        self, dueno: Any, movimiento: Any, columna_dueno: Any, unidad: Any = None
    ) -> list[tuple[int, str, int, Decimal, Decimal, str | None]]:
        """Los activos con stock_disponible <= stock_minimo, del más comprometido al menos.

        Devuelve (id, nombre, mínimo, real, disponible, unidad); la unidad es None para lo que no la tiene."""
        real = func.coalesce(func.sum(aporte(movimiento, SIGNO_REAL)), 0)
        disponible = func.coalesce(func.sum(aporte(movimiento, SIGNO_DISPONIBLE)), 0)
        unidad_col = unidad if unidad is not None else null()
        stmt = (
            select(dueno.id, dueno.nombre, dueno.stock_minimo, real, disponible, unidad_col)
            .select_from(dueno)
            .outerjoin(movimiento, columna_dueno == dueno.id)
            .where(dueno.deleted_at.is_(None))
            .group_by(dueno.id, dueno.nombre, dueno.stock_minimo, *([unidad] if unidad is not None else []))
            .having(disponible <= dueno.stock_minimo)
            .order_by(disponible - dueno.stock_minimo, dueno.nombre)
        )
        return list(self.session.exec(stmt).all())  # type: ignore[arg-type]

    def productos_bajo_minimo(self) -> list[tuple[int, str, int, Decimal, Decimal, str | None]]:
        return self._stock_bajo(Producto, MovimientoStock, MovimientoStock.producto_id)

    def ingredientes_bajo_minimo(self) -> list[tuple[int, str, int, Decimal, Decimal, str | None]]:
        return self._stock_bajo(
            Ingrediente, MovimientoIngrediente, MovimientoIngrediente.ingrediente_id, Ingrediente.unidad_medida
        )

    def mermas_de_insumos(self, desde: datetime, hasta: datetime) -> list[tuple[str, int, str, str, Decimal, int]]:
        """(motivo, ingrediente_id, nombre, unidad, cantidad, movimientos) de las MERMA de insumos del período.

        Una fila por motivo e insumo; el servicio las agrupa por motivo y unidad. Cuentan también los insumos dados
        de baja: la pérdida ocurrió igual."""
        total = func.sum(MovimientoIngrediente.cantidad)
        motivo = case((MovimientoIngrediente.motivo.is_(None), "SIN_MOTIVO"), else_=MovimientoIngrediente.motivo)
        stmt = (
            select(motivo, Ingrediente.id, Ingrediente.nombre, Ingrediente.unidad_medida, total, func.count())
            .select_from(MovimientoIngrediente)
            .join(Ingrediente, Ingrediente.id == MovimientoIngrediente.ingrediente_id)  # type: ignore[arg-type]
            .where(
                MovimientoIngrediente.tipo_movimiento == TipoMovimiento.MERMA,
                MovimientoIngrediente.fecha_registro >= desde,
                MovimientoIngrediente.fecha_registro < hasta,
            )
            .group_by(motivo, Ingrediente.id, Ingrediente.nombre, Ingrediente.unidad_medida)
        )
        return list(self.session.exec(stmt).all())  # type: ignore[arg-type]

    def mermas(self, modelo: Any, desde: datetime, hasta: datetime) -> list[tuple[str, Decimal, int]]:
        """(motivo, cantidad total, cantidad de movimientos) de las MERMA del período, la mayor primero."""
        total = func.sum(modelo.cantidad)
        motivo = case((modelo.motivo.is_(None), "SIN_MOTIVO"), else_=modelo.motivo)
        stmt = (
            select(motivo, total, func.count())
            .where(
                modelo.tipo_movimiento == TipoMovimiento.MERMA,
                modelo.fecha_registro >= desde,
                modelo.fecha_registro < hasta,
            )
            .group_by(motivo)
            .order_by(total.desc(), motivo)
        )
        return list(self.session.exec(stmt).all())  # type: ignore[arg-type]
