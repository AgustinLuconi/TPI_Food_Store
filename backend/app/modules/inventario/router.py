"""HTTP puro del inventario (sección 6.4): valida, verifica el rol y delega en el Service."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, require_roles
from app.core.schemas import Paginated
from app.modules.inventario import service
from app.modules.inventario.deps import get_inventario_uow
from app.modules.inventario.schemas import (
    FiltrosMovimientos,
    LotePorVencer,
    LoteRead,
    MovimientoCreate,
    MovimientoProductoCreate,
    MovimientoRead,
    StockRead,
)
from app.modules.inventario.uow import InventarioUnitOfWork

router = APIRouter(tags=["inventario"])

Uow = Annotated[InventarioUnitOfWork, Depends(get_inventario_uow)]
AdminOStock = Annotated[CurrentUser, Depends(require_roles("ADMIN", "STOCK"))]


@router.get("/productos/{producto_id}/stock", response_model=StockRead)
def stock_de_producto(producto_id: int, _: AdminOStock, uow: Uow):
    """stock_real y stock_disponible, derivados del ledger."""
    return service.obtener_stock_producto(uow, producto_id)


@router.get("/productos/{producto_id}/movimientos", response_model=Paginated[MovimientoRead])
def movimientos_de_producto(
    producto_id: int, _: AdminOStock, uow: Uow, filtros: Annotated[FiltrosMovimientos, Query()]
):
    """Ledger del producto, del más reciente al más antiguo."""
    return service.listar_movimientos_producto(uow, producto_id, filtros)


@router.post("/productos/{producto_id}/movimientos", status_code=201, response_model=list[MovimientoRead])
def registrar_movimiento_de_producto(producto_id: int, body: MovimientoProductoCreate, _: AdminOStock, uow: Uow):
    """Alta manual (RN-07, RN-08). Devuelve un movimiento por lote afectado (FEFO, RN-09)."""
    return service.registrar_movimiento_producto(uow, producto_id, body)


@router.get("/productos/{producto_id}/lotes", response_model=list[LoteRead])
def lotes_de_producto(producto_id: int, _: AdminOStock, uow: Uow):
    return service.lotes_de_producto(uow, producto_id)


@router.get("/ingredientes/{ingrediente_id}/stock", response_model=StockRead)
def stock_de_ingrediente(ingrediente_id: int, _: AdminOStock, uow: Uow):
    return service.obtener_stock_ingrediente(uow, ingrediente_id)


@router.get("/ingredientes/{ingrediente_id}/movimientos", response_model=Paginated[MovimientoRead])
def movimientos_de_ingrediente(
    ingrediente_id: int, _: AdminOStock, uow: Uow, filtros: Annotated[FiltrosMovimientos, Query()]
):
    return service.listar_movimientos_ingrediente(uow, ingrediente_id, filtros)


@router.post("/ingredientes/{ingrediente_id}/movimientos", status_code=201, response_model=MovimientoRead)
def registrar_movimiento_de_ingrediente(ingrediente_id: int, body: MovimientoCreate, _: AdminOStock, uow: Uow):
    return service.registrar_movimiento_ingrediente(uow, ingrediente_id, body)


@router.get("/inventario/por-vencer", response_model=list[LotePorVencer])
def por_vencer(_: AdminOStock, uow: Uow, dias: Annotated[int, Query(ge=0, le=365)] = 7):
    """Lotes con stock que vencen en los próximos `dias` días o que ya vencieron."""
    return service.lotes_por_vencer(uow, dias)
