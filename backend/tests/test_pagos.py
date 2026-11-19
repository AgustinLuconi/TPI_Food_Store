"""Pagos (secciones 6.6 y 9.4): registro manual idempotente que confirma el pedido en la misma transacción."""

import uuid

from fastapi.testclient import TestClient

from app.modules.pedidos.uow import PedidosUnitOfWork
from tests.helpers import API, registrar_y_loguear
from tests.pedidos_helpers import crear_pedido, estado, linea, pagar, pedido_ok
from tests.test_inventario import D

PEDIDOS = f"{API}/pedidos"


def test_registrar_el_pago_confirma_el_pedido(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza)])
    r = pagar(t.pedidos, p)
    assert r.status_code == 201, r.text
    pago = r.json()
    assert pago["mp_status"] == "approved" and pago["forma_pago_codigo"] == "EFECTIVO" and D(pago["monto"]) == 9500
    assert pago["external_reference"] == p["external_reference"] and pago["pedido_id"] == p["id"]

    detalle = t.cliente.get(f"{PEDIDOS}/{p['id']}").json()
    assert detalle["estado_codigo"] == "CONFIRMADO" and detalle["pago"]["id"] == pago["id"]
    ultimo = detalle["historial"][-1]
    assert (ultimo["estado_desde"], ultimo["estado_hasta"]) == ("PENDIENTE", "CONFIRMADO")
    assert ultimo["usuario_id"] != detalle["usuario_id"]  # lo confirmó el personal que cobró


def test_el_pago_usa_la_forma_de_pago_del_pedido(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.empanada)], forma_pago_codigo="TRANSFERENCIA")
    assert pagar(t.admin, p).json()["forma_pago_codigo"] == "TRANSFERENCIA"


def test_idempotencia_la_misma_clave_devuelve_el_mismo_pago(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza)])
    clave = str(uuid.uuid4())
    primero, repetido = pagar(t.pedidos, p, clave=clave), pagar(t.pedidos, p, clave=clave)
    assert (primero.status_code, repetido.status_code) == (201, 200)
    assert repetido.json()["id"] == primero.json()["id"]
    historial = t.cliente.get(f"{PEDIDOS}/{p['id']}/historial").json()
    assert [h["estado_hasta"] for h in historial] == ["PENDIENTE", "CONFIRMADO"]  # no se confirmó dos veces


def test_un_segundo_pago_para_el_mismo_pedido_es_409(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza)])
    assert pagar(t.pedidos, p).status_code == 201
    r = pagar(t.pedidos, p)  # otra clave: es otro intento de pago
    assert r.status_code == 409 and r.json()["code"] == "PAYMENT_ALREADY_REGISTERED"
    assert t.cliente.get(f"{API}/pagos/{p['id']}").json()["monto"] == p["total"]


def test_una_clave_usada_en_otro_pedido_es_409(tienda):
    t = tienda
    a, b = pedido_ok(t.cliente, [linea(t.empanada)]), pedido_ok(t.cliente, [linea(t.empanada)])
    clave = str(uuid.uuid4())
    assert pagar(t.pedidos, a, clave=clave).status_code == 201
    r = pagar(t.pedidos, b, clave=clave)
    assert r.status_code == 409 and r.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert estado(t.cliente, b["id"]) == "PENDIENTE"


def test_el_monto_debe_coincidir_con_el_total(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza)])  # 9.500
    for monto in ("9499.99", "9500.01", "0", "19000"):
        r = pagar(t.pedidos, p, monto=monto)
        assert r.status_code == 422 and r.json()["code"] == "AMOUNT_MISMATCH", monto
    for malo in ("-1", "abc", "9500.123"):
        assert pagar(t.pedidos, p, monto=malo).status_code == 422, malo
    assert estado(t.cliente, p["id"]) == "PENDIENTE" and t.cliente.get(f"{API}/pagos/{p['id']}").status_code == 404
    assert pagar(t.pedidos, p, monto="9500").status_code == 201  # sin decimales también vale

    con_envio = pedido_ok(t.cliente, [linea(t.pizza)], direccion_id=t.dentro)  # el total incluye el envío
    assert pagar(t.pedidos, con_envio, monto="9500").json()["code"] == "AMOUNT_MISMATCH"
    assert pagar(t.pedidos, con_envio).status_code == 201


def test_solo_se_paga_un_pedido_pendiente(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza)])
    t.cliente.post(f"{PEDIDOS}/{p['id']}/cancelar", json={"motivo": "Ya no lo quiero"})
    r = pagar(t.pedidos, p)
    assert r.status_code == 409 and r.json()["code"] == "ORDER_NOT_PENDING"
    assert estado(t.cliente, p["id"]) == "CANCELADO"


