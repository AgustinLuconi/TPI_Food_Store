"""MercadoPago (Anexo B): cobro con tarjeta tokenizada y confirmación por webhook firmado.

Se usa una pasarela falsa inyectada con `dependency_overrides`: ningún test llama a la red. Los estados que
devuelve imitan a los de las tarjetas de prueba (B.5): el titular APRO aprueba, CONT deja pendiente y OTHE rechaza.
"""

import hashlib
import hmac
import uuid
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from app.core.errors import BadGatewayError, ValidationError
from app.main import app
from app.modules.pagos.pasarela import (
    CobroConTarjeta,
    MercadoPagoPasarela,
    PagoMP,
    firma_valida,
    get_pasarela,
)
from tests.helpers import API, registrar_y_loguear
from tests.pedidos_helpers import PUBLICA, SECRETO, crear_pedido, estado, linea, pagar, pedido_ok
from tests.test_inventario import D

PAGOS = f"{API}/pagos"


@dataclass
class PasarelaFalsa:
    """Responde según `proximo` y guarda lo que recibió, para comprobar qué se le cobró."""

    proximo: tuple[str, str | None] = ("approved", "accredited")
    cobros: list[CobroConTarjeta] = field(default_factory=list)
    pagos: dict[int, PagoMP] = field(default_factory=dict)
    _siguiente_id: int = 5000

    def crear_pago(self, cobro: CobroConTarjeta) -> PagoMP:
        self._siguiente_id += 1
        self.cobros.append(cobro)
        estado_, detalle = self.proximo
        pago = PagoMP(self._siguiente_id, estado_, detalle, cobro.external_reference)
        self.pagos[pago.id] = pago
        return pago

    def obtener_pago(self, payment_id: int) -> PagoMP | None:
        return self.pagos.get(payment_id)

    def cambiar(self, payment_id: int, status: str, detalle: str | None = None) -> None:
        anterior = self.pagos[payment_id]
        self.pagos[payment_id] = PagoMP(payment_id, status, detalle, anterior.external_reference)


@pytest.fixture
def mp(client, mp_configurado) -> PasarelaFalsa:
    falsa = PasarelaFalsa()
    app.dependency_overrides[get_pasarela] = lambda: falsa
    return falsa


def tarjeta(pedido: dict, **extra) -> dict:
    return {
        "pedido_id": pedido["id"],
        "token": "token-de-la-tarjeta",
        "payment_method_id": "visa",
        "installments": 1,
        "email": "cliente@test.com",
        **extra,
    }


def pedido_mp(t, producto=None) -> dict:
    return pedido_ok(t.cliente, [linea(producto or t.pizza)], forma_pago_codigo="MERCADOPAGO")


def cobrar(cliente: TestClient, pedido: dict, **extra):
    return cliente.post(f"{PAGOS}/mercadopago", json=tarjeta(pedido, **extra))


def firmar(data_id: str, *, request_id: str = "req-1", ts: str = "1700000000000", secreto: str = SECRETO) -> dict:
    manifiesto = f"id:{data_id.lower()};request-id:{request_id};ts:{ts};"
    v1 = hmac.new(secreto.encode(), manifiesto.encode(), hashlib.sha256).hexdigest()
    return {"x-signature": f"ts={ts},v1={v1}", "x-request-id": request_id}


def avisar(client: TestClient, payment_id: int | str, *, headers: dict | None = None, tipo: str = "payment"):
    """Imita la notificación de MercadoPago: el id viaja en la query y en el cuerpo."""
    h = firmar(str(payment_id)) if headers is None else headers
    return client.post(
        f"{PAGOS}/webhook",
        params={"data.id": str(payment_id), "type": tipo},
        json={"type": tipo, "action": "payment.updated", "data": {"id": str(payment_id)}},
        headers=h,
    )


def pago_de(cliente: TestClient, pedido_id: int) -> dict:
    return cliente.get(f"{PAGOS}/{pedido_id}").json()


# --- disponibilidad -----------------------------------------------------------------------------------------


def test_sin_credenciales_mercadopago_no_se_ofrece(tienda):
    t = tienda
    codigos = [f["codigo"] for f in t.cliente.get(f"{PAGOS}/formas").json()]
    assert codigos == ["EFECTIVO", "TRANSFERENCIA"]
    r = crear_pedido(t.cliente, [linea(t.pizza)], forma_pago_codigo="MERCADOPAGO")
    assert r.status_code == 422 and r.json()["code"] == "PAYMENT_METHOD_UNAVAILABLE"
    c = t.cliente.get(f"{PAGOS}/mercadopago/config")
    assert c.status_code == 503 and c.json()["code"] == "MP_NOT_CONFIGURED"


