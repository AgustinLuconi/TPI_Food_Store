"""Pagos (sección 9.4 y Anexo B): el pago confirma el pedido en la MISMA transacción.

Efectivo y transferencia los registra el personal; MercadoPago lo cobra el cliente con tarjeta y lo confirma la
pasarela (en la respuesta o, más tarde, por webhook).
"""

import uuid

from app.core.deps import CurrentUser
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.modules.pagos.formas import MERCADOPAGO, forma_ofrecida
from app.modules.pagos.models import Pago
from app.modules.pagos.pasarela import CobroConTarjeta, PagoMP, Pasarela
from app.modules.pagos.schemas import FormaPagoRead, PagoCreate, PagoMercadoPago, PagoRead
from app.modules.pedidos import service as pedidos
from app.modules.pedidos.uow import PedidosUnitOfWork

# Efectivo y transferencia los registra el personal una vez verificado el cobro o el comprobante.
FORMAS_MANUALES = frozenset({"EFECTIVO", "TRANSFERENCIA"})


def registrar_pago(
    uow: PedidosUnitOfWork, pedido_id: int, datos: PagoCreate, usuario: CurrentUser, clave: str
) -> tuple[PagoRead, bool]:
    """Devuelve (pago, creado). Repetir la misma Idempotency-Key devuelve el pago ya registrado sin duplicarlo;
    un segundo pago distinto para el mismo pedido es 409."""
    with uow:
        pedido = pedidos.obtener_pedido_visible(uow, pedido_id, usuario, bloquear=True)

        existente = uow.pagos.get_by_pedido(pedido.id)  # type: ignore[arg-type]
        if existente is not None:
            if existente.idempotency_key == clave:
                return PagoRead.model_validate(existente), False
            raise ConflictError("El pedido ya tiene un pago registrado", code="PAYMENT_ALREADY_REGISTERED")
        if uow.pagos.get_by_idempotency_key(clave) is not None:
            raise ConflictError("Esa Idempotency-Key ya se usó en otro pago", code="IDEMPOTENCY_KEY_REUSED")

        if pedido.estado_codigo != "PENDIENTE":
            raise ConflictError(
                f"Solo se registra el pago de un pedido PENDIENTE (está {pedido.estado_codigo})",
                code="ORDER_NOT_PENDING",
            )
        if pedido.forma_pago_codigo not in FORMAS_MANUALES:
            raise ValidationError(
                f"El pago {pedido.forma_pago_codigo} no se registra a mano", code="PAYMENT_METHOD_NOT_MANUAL"
            )
        if datos.monto != pedido.total:
            raise ValidationError(
                f"El monto debe coincidir con el total del pedido ({pedido.total})",
                code="AMOUNT_MISMATCH",
                field="monto",
            )

        pago = uow.pagos.create(
            Pago(
                pedido_id=pedido.id,  # type: ignore[arg-type]
                forma_pago_codigo=pedido.forma_pago_codigo,
                monto=datos.monto,
                mp_status="approved",
                external_reference=pedido.external_reference,
                idempotency_key=clave,
            )
        )
        pedidos.registrar_transicion(uow, pedido, "CONFIRMADO", usuario.id)
        return PagoRead.model_validate(pago), True


def obtener_pago(uow: PedidosUnitOfWork, pedido_id: int, usuario: CurrentUser) -> PagoRead:
    with uow:
        pedido = pedidos.obtener_pedido_visible(uow, pedido_id, usuario)
        pago = uow.pagos.get_by_pedido(pedido.id)  # type: ignore[arg-type]
        if pago is None:
            raise NotFoundError("El pedido todavía no tiene un pago registrado", code="PAYMENT_NOT_FOUND")
        return PagoRead.model_validate(pago)


def formas_habilitadas(uow: PedidosUnitOfWork) -> list[FormaPagoRead]:
    """Las formas de pago que el checkout ofrece (FormaPago.habilitado = true)."""
    with uow:
        return [FormaPagoRead.model_validate(f) for f in uow.formas_pago.habilitadas() if forma_ofrecida(f.codigo)]


# Estados de MercadoPago con un cobro vivo: reintentar con otra tarjeta podría cobrar dos veces.
ESTADOS_EN_CURSO = frozenset({"approved", "authorized", "pending", "in_process", "in_mediation"})


