"""HTTP puro de los pagos (sección 6.6)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response

from app.core.config import get_settings
from app.core.deps import CurrentUser, IdempotencyKey, get_current_user, require_roles
from app.core.errors import ServiceUnavailableError, UnauthorizedError
from app.modules.pagos import service
from app.modules.pagos.deps import get_pagos_uow
from app.modules.pagos.pasarela import Pasarela, firma_valida, get_pasarela
from app.modules.pagos.schemas import FormaPagoRead, MercadoPagoConfig, PagoCreate, PagoMercadoPago, PagoRead
from app.modules.pedidos.uow import PedidosUnitOfWork

router = APIRouter(prefix="/pagos", tags=["pagos"])

Uow = Annotated[PedidosUnitOfWork, Depends(get_pagos_uow)]
Autenticado = Annotated[CurrentUser, Depends(get_current_user)]
Personal = Annotated[CurrentUser, Depends(require_roles("ADMIN", "PEDIDOS"))]
Cliente = Annotated[CurrentUser, Depends(require_roles("CLIENT"))]
PasarelaDePago = Annotated[Pasarela, Depends(get_pasarela)]


@router.get("/formas", response_model=list[FormaPagoRead])
def formas_de_pago(_: Autenticado, uow: Uow):
    """Formas de pago habilitadas para el checkout. Va antes de `/{pedido_id}` para que no se confunda con un id."""
    return service.formas_habilitadas(uow)


@router.get("/mercadopago/config", response_model=MercadoPagoConfig)
def configuracion_de_mercadopago(_: Autenticado):
    """Clave pública para que el SDK del navegador tokenice la tarjeta. 503 si el servidor no la tiene."""
    s = get_settings()
    if not s.MP_CONFIGURADO:
        raise ServiceUnavailableError("MercadoPago no está configurado en este servidor", code="MP_NOT_CONFIGURED")
    return MercadoPagoConfig(public_key=s.MP_PUBLIC_KEY)


@router.post("/mercadopago", status_code=201, response_model=PagoRead)
def pagar_con_mercadopago(body: PagoMercadoPago, usuario: Cliente, uow: Uow, pasarela: PasarelaDePago):
    """Cobra con tarjeta el pedido PENDIENTE del cliente. `approved` confirma el pedido; `pending` e `in_process`
    lo dejan PENDIENTE hasta el webhook; `rejected` devuelve el detalle y permite reintentar."""
    return service.pagar_con_mercadopago(uow, pasarela, body, usuario)


@router.post("/webhook")
async def webhook_de_mercadopago(
    request: Request,
    uow: Uow,
    pasarela: PasarelaDePago,
    x_signature: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
):
    """Notificación de MercadoPago. Público, pero solo se acepta con la firma válida (B.2). Siempre responde 200
    a una notificación auténtica, aun si no hay nada que hacer, para que MercadoPago deje de reintentarla."""
    try:
        cuerpo = await request.json()
    except ValueError:  # sin cuerpo o no es JSON: igual se firma sobre la query y las cabeceras
        cuerpo = {}
    if not isinstance(cuerpo, dict):
        cuerpo = {}
    data_id = request.query_params.get("data.id") or str((cuerpo.get("data") or {}).get("id") or "")
    if not firma_valida(get_settings().MP_WEBHOOK_SECRET, x_signature, x_request_id, data_id):
        raise UnauthorizedError("Firma inválida", code="INVALID_SIGNATURE")
    tipo = request.query_params.get("type") or cuerpo.get("type")
    if tipo != "payment" or not data_id.isdigit():
        return {"resultado": "ignorada"}
    return {"resultado": service.procesar_notificacion(uow, pasarela, int(data_id))}


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
