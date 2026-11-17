"""HTTP puro de la producción (sección 6.4): valida, verifica el rol y delega en el Service."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, require_roles
from app.core.schemas import Paginated
from app.modules.produccion import service
from app.modules.produccion.deps import get_produccion_uow
from app.modules.produccion.schemas import FiltrosOrdenes, OrdenCancelar, OrdenCompletar, OrdenCreate, OrdenRead
from app.modules.produccion.uow import ProduccionUnitOfWork

router = APIRouter(prefix="/produccion", tags=["produccion"])

Uow = Annotated[ProduccionUnitOfWork, Depends(get_produccion_uow)]
AdminOStock = Annotated[CurrentUser, Depends(require_roles("ADMIN", "STOCK"))]


@router.get("", response_model=Paginated[OrdenRead])
def listar_ordenes(_: AdminOStock, uow: Uow, filtros: Annotated[FiltrosOrdenes, Query()]):
    return service.listar_ordenes(uow, filtros)


@router.post("", status_code=201, response_model=OrdenRead)
def planificar_orden(body: OrdenCreate, _: AdminOStock, uow: Uow):
    """Planificar: crea la orden (PLANIFICADA) y reserva los insumos. 409 si falta alguno."""
    return service.crear_orden(uow, body)


@router.get("/{orden_id}", response_model=OrdenRead)
def obtener_orden(orden_id: int, _: AdminOStock, uow: Uow):
    """Detalle con los insumos que consume la orden."""
    return service.obtener_orden(uow, orden_id)


@router.patch("/{orden_id}/iniciar", response_model=OrdenRead)
def iniciar_orden(orden_id: int, usuario: AdminOStock, uow: Uow):
    return service.iniciar_orden(uow, orden_id, usuario)


@router.patch("/{orden_id}/completar", response_model=OrdenRead)
def completar_orden(orden_id: int, usuario: AdminOStock, uow: Uow, body: OrdenCompletar | None = None):
    """Libera y consume los insumos y da de alta el resultado (opcionalmente con lote)."""
    return service.completar_orden(uow, orden_id, body or OrdenCompletar(), usuario)


@router.patch("/{orden_id}/cancelar", response_model=OrdenRead)
def cancelar_orden(orden_id: int, body: OrdenCancelar, usuario: AdminOStock, uow: Uow):
    return service.cancelar_orden(uow, orden_id, body, usuario)
