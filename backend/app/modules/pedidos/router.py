"""HTTP puro de los pedidos (sección 6.5): valida, verifica el rol y delega en el Service."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.core.deps import CurrentUser, IdempotencyKey, get_current_user, require_roles
from app.core.schemas import Paginated
from app.modules.pedidos import service
from app.modules.pedidos.deps import get_pedidos_uow
from app.modules.pedidos.schemas import (
    CancelarPedido,
    EstadoUpdate,
    FiltrosPedidos,
    HistorialRead,
    PedidoCreate,
    PedidoItem,
    PedidoRead,
)
from app.modules.pedidos.uow import PedidosUnitOfWork

router = APIRouter(prefix="/pedidos", tags=["pedidos"])

Uow = Annotated[PedidosUnitOfWork, Depends(get_pedidos_uow)]
Autenticado = Annotated[CurrentUser, Depends(get_current_user)]
Cliente = Annotated[CurrentUser, Depends(require_roles("CLIENT"))]
Personal = Annotated[CurrentUser, Depends(require_roles("ADMIN", "PEDIDOS"))]


@router.get("", response_model=Paginated[PedidoItem])
def listar_pedidos(usuario: Autenticado, uow: Uow, filtros: Annotated[FiltrosPedidos, Query()]):
    """Propios (CLIENT) o todos (ADMIN, PEDIDOS). Filtros: estado, desde y hasta (días del local)."""
    return service.listar_pedidos(uow, usuario, filtros)


@router.post("", status_code=201, response_model=PedidoRead)
def crear_pedido(body: PedidoCreate, usuario: Cliente, uow: Uow, clave: IdempotencyKey, response: Response):
    """Crea el pedido desde el carrito. Requiere `Idempotency-Key` (UUID): repetirla devuelve el mismo pedido
    (200) sin crear otro."""
    pedido, creado = service.crear_pedido(uow, usuario, body, clave)
    if not creado:
        response.status_code = 200
    return pedido


@router.get("/{pedido_id}", response_model=PedidoRead)
def obtener_pedido(pedido_id: int, usuario: Autenticado, uow: Uow):
    """Detalle con líneas, exclusiones, pago e historial. Propietario, ADMIN o PEDIDOS."""
    return service.obtener_pedido(uow, pedido_id, usuario)


@router.patch("/{pedido_id}/estado", response_model=PedidoRead)
def cambiar_estado(pedido_id: int, body: EstadoUpdate, usuario: Personal, uow: Uow):
    return service.cambiar_estado(uow, pedido_id, body, usuario)


@router.post("/{pedido_id}/cancelar", response_model=PedidoRead)
def cancelar_pedido(pedido_id: int, body: CancelarPedido, usuario: Autenticado, uow: Uow):
    """Cancela con motivo (RN-05). El propietario en PENDIENTE o CONFIRMADO; ADMIN y PEDIDOS en cualquier
    estado no terminal."""
    return service.cancelar_pedido(uow, pedido_id, body, usuario)


@router.get("/{pedido_id}/historial", response_model=list[HistorialRead])
def obtener_historial(pedido_id: int, usuario: Autenticado, uow: Uow):
    return service.obtener_historial(uow, pedido_id, usuario)