def test_con_credenciales_se_ofrece_y_se_expone_solo_la_clave_publica(tienda, mp):
    t = tienda
    codigos = [f["codigo"] for f in t.cliente.get(f"{PAGOS}/formas").json()]
    assert codigos == ["EFECTIVO", "MERCADOPAGO", "TRANSFERENCIA"]
    r = t.cliente.get(f"{PAGOS}/mercadopago/config")
    assert r.status_code == 200 and r.json() == {"public_key": PUBLICA}
    assert "TEST-token" not in r.text and SECRETO not in r.text  # las credenciales privadas nunca salen


def test_la_configuracion_exige_sesion(client, mp_configurado):
    assert client.get(f"{PAGOS}/mercadopago/config").status_code == 401


# --- cobro con tarjeta (CE-B2 y CE-B3) ----------------------------------------------------------------------


def test_pago_aprobado_confirma_el_pedido_de_punta_a_punta(tienda, mp):
    t = tienda
    p = pedido_mp(t)
    r = cobrar(t.cliente, p)
    assert r.status_code == 201, r.text
    pago = r.json()
    assert pago["mp_status"] == "approved" and pago["forma_pago_codigo"] == "MERCADOPAGO"
    assert D(pago["monto"]) == 9500 and pago["external_reference"] == p["external_reference"]
    assert estado(t.cliente, p["id"]) == "CONFIRMADO"
    ultimo = t.cliente.get(f"{API}/pedidos/{p['id']}/historial").json()[-1]
    assert (ultimo["estado_desde"], ultimo["estado_hasta"]) == ("PENDIENTE", "CONFIRMADO")


def test_el_monto_cobrado_es_el_del_pedido_y_se_manda_la_referencia(tienda, mp):
    t = tienda
    p = pedido_mp(t)
    # un monto en el cuerpo se ignora: el esquema no lo acepta y el servidor usa el total del pedido
    assert cobrar(t.cliente, p, monto="1.00", transaction_amount=1).status_code == 201
    cobro = mp.cobros[0]
    assert cobro.monto == D(p["total"]) and cobro.external_reference == p["external_reference"]
    assert cobro.token == "token-de-la-tarjeta" and cobro.email == "cliente@test.com"
    uuid.UUID(cobro.idempotency_key)  # clave generada en el backend


def test_pago_rechazado_deja_el_pedido_pendiente_y_muestra_el_detalle(tienda, mp):
    t = tienda
    mp.proximo = ("rejected", "cc_rejected_other_reason")  # titular OTHE
    p = pedido_mp(t)
    r = cobrar(t.cliente, p)
    assert r.status_code == 201
    assert r.json()["mp_status"] == "rejected" and r.json()["mp_status_detail"] == "cc_rejected_other_reason"
    assert estado(t.cliente, p["id"]) == "PENDIENTE"


def test_reintentar_tras_un_rechazo_reutiliza_el_unico_registro_de_pago(tienda, mp):
    t = tienda
    mp.proximo = ("rejected", "cc_rejected_insufficient_amount")  # titular FUND
    p = pedido_mp(t)
    primero = cobrar(t.cliente, p).json()
    mp.proximo = ("approved", "accredited")
    segundo = cobrar(t.cliente, p).json()
    assert segundo["id"] == primero["id"]  # un solo Pago por pedido (external_reference única)
    assert segundo["mp_status"] == "approved" and segundo["mp_status_detail"] == "accredited"
    assert len({c.idempotency_key for c in mp.cobros}) == 2  # cada intento lleva su propia clave
    assert estado(t.cliente, p["id"]) == "CONFIRMADO"


def test_pago_pendiente_bloquea_un_segundo_cobro_hasta_el_webhook(tienda, mp):
    t = tienda
    mp.proximo = ("in_process", "pending_contingency")  # titular CONT
    p = pedido_mp(t)
    assert cobrar(t.cliente, p).json()["mp_status"] == "in_process"
    assert estado(t.cliente, p["id"]) == "PENDIENTE"
    r = cobrar(t.cliente, p)  # otro clic o otra tarjeta: podría cobrar dos veces
    assert r.status_code == 409 and r.json()["code"] == "PAYMENT_IN_PROGRESS"
    assert len(mp.cobros) == 1


