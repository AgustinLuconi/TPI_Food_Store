from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.modules.inventario.schemas import LotePorVencer


class StockBajoResumen(BaseModel):
    productos: int
    insumos: int


class ResumenRead(BaseModel):
    """Panel del ADMIN: el día en la zona horaria del local."""

    fecha: date
    ventas_del_dia: Decimal
    pedidos_pagados_del_dia: int
    ticket_promedio: Decimal
    pedidos_del_dia: int
    pedidos_por_estado: dict[str, int]
    pagos_por_estado: dict[str, int]
    stock_bajo: StockBajoResumen


class PuntoDeVentas(BaseModel):
    fecha: date
    total: Decimal
    pedidos: int


class VentasRead(BaseModel):
    desde: date
    hasta: date
    total: Decimal
    pedidos: int
    serie: list[PuntoDeVentas]


class TopProducto(BaseModel):
    producto_id: int
    nombre: str
    unidades: int
    ingresos: Decimal


class StockBajoItem(BaseModel):
    id: int
    nombre: str
    # Solo los insumos tienen unidad (RN-10); un producto se cuenta en unidades y no la lleva.
    unidad_medida: str | None = None
    stock_minimo: int
    stock_real: Decimal
    stock_disponible: Decimal


class StockBajoRead(BaseModel):
    productos: list[StockBajoItem]
    insumos: list[StockBajoItem]
    dias: int
    lotes_por_vencer: list[LotePorVencer]


class MermaDeInsumo(BaseModel):
    """Cuánto aportó un insumo al total de un motivo."""

    ingrediente_id: int
    nombre: str
    cantidad: Decimal
    movimientos: int


class MermaPorMotivo(BaseModel):
    motivo: str
    # Solo en los insumos: kilos y unidades no se suman (RN-10), así que un motivo con insumos de distinta unidad
    # aparece en una fila por unidad. `detalle` dice qué insumos componen el total y cuánto aportó cada uno.
    unidad_medida: str | None = None
    cantidad: Decimal
    movimientos: int
    detalle: list[MermaDeInsumo] = []


class MermasRead(BaseModel):
    desde: date
    hasta: date
    productos: list[MermaPorMotivo]
    insumos: list[MermaPorMotivo]
