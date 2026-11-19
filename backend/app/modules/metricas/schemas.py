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
    stock_minimo: int
    stock_real: Decimal
    stock_disponible: Decimal


class StockBajoRead(BaseModel):
    productos: list[StockBajoItem]
    insumos: list[StockBajoItem]
    dias: int
    lotes_por_vencer: list[LotePorVencer]


class MermaPorMotivo(BaseModel):
    motivo: str
    cantidad: Decimal
    movimientos: int


class MermasRead(BaseModel):
    desde: date
    hasta: date
    productos: list[MermaPorMotivo]
    insumos: list[MermaPorMotivo]
