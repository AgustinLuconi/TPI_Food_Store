"""HTTP puro de los pagos (sección 6.6)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.deps import CurrentUser, IdempotencyKey, get_current_user, require_roles
from app.modules.pagos import service
from app.modules.pagos.deps import get_pagos_uow
from app.modules.pagos.schemas import PagoCreate, PagoRead
from app.modules.pedidos.uow import PedidosUnitOfWork

router = APIRouter(prefix="/pagos", tags=["pagos"])

Uow = Annotated[PedidosUnitOfWork, Depends(get_pagos_uow)]
Autenticado = Annotated[CurrentUser, Depends(get_current_user)]
Personal = Annotated[CurrentUser, Depends(require_roles("ADMIN", "PEDIDOS"))]


@router.post("/{pedido_id}", status_code=201, response_model=PagoRead)
def registrar_pago(
    pedido_id: int, body: PagoCreate, usuario: Personal, uow: Uow, clave: IdempotencyKey, response: Response
):
    """Registra un pago en efectivo o por transferencia y confirma el pedido (PENDIENTE → CONFIRMADO).
    Requiere `Idempotency-Key`: repetirla devuelve el mismo pago (200). Un segundo pago es 409."""
    pago, creado = service.registrar_pago(uow, pedido_id, body, usuario, clave)
    if not creado:
        response.status_code = 200
    return pago


@router.get("/{pedido_id}", response_model=PagoRead)
def obtener_pago(pedido_id: int, usuario: Autenticado, uow: Uow):
    """Pago del pedido. Propietario, ADMIN o PEDIDOS."""
    return service.obtener_pago(uow, pedido_id, usuario)