def test_un_pedido_ya_pagado_no_se_cobra_otra_vez(tienda, mp):
    t = tienda
    p = pedido_mp(t)
    assert cobrar(t.cliente, p).status_code == 201
    r = cobrar(t.cliente, p)
    assert r.status_code == 409 and len(mp.cobros) == 1
    assert r.json()["code"] in {"ORDER_NOT_PENDING", "PAYMENT_ALREADY_REGISTERED"}


def test_solo_el_dueno_cliente_puede_pagar(tienda, mp):
    t = tienda
    p = pedido_mp(t)
    assert cobrar(t.pedidos, p).status_code == 403  # el personal no tiene el rol CLIENT
    assert cobrar(t.admin, p).status_code == 403
    assert mp.cobros == []
    # otro cliente: el pedido ajeno no existe para él
    otro = TestClient(t.cliente.app)
    registrar_y_loguear(otro, "otro@test.com")
    r = cobrar(otro, p)
    assert r.status_code == 404 and r.json()["code"] == "ORDER_NOT_FOUND"


def test_un_pedido_en_efectivo_no_se_paga_con_tarjeta(tienda, mp):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza)], forma_pago_codigo="EFECTIVO")
    r = cobrar(t.cliente, p)
    assert r.status_code == 422 and r.json()["code"] == "PAYMENT_METHOD_NOT_MERCADOPAGO"
    assert mp.cobros == []


def test_un_pedido_cancelado_no_se_cobra(tienda, mp):
    t = tienda
    p = pedido_mp(t)
    assert t.cliente.post(f"{API}/pedidos/{p['id']}/cancelar", json={"motivo": "Cambié de idea"}).status_code == 200
    r = cobrar(t.cliente, p)
    assert r.status_code == 409 and r.json()["code"] == "ORDER_NOT_PENDING"


def test_el_personal_no_registra_a_mano_un_pago_de_mercadopago(tienda, mp):
    t = tienda
    p = pedido_mp(t)
    r = pagar(t.pedidos, p)
    assert r.status_code == 422 and r.json()["code"] == "PAYMENT_METHOD_NOT_MANUAL"


def test_datos_de_tarjeta_invalidos(tienda, mp):
    t = tienda
    p = pedido_mp(t)
    for extra in ({"token": ""}, {"email": "no-es-un-mail"}, {"installments": 0}):
        assert cobrar(t.cliente, p, **extra).status_code == 422
    assert mp.cobros == []


def test_sin_credenciales_cobrar_es_503(tienda):
    t = tienda  # sin la fixture mp: no hay pasarela
    r = t.cliente.post(f"{PAGOS}/mercadopago", json=tarjeta({"id": 1}))
    assert r.status_code == 503 and r.json()["code"] == "MP_NOT_CONFIGURED"


# --- webhook (CE-B4) ----------------------------------------------------------------------------------------


def test_el_webhook_confirma_el_pedido_pendiente(tienda, mp, client):
    t = tienda
    mp.proximo = ("in_process", "pending_contingency")
    p = pedido_mp(t)
    cobrar(t.cliente, p)
    pago_id = max(mp.pagos)
    mp.cambiar(pago_id, "approved", "accredited")
    r = avisar(client, pago_id)
    assert r.status_code == 200 and r.json() == {"resultado": "confirmada"}
    assert estado(t.cliente, p["id"]) == "CONFIRMADO"
    assert pago_de(t.cliente, p["id"])["mp_status"] == "approved"
    ultimo = t.cliente.get(f"{API}/pedidos/{p['id']}/historial").json()[-1]
    assert ultimo["usuario_id"] is None and "MercadoPago" in ultimo["motivo"]  # lo hizo el sistema


def test_el_webhook_repetido_es_idempotente(tienda, mp, client):
    t = tienda
    mp.proximo = ("in_process", None)
    p = pedido_mp(t)
    cobrar(t.cliente, p)
    pago_id = max(mp.pagos)
    mp.cambiar(pago_id, "approved", "accredited")
    resultados = [avisar(client, pago_id).json()["resultado"] for _ in range(3)]
    assert resultados == ["confirmada", "sin_cambios", "sin_cambios"]
    historial = t.cliente.get(f"{API}/pedidos/{p['id']}/historial").json()
    assert [h["estado_hasta"] for h in historial] == ["PENDIENTE", "CONFIRMADO"]  # una sola confirmación


