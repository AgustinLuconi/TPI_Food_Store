"""Métricas del panel (sección 6.8). Solo lectura: arma las respuestas con lo que agrega la base."""

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from app.core.db_types import utcnow
from app.core.errors import NotFoundError, ValidationError
from app.modules.inventario.service import calcular_lotes_por_vencer
from app.modules.metricas import fechas
from app.modules.metricas.schemas import (
    MermaPorMotivo,
    MermasRead,
    PuntoDeVentas,
    ResumenRead,
    StockBajoItem,
    StockBajoRead,
    StockBajoResumen,
    TopProducto,
    VentasRead,
)
from app.modules.metricas.uow import MetricasUnitOfWork
from app.modules.productos.models import MovimientoIngrediente, MovimientoStock

CENTAVO = Decimal("0.01")
ESTADOS_PEDIDO = ("PENDIENTE", "CONFIRMADO", "EN_PREPARACION", "EN_CAMINO", "ENTREGADO", "CANCELADO")
DIAS_POR_DEFECTO = 30


def _zona(uow: MetricasUnitOfWork) -> ZoneInfo:
    local = uow.local.unico()
    if local is None:
        raise NotFoundError("El local todavía no está configurado", code="LOCAL_NOT_CONFIGURED")
    return ZoneInfo(local.zona_horaria)


def _rango(desde: date | None, hasta: date | None, zona: ZoneInfo, ahora: datetime) -> tuple[date, date]:
    """Por defecto, los últimos 30 días (hoy incluido). Un rango invertido o de más de un año es 422."""
    fin = hasta or fechas.hoy_local(ahora, zona)
    inicio = desde or fin - timedelta(days=DIAS_POR_DEFECTO - 1)
    if inicio > fin:
        raise ValidationError("`desde` no puede ser posterior a `hasta`", code="INVALID_RANGE", field="desde")
    if (fin - inicio).days + 1 > fechas.MAX_DIAS_RANGO:
        raise ValidationError(
            f"El rango no puede superar {fechas.MAX_DIAS_RANGO} días", code="RANGE_TOO_LARGE", field="desde"
        )
    return inicio, fin


def resumen(uow: MetricasUnitOfWork, ahora: datetime | None = None) -> ResumenRead:
    """Ventas y pedidos del día, ticket promedio, pedidos y pagos por estado y cantidad de stock bajo."""
    with uow:
        zona, ahora = _zona(uow), ahora or utcnow()
        dia = fechas.hoy_local(ahora, zona)
        desde, hasta = fechas.limites_del_dia(dia, zona)
        total, pagados = uow.metricas.ventas_en(desde, hasta)
        ticket = (total / pagados).quantize(CENTAVO, ROUND_HALF_UP) if pagados else Decimal("0.00")
        por_estado = {e: 0 for e in ESTADOS_PEDIDO} | uow.metricas.pedidos_por_estado()
        return ResumenRead(
            fecha=dia,
            ventas_del_dia=total,
            pedidos_pagados_del_dia=pagados,
            ticket_promedio=ticket,
            pedidos_del_dia=uow.metricas.pedidos_creados_en(desde, hasta),
            pedidos_por_estado=por_estado,
            pagos_por_estado=uow.metricas.pagos_por_estado(),
            stock_bajo=StockBajoResumen(
                productos=len(uow.metricas.productos_bajo_minimo()),
                insumos=len(uow.metricas.ingredientes_bajo_minimo()),
            ),
        )


def ventas(
    uow: MetricasUnitOfWork, desde: date | None, hasta: date | None, ahora: datetime | None = None
) -> VentasRead:
    """Serie de ingresos por día del local. Los días sin ventas aparecen en cero (el gráfico no se corta)."""
    with uow:
        zona = _zona(uow)
        inicio, fin = _rango(desde, hasta, zona, ahora or utcnow())
        instante_desde, instante_hasta = fechas.limites_del_rango(inicio, fin, zona)
        por_dia = uow.metricas.serie_de_ventas(instante_desde, instante_hasta, str(zona))
        serie = [
            PuntoDeVentas(fecha=d, total=por_dia.get(d, (Decimal(0), 0))[0], pedidos=por_dia.get(d, (0, 0))[1])
            for d in fechas.dias_entre(inicio, fin)
        ]
        return VentasRead(
            desde=inicio,
            hasta=fin,
            total=sum((p.total for p in serie), Decimal(0)),
            pedidos=sum(p.pedidos for p in serie),
            serie=serie,
        )


def top_productos(uow: MetricasUnitOfWork, limite: int) -> list[TopProducto]:
    with uow:
        return [
            TopProducto(producto_id=pid, nombre=nombre, unidades=int(unidades), ingresos=ingresos)
            for pid, nombre, unidades, ingresos in uow.metricas.top_productos(limite)
        ]


def _items(filas) -> list[StockBajoItem]:
    return [
        StockBajoItem(id=i, nombre=n, unidad_medida=unidad, stock_minimo=minimo, stock_real=real, stock_disponible=disp)
        for i, n, minimo, real, disp, unidad in filas
    ]


def stock_bajo(uow: MetricasUnitOfWork, dias: int) -> StockBajoRead:
    """Productos e insumos con stock disponible <= mínimo, y los lotes que vencen dentro de `dias` días."""
    with uow:
        return StockBajoRead(
            productos=_items(uow.metricas.productos_bajo_minimo()),
            insumos=_items(uow.metricas.ingredientes_bajo_minimo()),
            dias=dias,
            lotes_por_vencer=calcular_lotes_por_vencer(uow, dias),
        )


def mermas(
    uow: MetricasUnitOfWork, desde: date | None, hasta: date | None, ahora: datetime | None = None
) -> MermasRead:
    """Mermas por motivo en el período, separadas en productos e insumos (sus unidades no se pueden sumar)."""
    with uow:
        zona = _zona(uow)
        inicio, fin = _rango(desde, hasta, zona, ahora or utcnow())
        instante_desde, instante_hasta = fechas.limites_del_rango(inicio, fin, zona)

        def por_motivo(modelo):
            return [
                MermaPorMotivo(motivo=m, cantidad=c, movimientos=n)
                for m, c, n in uow.metricas.mermas(modelo, instante_desde, instante_hasta)
            ]

        return MermasRead(
            desde=inicio,
            hasta=fin,
            productos=por_motivo(MovimientoStock),
            insumos=por_motivo(MovimientoIngrediente),
        )