def pagar_con_mercadopago(
    uow: PedidosUnitOfWork, pasarela: Pasarela, datos: PagoMercadoPago, usuario: CurrentUser
) -> PagoRead:
    """Cobra el pedido con la tarjeta tokenizada (B.3). El monto sale del pedido, nunca del cliente.

    Hay un solo registro de Pago por pedido: un reintento tras un rechazo lo actualiza con el nuevo pago y
    una `idempotency_key` nueva, generada acá (no la manda el navegador).
    """
    with uow:
        pedido = pedidos.obtener_pedido_visible(uow, datos.pedido_id, usuario, bloquear=True)
        if pedido.usuario_id != usuario.id:  # el personal no cobra con la tarjeta de otra persona
            raise NotFoundError("Pedido no encontrado", code="ORDER_NOT_FOUND")
        if pedido.forma_pago_codigo != MERCADOPAGO:
            raise ValidationError(
                f"El pedido se paga con {pedido.forma_pago_codigo}, no con MercadoPago",
                code="PAYMENT_METHOD_NOT_MERCADOPAGO",
            )
        if pedido.estado_codigo != "PENDIENTE":
            raise ConflictError(
                f"Solo se paga un pedido PENDIENTE (está {pedido.estado_codigo})", code="ORDER_NOT_PENDING"
            )
        existente = uow.pagos.get_by_pedido(pedido.id)  # type: ignore[arg-type]
        if existente is not None and existente.mp_status in ESTADOS_EN_CURSO:
            if existente.mp_status in {"approved", "authorized"}:
                raise ConflictError("El pedido ya tiene un pago aprobado", code="PAYMENT_ALREADY_REGISTERED")
            raise ConflictError(
                "Hay un pago en proceso: esperá la confirmación de MercadoPago", code="PAYMENT_IN_PROGRESS"
            )

        clave = str(uuid.uuid4())
        mp = pasarela.crear_pago(
            CobroConTarjeta(
                token=datos.token,
                monto=pedido.total,
                descripcion=f"Food Store · pedido #{pedido.id}",
                metodo_de_pago=datos.payment_method_id,
                cuotas=datos.installments,
                email=str(datos.email),
                emisor=datos.issuer_id,
                identificacion_tipo=datos.identification_type,
                identificacion_numero=datos.identification_number,
                external_reference=pedido.external_reference,
                idempotency_key=clave,
            )
        )
        campos = {
            "mp_payment_id": mp.id,
            "mp_status": mp.status,
            "mp_status_detail": mp.status_detail,
            "idempotency_key": clave,
        }
        if existente is None:
            pago = uow.pagos.create(
                Pago(
                    pedido_id=pedido.id,  # type: ignore[arg-type]
                    forma_pago_codigo=MERCADOPAGO,
                    monto=pedido.total,
                    external_reference=pedido.external_reference,
                    **campos,  # type: ignore[arg-type]
                )
            )
        else:
            pago = uow.pagos.update(existente, campos)
        if mp.status == "approved":
            pedidos.registrar_transicion(uow, pedido, "CONFIRMADO", usuario.id)
        return PagoRead.model_validate(pago)


def procesar_notificacion(uow: PedidosUnitOfWork, pasarela: Pasarela, payment_id: int) -> str:
    """Webhook (B.3 paso 5): consulta el pago en MercadoPago y sincroniza el registro y el pedido.

    Idempotente: la misma notificación repetida no cambia nada. Devuelve qué hizo, para el log y los tests.
    """
    mp = pasarela.obtener_pago(payment_id)  # fuera de la transacción: no se retiene un bloqueo mientras se espera
    if mp is None or not mp.external_reference:
        return "ignorada"
    with uow:
        pago = uow.pagos.get_by_external_reference(mp.external_reference)
        if pago is None:
            return "ignorada"
        pedido = uow.pedidos.get_for_update(pago.pedido_id)
        if pedido is None:
            return "ignorada"
        if pago.mp_payment_id not in (None, mp.id):
            return "ignorada"  # aviso de un intento anterior ya reemplazado por un reintento
        return _sincronizar(uow, pago, pedido, mp)


def _sincronizar(uow: PedidosUnitOfWork, pago: Pago, pedido, mp: PagoMP) -> str:
    sin_cambios = pago.mp_payment_id == mp.id and pago.mp_status == mp.status
    if not sin_cambios or pago.mp_status_detail != mp.status_detail:
        uow.pagos.update(pago, {"mp_payment_id": mp.id, "mp_status": mp.status, "mp_status_detail": mp.status_detail})
    if mp.status == "approved" and pedido.estado_codigo == "PENDIENTE":
        pedidos.registrar_transicion(uow, pedido, "CONFIRMADO", None, "Pago aprobado por MercadoPago")
        return "confirmada"
    # Si el pedido ya estaba confirmado (o se canceló) no se toca: el aviso repetido es inofensivo.
    return "sin_cambios" if sin_cambios else "actualizada"