def test_mercadopago_no_se_registra_a_mano(tienda, uow_factory):
    t = tienda
    uow = uow_factory(PedidosUnitOfWork)
    with uow:  # se habilita solo para este test (el seed la deja apagada hasta el Anexo B)
        uow.formas_pago.update(uow.formas_pago.get_by_id("MERCADOPAGO"), {"habilitado": True})
    p = pedido_ok(t.cliente, [linea(t.pizza)], forma_pago_codigo="MERCADOPAGO")
    r = pagar(t.pedidos, p)
    assert r.status_code == 422 and r.json()["code"] == "PAYMENT_METHOD_NOT_MANUAL"
    assert estado(t.cliente, p["id"]) == "PENDIENTE"


def test_la_clave_de_idempotencia_es_obligatoria(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza)])
    sin = t.pedidos.post(f"{API}/pagos/{p['id']}", json={"monto": p["total"]})
    assert sin.status_code == 422 and sin.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    mala = t.pedidos.post(f"{API}/pagos/{p['id']}", json={"monto": p["total"]}, headers={"Idempotency-Key": "abc"})
    assert mala.json()["code"] == "INVALID_IDEMPOTENCY_KEY"
    assert (
        t.pedidos.post(f"{API}/pagos/{p['id']}", json={}, headers={"Idempotency-Key": str(uuid.uuid4())}).status_code
        == 422
    )


def test_permisos_de_los_pagos(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza)])
    clave = {"Idempotency-Key": str(uuid.uuid4())}
    cuerpo = {"monto": p["total"]}
    assert t.cliente.post(f"{API}/pagos/{p['id']}", json=cuerpo, headers=clave).status_code == 403  # no se autopaga
    assert t.stock.post(f"{API}/pagos/{p['id']}", json=cuerpo, headers=clave).status_code == 403
    assert TestClient(t.cliente.app).post(f"{API}/pagos/{p['id']}", json=cuerpo, headers=clave).status_code == 401
    assert t.pedidos.post(f"{API}/pagos/999999", json=cuerpo, headers=clave).status_code == 404

    assert pagar(t.admin, p).status_code == 201  # ADMIN también puede registrarlo


def test_consultar_el_pago(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza)])
    assert t.cliente.get(f"{API}/pagos/{p['id']}").json()["code"] == "PAYMENT_NOT_FOUND"  # todavía no hay
    pagar(t.pedidos, p)
    for quien in (t.cliente, t.pedidos, t.admin):
        assert quien.get(f"{API}/pagos/{p['id']}").status_code == 200

    otro = TestClient(t.cliente.app)
    registrar_y_loguear(otro, "otro@test.com")
    assert otro.get(f"{API}/pagos/{p['id']}").status_code == 404  # ajeno: no se revela
    assert t.stock.get(f"{API}/pagos/{p['id']}").status_code == 404
    assert TestClient(t.cliente.app).get(f"{API}/pagos/{p['id']}").status_code == 401
    assert t.cliente.get(f"{API}/pagos/999999").status_code == 404


def test_el_pago_no_confirma_si_el_pedido_no_existe_ni_deja_registros_sueltos(tienda):
    t = tienda
    assert pagar(t.pedidos, {"id": 999999, "total": "1"}).status_code == 404
    p = pedido_ok(t.cliente, [linea(t.pizza)])
    pagar(t.pedidos, p, monto="1")  # rechazado
    assert crear_pedido(t.cliente, [linea(t.empanada)]).status_code == 201  # la sesión sigue sana
    assert t.cliente.get(f"{API}/pagos/{p['id']}").status_code == 404


def test_formas_de_pago_habilitadas(tienda, uow_factory):
    t = tienda
    # el seed deja MercadoPago deshabilitada hasta el Anexo B
    assert [f["codigo"] for f in t.cliente.get(f"{API}/pagos/formas").json()] == ["EFECTIVO", "TRANSFERENCIA"]
    assert t.cliente.get(f"{API}/pagos/formas").json()[0] == {"codigo": "EFECTIVO", "nombre": "Efectivo"}
    assert TestClient(t.cliente.app).get(f"{API}/pagos/formas").status_code == 401

    uow = uow_factory(PedidosUnitOfWork)
    with uow:
        uow.formas_pago.update(uow.formas_pago.get_by_id("MERCADOPAGO"), {"habilitado": True})
    assert [f["codigo"] for f in t.cliente.get(f"{API}/pagos/formas").json()] == [
        "EFECTIVO",
        "MERCADOPAGO",
        "TRANSFERENCIA",
    ]
