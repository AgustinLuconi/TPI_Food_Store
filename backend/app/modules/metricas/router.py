"""HTTP puro de las métricas del panel (sección 6.8): valida, verifica el rol y delega en el Service."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, require_roles
from app.modules.metricas import service
from app.modules.metricas.deps import get_metricas_uow
from app.modules.metricas.schemas import MermasRead, ResumenRead, StockBajoRead, TopProducto, VentasRead
from app.modules.metricas.uow import MetricasUnitOfWork

router = APIRouter(prefix="/admin/metrics", tags=["metricas"])

Uow = Annotated[MetricasUnitOfWork, Depends(get_metricas_uow)]
Admin = Annotated[CurrentUser, Depends(require_roles("ADMIN"))]
AdminOStock = Annotated[CurrentUser, Depends(require_roles("ADMIN", "STOCK"))]


@router.get("/resumen", response_model=ResumenRead)
def resumen(_: Admin, uow: Uow):
    """Ventas y pedidos del día, ticket promedio, pedidos y pagos por estado, y stock bajo."""
    return service.resumen(uow)


@router.get("/ventas", response_model=VentasRead)
def ventas(
    _: Admin,
    uow: Uow,
    desde: Annotated[date | None, Query(description="Por defecto, 30 días atrás")] = None,
    hasta: Annotated[date | None, Query(description="Por defecto, hoy")] = None,
):
    """Serie temporal de ingresos por día (en la zona horaria del local)."""
    return service.ventas(uow, desde, hasta)


@router.get("/top-productos", response_model=list[TopProducto])
def top_productos(_: Admin, uow: Uow, limit: Annotated[int, Query(ge=1, le=50)] = 10):
    """Ranking de productos vendidos (unidades e ingresos)."""
    return service.top_productos(uow, limit)


@router.get("/stock-bajo", response_model=StockBajoRead)
def stock_bajo(_: AdminOStock, uow: Uow, dias: Annotated[int, Query(ge=0, le=365)] = 7):
    """Productos e insumos bajo el mínimo y lotes por vencer."""
    return service.stock_bajo(uow, dias)


@router.get("/mermas", response_model=MermasRead)
def mermas(
    _: AdminOStock,
    uow: Uow,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
):
    """Mermas por motivo y período."""
    return service.mermas(uow, desde, hasta)
