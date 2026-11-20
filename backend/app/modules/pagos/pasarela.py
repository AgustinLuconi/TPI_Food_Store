"""Pasarela de pagos (Anexo B): el service habla con un puerto, no con el SDK de MercadoPago.

Así los tests inyectan una pasarela falsa por `dependency_overrides` y nunca llaman a la red. Los datos de la
tarjeta no pasan por acá: el navegador los tokeniza con MercadoPago y el backend solo recibe el token.
"""

import hashlib
import hmac
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

import mercadopago
from mercadopago.config import RequestOptions

from app.core.config import get_settings
from app.core.errors import BadGatewayError, ServiceUnavailableError, ValidationError


@dataclass(frozen=True)
class PagoMP:
    """Lo que el sistema necesita saber de un pago de MercadoPago."""

    id: int
    status: str
    status_detail: str | None
    external_reference: str | None


@dataclass(frozen=True)
class CobroConTarjeta:
    token: str
    monto: Decimal
    descripcion: str
    metodo_de_pago: str
    cuotas: int
    email: str
    emisor: str | None
    identificacion_tipo: str | None
    identificacion_numero: str | None
    external_reference: str
    idempotency_key: str


class Pasarela(Protocol):
    def crear_pago(self, cobro: CobroConTarjeta) -> PagoMP: ...

    def obtener_pago(self, payment_id: int) -> PagoMP | None: ...


def _a_pago(datos: dict) -> PagoMP:
    return PagoMP(
        id=int(datos["id"]),
        status=str(datos["status"]),
        status_detail=datos.get("status_detail"),
        external_reference=datos.get("external_reference"),
    )


class MercadoPagoPasarela:
    """Adaptador del SDK oficial (`mercadopago`) con las credenciales de la configuración."""

    def __init__(self, access_token: str, notification_url: str = "") -> None:
        self._sdk = mercadopago.SDK(access_token)
        self._access_token = access_token
        self._notification_url = notification_url

    def crear_pago(self, cobro: CobroConTarjeta) -> PagoMP:
        cuerpo: dict = {
            "transaction_amount": float(cobro.monto),
            "token": cobro.token,
            "description": cobro.descripcion,
            "installments": cobro.cuotas,
            "payment_method_id": cobro.metodo_de_pago,
            "external_reference": cobro.external_reference,
            "payer": {"email": cobro.email},
        }
        if cobro.emisor:
            cuerpo["issuer_id"] = cobro.emisor
        if cobro.identificacion_tipo and cobro.identificacion_numero:
            cuerpo["payer"]["identification"] = {
                "type": cobro.identificacion_tipo,
                "number": cobro.identificacion_numero,
            }
        if self._notification_url:
            cuerpo["notification_url"] = self._notification_url
        opciones = RequestOptions(
            access_token=self._access_token, custom_headers={"x-idempotency-key": cobro.idempotency_key}
        )
        try:
            r = self._sdk.payment().create(cuerpo, opciones)
        except Exception as exc:  # red caída, tiempo agotado, etc.
            raise BadGatewayError("No se pudo contactar a MercadoPago", code="MP_UNAVAILABLE") from exc
        estado, datos = r.get("status", 0), r.get("response") or {}
        if estado >= 500:
            raise BadGatewayError("MercadoPago no pudo procesar el pago", code="MP_UNAVAILABLE")
        if estado >= 400:  # token inválido o vencido, datos mal formados…
            raise ValidationError(
                str(datos.get("message") or "MercadoPago rechazó los datos del pago"), code="MP_REQUEST_REJECTED"
            )
        return _a_pago(datos)

    def obtener_pago(self, payment_id: int) -> PagoMP | None:
        try:
            r = self._sdk.payment().get(payment_id, RequestOptions(access_token=self._access_token))
        except Exception as exc:
            raise BadGatewayError("No se pudo contactar a MercadoPago", code="MP_UNAVAILABLE") from exc
        estado = r.get("status", 0)
        if estado == 404:
            return None
        if estado >= 400:
            raise BadGatewayError("MercadoPago no pudo informar el pago", code="MP_UNAVAILABLE")
        return _a_pago(r["response"])


def get_pasarela() -> Pasarela:
    """Dependencia de FastAPI. Sin credenciales, 503: la funcionalidad no está configurada."""
    s = get_settings()
    if not s.MP_CONFIGURADO:
        raise ServiceUnavailableError("MercadoPago no está configurado en este servidor", code="MP_NOT_CONFIGURED")
    return MercadoPagoPasarela(s.MP_ACCESS_TOKEN, s.MP_NOTIFICATION_URL)


def firma_valida(secret: str, x_signature: str | None, x_request_id: str | None, data_id: str | None) -> bool:
    """Valida la cabecera `x-signature` de una notificación (`ts=<ms>,v1=<hmac>`).

    MercadoPago firma con HMAC-SHA256 el texto `id:<data.id>;request-id:<x-request-id>;ts:<ts>;`; las partes
    que no vengan se omiten. La comparación es de tiempo constante.
    """
    if not secret or not x_signature:
        return False
    partes = dict(p.strip().split("=", 1) for p in x_signature.split(",") if "=" in p)
    ts, recibida = partes.get("ts"), partes.get("v1")
    if not ts or not recibida:
        return False
    manifiesto = ""
    if data_id:
        manifiesto += f"id:{data_id.lower()};"
    if x_request_id:
        manifiesto += f"request-id:{x_request_id};"
    manifiesto += f"ts:{ts};"
    esperada = hmac.new(secret.encode(), manifiesto.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, recibida)