def test_el_webhook_de_un_pedido_ya_confirmado_responde_200_sin_efectos(tienda, mp, client):
    t = tienda
    p = pedido_mp(t)
    cobrar(t.cliente, p)  # approved: ya CONFIRMADO
    r = avisar(client, max(mp.pagos))
    assert r.status_code == 200 and r.json() == {"resultado": "sin_cambios"}
    assert estado(t.cliente, p["id"]) == "CONFIRMADO"


def test_el_webhook_de_un_rechazo_no_confirma(tienda, mp, client):
    t = tienda
    mp.proximo = ("in_process", None)
    p = pedido_mp(t)
    cobrar(t.cliente, p)
    pago_id = max(mp.pagos)
    mp.cambiar(pago_id, "rejected", "cc_rejected_other_reason")
    assert avisar(client, pago_id).json() == {"resultado": "actualizada"}
    assert estado(t.cliente, p["id"]) == "PENDIENTE"
    assert pago_de(t.cliente, p["id"])["mp_status_detail"] == "cc_rejected_other_reason"
    # y el cliente puede reintentar con otra tarjeta
    mp.proximo = ("approved", "accredited")
    assert cobrar(t.cliente, p).status_code == 201 and estado(t.cliente, p["id"]) == "CONFIRMADO"


def test_aviso_de_un_intento_viejo_no_pisa_al_reintento(tienda, mp, client):
    t = tienda
    mp.proximo = ("rejected", "cc_rejected_other_reason")
    p = pedido_mp(t)
    cobrar(t.cliente, p)
    viejo = max(mp.pagos)
    mp.proximo = ("in_process", None)
    cobrar(t.cliente, p)
    nuevo = max(mp.pagos)
    mp.cambiar(viejo, "approved")  # un aviso tardío del primer intento
    assert avisar(client, viejo).json() == {"resultado": "ignorada"}
    assert estado(t.cliente, p["id"]) == "PENDIENTE" and pago_de(t.cliente, p["id"])["mp_status"] == "in_process"
    assert nuevo != viejo


def test_un_pago_aprobado_de_un_pedido_cancelado_no_lo_revive(tienda, mp, client):
    t = tienda
    mp.proximo = ("in_process", None)
    p = pedido_mp(t)
    cobrar(t.cliente, p)
    assert t.cliente.post(f"{API}/pedidos/{p['id']}/cancelar", json={"motivo": "Cambié de idea"}).status_code == 200
    pago_id = max(mp.pagos)
    mp.cambiar(pago_id, "approved", "accredited")
    assert avisar(client, pago_id).json() == {"resultado": "actualizada"}
    assert estado(t.cliente, p["id"]) == "CANCELADO"  # queda registrado el cobro, pero hay que reembolsarlo a mano


def test_webhook_sin_firma_o_con_firma_falsa_es_401(tienda, mp, client):
    t = tienda
    mp.proximo = ("in_process", None)
    p = pedido_mp(t)
    cobrar(t.cliente, p)
    pago_id = max(mp.pagos)
    mp.cambiar(pago_id, "approved")
    for h in ({}, {"x-signature": "ts=1,v1=00"}, firmar(str(pago_id), secreto="otro-secreto"), firmar("999")):
        r = avisar(client, pago_id, headers=h)
        assert r.status_code == 401 and r.json()["code"] == "INVALID_SIGNATURE"
    assert estado(t.cliente, p["id"]) == "PENDIENTE"  # nada se aplicó


def test_webhook_ignora_tipos_y_pagos_desconocidos(tienda, mp, client):
    assert avisar(client, 77, tipo="merchant_order").json() == {"resultado": "ignorada"}
    assert avisar(client, 424242).json() == {"resultado": "ignorada"}  # pago que MercadoPago no conoce
    assert avisar(client, "no-numerico").json() == {"resultado": "ignorada"}


def test_webhook_con_cuerpo_invalido_no_rompe(mp, client):
    r = client.post(f"{PAGOS}/webhook", content=b"no es json", headers={"content-type": "application/json"})
    assert r.status_code == 401  # sin firma


def test_webhook_sin_credenciales_es_503(client):
    r = client.post(f"{PAGOS}/webhook", json={})
    assert r.status_code == 503


# --- firma y adaptador --------------------------------------------------------------------------------------


def test_firma_valida_acepta_la_correcta_y_rechaza_alteraciones():
    h = firmar("12345")
    assert firma_valida(SECRETO, h["x-signature"], h["x-request-id"], "12345")
    assert not firma_valida(SECRETO, h["x-signature"], h["x-request-id"], "12346")  # otro pago
    assert not firma_valida(SECRETO, h["x-signature"], "otro-request", "12345")
    assert not firma_valida("otro", h["x-signature"], h["x-request-id"], "12345")
    assert not firma_valida(SECRETO, None, h["x-request-id"], "12345")
    assert not firma_valida("", h["x-signature"], h["x-request-id"], "12345")  # sin secreto no se acepta nada
    assert not firma_valida(SECRETO, "ts=1700000000000", h["x-request-id"], "12345")  # falta v1


