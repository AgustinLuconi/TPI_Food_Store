"""Pagos (sección 9.4): registro manual idempotente que confirma el pedido en la MISMA transacción."""

from app.core.deps import CurrentUser
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.modules.pagos.models import Pago
from app.modules.pagos.schemas import PagoCreate, PagoRead
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