def test_firma_se_calcula_sin_las_partes_ausentes():
    ts = "1700000000000"
    v1 = hmac.new(SECRETO.encode(), f"ts:{ts};".encode(), hashlib.sha256).hexdigest()
    assert firma_valida(SECRETO, f"ts={ts},v1={v1}", None, None)


class SdkFalso:
    """Imita `mercadopago.SDK().payment()` devolviendo la respuesta configurada."""

    def __init__(self, respuesta=None, error: Exception | None = None):
        self.respuesta, self.error, self.cuerpo, self.opciones = respuesta, error, None, None

    def payment(self):
        return self

    def create(self, cuerpo, opciones=None):
        self.cuerpo, self.opciones = cuerpo, opciones
        if self.error:
            raise self.error
        return self.respuesta

    def get(self, payment_id, opciones=None):
        if self.error:
            raise self.error
        return self.respuesta


def adaptador(sdk: SdkFalso) -> MercadoPagoPasarela:
    a = MercadoPagoPasarela("TEST-token", "https://ejemplo.test/api/v1/pagos/webhook")
    a._sdk = sdk
    return a


def un_cobro(**extra) -> CobroConTarjeta:
    base = dict(
        token="tok", monto=D("9500.00"), descripcion="pedido", metodo_de_pago="visa", cuotas=1,
        email="a@b.com", emisor="24", identificacion_tipo="DNI", identificacion_numero="12345678",
        external_reference="ref-1", idempotency_key="clave-1",
    )  # fmt: skip
    return CobroConTarjeta(**{**base, **extra})


def test_el_adaptador_arma_el_cuerpo_y_manda_la_clave_de_idempotencia():
    sdk = SdkFalso({"status": 201, "response": {"id": 9, "status": "approved", "status_detail": "accredited",
                                                 "external_reference": "ref-1"}})  # fmt: skip
    pago = adaptador(sdk).crear_pago(un_cobro())
    assert pago == PagoMP(9, "approved", "accredited", "ref-1")
    c = sdk.cuerpo
    assert c["transaction_amount"] == 9500.0 and c["token"] == "tok" and c["external_reference"] == "ref-1"
    assert c["payer"] == {"email": "a@b.com", "identification": {"type": "DNI", "number": "12345678"}}
    assert c["issuer_id"] == "24" and c["notification_url"].endswith("/pagos/webhook")
    assert sdk.opciones.custom_headers["x-idempotency-key"] == "clave-1"


def test_el_adaptador_omite_lo_opcional():
    sdk = SdkFalso({"status": 201, "response": {"id": 1, "status": "pending"}})
    adaptador(sdk).crear_pago(un_cobro(emisor=None, identificacion_tipo=None, identificacion_numero=None))
    assert "issuer_id" not in sdk.cuerpo and sdk.cuerpo["payer"] == {"email": "a@b.com"}


def test_el_adaptador_traduce_los_errores_de_la_pasarela():
    with pytest.raises(ValidationError) as e:
        adaptador(SdkFalso({"status": 400, "response": {"message": "invalid token"}})).crear_pago(un_cobro())
    assert e.value.code == "MP_REQUEST_REJECTED" and "invalid token" in e.value.detail
    with pytest.raises(BadGatewayError):
        adaptador(SdkFalso({"status": 503, "response": {}})).crear_pago(un_cobro())
    with pytest.raises(BadGatewayError):
        adaptador(SdkFalso(error=TimeoutError())).crear_pago(un_cobro())


def test_el_adaptador_consulta_un_pago():
    ok = {"status": 200, "response": {"id": 7, "status": "approved", "external_reference": "r"}}
    assert adaptador(SdkFalso(ok)).obtener_pago(7) == PagoMP(7, "approved", None, "r")
    assert adaptador(SdkFalso({"status": 404, "response": {}})).obtener_pago(7) is None
    with pytest.raises(BadGatewayError):
        adaptador(SdkFalso({"status": 500, "response": {}})).obtener_pago(7)
    with pytest.raises(BadGatewayError):
        adaptador(SdkFalso(error=ConnectionError())).obtener_pago(7)
