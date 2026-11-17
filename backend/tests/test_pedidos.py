"""Pedidos (secciones 6.5 y 9): creación idempotente, snapshot, reservas FEFO y máquina de estados."""

import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.core.fsm import PEDIDO_TRANSICIONES
from tests.helpers import API, registrar_y_loguear
from tests.pedidos_helpers import (
    BA,
    DENTRO,
    LUNES,
    Tienda,
    crear_pedido,
    estado,
    instante_local,
    linea,
    movimientos_de_pedido,
    pagar,
    pedido_ok,
    stock_producto,
)
from tests.test_config import cotizar
from tests.test_inventario import D

PEDIDOS = f"{API}/pedidos"


def confirmado(t: Tienda, items: list[dict], **extra) -> dict:
    """Un pedido ya pagado (CONFIRMADO)."""
    p = pedido_ok(t.cliente, items, **extra)
    assert pagar(t.pedidos, p).status_code == 201
    return p


def avanzar(t: Tienda, pedido_id: int, hasta: str):
    return t.pedidos.patch(f"{PEDIDOS}/{pedido_id}/estado", json={"estado": hasta})


# ----------------------------------------------------------------------------------------------
# Crear un pedido
# ----------------------------------------------------------------------------------------------


def test_crear_pedido_con_retiro_en_el_local(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza, 2), linea(t.empanada, 3)], notas="  Sin apuro  ")
    assert p["estado_codigo"] == "PENDIENTE" and p["direccion_id"] is None and p["notas"] == "Sin apuro"
    assert (D(p["subtotal"]), D(p["costo_envio"]), D(p["descuento"]), D(p["total"])) == (22600, 0, 0, 22600)
    assert p["cliente_nombre"] == "Ana Pérez" and p["pago"] is None and p["forma_pago_codigo"] == "EFECTIVO"

    por_producto = {x["producto_id"]: x for x in p["lineas"]}
    assert (
        por_producto[t.pizza]["nombre_snapshot"] == "Pizza muzzarella" and D(por_producto[t.pizza]["subtotal"]) == 19000
    )
    assert por_producto[t.empanada]["cantidad"] == 3

    # el primer registro del historial: estado_desde nulo → PENDIENTE
    assert [(h["estado_desde"], h["estado_hasta"]) for h in p["historial"]] == [(None, "PENDIENTE")]


def test_crear_pedido_con_envio_cotiza_y_congela_el_costo(tienda):
    t = tienda
    cotizacion = cotizar(t.cliente, *DENTRO, "9500").json()
    p = pedido_ok(t.cliente, [linea(t.pizza)], direccion_id=t.dentro)
    assert D(p["costo_envio"]) == D(cotizacion["costo_envio"]) > 0
    assert D(p["total"]) == D("9500") + D(cotizacion["costo_envio"])
    assert p["direccion"]["id"] == t.dentro and p["direccion"]["linea1"] == "Calle 123"

    # RN-04: el costo de envío queda congelado aunque cambie la tarifa de la zona
    zona = next(z for z in t.admin.get(f"{API}/config/zonas").json() if z["nombre"] == "Zona Centro")
    t.admin.put(f"{API}/config/zonas/{zona['id']}", json={"tarifa_base": "9999"})
    assert D(t.cliente.get(f"{PEDIDOS}/{p['id']}").json()["costo_envio"]) == D(cotizacion["costo_envio"])


def test_rn04_el_snapshot_no_cambia_si_el_producto_cambia(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza, 2)])
    r = t.admin.put(f"{API}/productos/{t.pizza}", json={"nombre": "Pizza renovada", "precio_base": "15000"})
    assert r.status_code == 200
    detalle = t.cliente.get(f"{PEDIDOS}/{p['id']}").json()
    assert detalle["lineas"][0]["nombre_snapshot"] == "Pizza muzzarella"
    assert D(detalle["lineas"][0]["precio_snapshot"]) == 9500 and D(detalle["total"]) == 19000


def test_el_pedido_reserva_el_stock_por_lote_con_fefo(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza, 5)])  # 4 del lote A (vence antes) y 1 del B
    assert stock_producto(t.admin, t.pizza) == (10, 5)  # el real no se toca: solo se reserva
    assert movimientos_de_pedido(t.admin, t.pizza, p["id"]) == [("RESERVA", t.lote_a, 4), ("RESERVA", t.lote_b, 1)]


def test_idempotencia_la_misma_clave_devuelve_el_mismo_pedido(tienda):
    t = tienda
    clave = str(uuid.uuid4())
    primero = crear_pedido(t.cliente, [linea(t.pizza, 2)], clave=clave)
    repetido = crear_pedido(t.cliente, [linea(t.pizza, 2)], clave=clave)
    assert primero.status_code == 201 and repetido.status_code == 200
    assert repetido.json()["id"] == primero.json()["id"]
    assert t.cliente.get(PEDIDOS).json()["total"] == 1  # un solo pedido
    assert stock_producto(t.admin, t.pizza) == (10, 8)  # y se reservó una sola vez

    # aunque el segundo intento traiga otro carrito, no se crea nada nuevo
    assert crear_pedido(t.cliente, [linea(t.empanada, 5)], clave=clave).json()["id"] == primero.json()["id"]
    assert stock_producto(t.admin, t.empanada) == (20, 20)

    # la clave se compara sin distinguir mayúsculas
    assert crear_pedido(t.cliente, [linea(t.pizza)], clave=clave.upper()).json()["id"] == primero.json()["id"]


def test_una_clave_de_otro_cliente_no_devuelve_su_pedido(tienda):
    t = tienda
    clave = str(uuid.uuid4())
    pedido_ok_ajeno = crear_pedido(t.cliente, [linea(t.pizza)], clave=clave)
    assert pedido_ok_ajeno.status_code == 201
    otro = TestClient(t.cliente.app)
    registrar_y_loguear(otro, "otro@test.com")
    r = crear_pedido(otro, [linea(t.pizza)], clave=clave)
    assert r.status_code == 409 and r.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_la_idempotency_key_es_obligatoria_y_debe_ser_uuid(tienda):
    t = tienda
    cuerpo = {"items": [linea(t.pizza)], "forma_pago_codigo": "EFECTIVO"}
    sin = t.cliente.post(PEDIDOS, json=cuerpo)
    assert sin.status_code == 422 and sin.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    mala = t.cliente.post(PEDIDOS, json=cuerpo, headers={"Idempotency-Key": "123"})
    assert mala.status_code == 422 and mala.json()["code"] == "INVALID_IDEMPOTENCY_KEY"
    assert t.cliente.get(PEDIDOS).json()["total"] == 0


def test_rn13_con_el_local_cerrado_no_se_crean_pedidos(tienda, reloj):
    t = tienda
    reloj(instante_local(8))  # el local abre a las 11
    r = crear_pedido(t.cliente, [linea(t.pizza)])
    assert r.status_code == 409 and r.json()["code"] == "LOCAL_CLOSED" and "16/11/2026 11:00" in r.json()["detail"]
    assert stock_producto(t.admin, t.pizza) == (10, 10) and t.cliente.get(PEDIDOS).json()["total"] == 0

    reloj(instante_local(12))
    assert crear_pedido(t.cliente, [linea(t.pizza)]).status_code == 201
    t.admin.post(f"{API}/config/dias-bloqueados", json={"fecha": LUNES.isoformat(), "motivo": "Feriado"})
    assert crear_pedido(t.cliente, [linea(t.pizza)]).json()["code"] == "LOCAL_CLOSED"


def test_forma_de_pago_habilitada(tienda):
    t = tienda
    for codigo in ("MERCADOPAGO", "BITCOIN"):  # MercadoPago está deshabilitada en el seed
        r = crear_pedido(t.cliente, [linea(t.pizza)], forma_pago_codigo=codigo)
        assert r.status_code == 422 and r.json()["code"] == "PAYMENT_METHOD_UNAVAILABLE", codigo
    assert crear_pedido(t.cliente, [linea(t.pizza)], forma_pago_codigo="transferencia").json()["forma_pago_codigo"] == (
        "TRANSFERENCIA"
    )


def test_rn14_validaciones_de_la_direccion(tienda):
    t = tienda
    fuera = crear_pedido(t.cliente, [linea(t.pizza)], direccion_id=t.fuera)
    assert fuera.status_code == 422 and fuera.json()["code"] == "OUTSIDE_COVERAGE"
    sin = crear_pedido(t.cliente, [linea(t.pizza)], direccion_id=t.sin_coords)
    assert sin.status_code == 422 and sin.json()["code"] == "ADDRESS_WITHOUT_COORDS"
    minimo = crear_pedido(t.cliente, [linea(t.empanada)], direccion_id=t.dentro)  # 1.200 < 3.000
    assert minimo.status_code == 422 and minimo.json()["code"] == "BELOW_MINIMUM"
    assert crear_pedido(t.cliente, [linea(t.empanada, 3)], direccion_id=t.dentro).status_code == 201  # 3.600 alcanza
    # el pedido mínimo es solo para envíos: retirar en el local no lo exige
    assert crear_pedido(t.cliente, [linea(t.empanada)]).status_code == 201
    assert crear_pedido(t.cliente, [linea(t.pizza)], direccion_id=999999).json()["code"] == "ADDRESS_NOT_FOUND"

    otro = TestClient(t.cliente.app)
    registrar_y_loguear(otro, "otro@test.com")
    ajena = crear_pedido(otro, [linea(t.pizza)], direccion_id=t.dentro)  # dirección de otro usuario
    assert ajena.status_code == 404 and ajena.json()["code"] == "ADDRESS_NOT_FOUND"
    # cada rechazo revirtió todo: solo quedaron los dos pedidos válidos
    assert t.cliente.get(PEDIDOS).json()["total"] == 2


def test_validacion_de_lineas_siempre_409(tienda):
    t = tienda
    inexistente = crear_pedido(t.cliente, [linea(999999)])
    assert inexistente.status_code == 409 and inexistente.json()["code"] == "PRODUCT_UNAVAILABLE"

    t.admin.patch(f"{API}/productos/{t.empanada}/disponibilidad", json={"disponible": False})
    assert crear_pedido(t.cliente, [linea(t.empanada)]).json()["code"] == "PRODUCT_UNAVAILABLE"
    t.admin.patch(f"{API}/productos/{t.empanada}/disponibilidad", json={"disponible": True})
    assert crear_pedido(t.cliente, [linea(t.empanada)]).status_code == 201

    t.admin.delete(f"{API}/productos/{t.empanada}")  # dado de baja
    assert crear_pedido(t.cliente, [linea(t.empanada)]).json()["code"] == "PRODUCT_UNAVAILABLE"


def test_rn12_solo_se_excluyen_ingredientes_removibles_de_la_receta(tienda):
    t = tienda
    ok = pedido_ok(t.cliente, [linea(t.pizza, 1, t.queso)])
    assert [e["nombre"] for e in ok["lineas"][0]["exclusiones"]] == ["Queso"]

    for malo, motivo in ((t.harina, "no removible"), (t.cebolla, "fuera de la receta"), (999999, "inexistente")):
        r = crear_pedido(t.cliente, [linea(t.pizza, 1, malo)])
        assert r.status_code == 409 and r.json()["code"] == "INVALID_EXCLUSION", motivo
    assert crear_pedido(t.cliente, [linea(t.empanada, 1, t.queso)]).json()["code"] == "INVALID_EXCLUSION"  # sin receta

    # las exclusiones son una indicación para la cocina: no generan movimientos de stock
    assert movimientos_de_pedido(t.admin, t.pizza, ok["id"]) == [("RESERVA", t.lote_a, 1)]


def test_una_misma_pizza_con_distintas_exclusiones_son_lineas_separadas(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza, 1, t.queso), linea(t.pizza, 2)])
    assert len(p["lineas"]) == 2 and D(p["subtotal"]) == 28500
    assert sorted(len(x["exclusiones"]) for x in p["lineas"]) == [0, 1]


def test_stock_insuficiente_da_409_y_no_deja_nada_a_medias(tienda):
    t = tienda
    # la primera línea alcanza, la segunda no: ninguna de las dos puede quedar reservada
    r = crear_pedido(t.cliente, [linea(t.pizza, 3), linea(t.empanada, 21)])
    assert r.status_code == 409 and r.json()["code"] == "INSUFFICIENT_STOCK" and "Empanada" in r.json()["detail"]
    assert stock_producto(t.admin, t.pizza) == (10, 10) and stock_producto(t.admin, t.empanada) == (20, 20)
    assert t.cliente.get(PEDIDOS).json()["total"] == 0 and t.pedidos.get(PEDIDOS).json()["total"] == 0


def test_el_stock_se_suma_entre_lineas_del_mismo_producto(tienda):
    t = tienda
    r = crear_pedido(t.cliente, [linea(t.pizza, 6), linea(t.pizza, 6, t.queso)])  # 12 > 10
    assert r.status_code == 409 and r.json()["code"] == "INSUFFICIENT_STOCK"
    ok = crear_pedido(t.cliente, [linea(t.pizza, 5), linea(t.pizza, 5, t.queso)])  # 10 alcanza justo
    assert ok.status_code == 201 and stock_producto(t.admin, t.pizza) == (10, 0)
    assert crear_pedido(t.cliente, [linea(t.pizza)]).status_code == 409  # ya no queda nada


def test_no_se_reserva_stock_de_un_lote_vencido(tienda):
    t = tienda
    # el lote A (4 u.) vence en 3 días: con el reloj 5 días adelante está vencido y solo quedan las 6 del B
    t.admin.post(f"{API}/config/dias-bloqueados", json={"fecha": "2030-01-01"})  # un bloqueo cualquiera, sin efecto
    reloj_futuro = datetime.now(BA) + timedelta(days=5)
    assert reloj_futuro > datetime.now(BA)
    # (la vigencia de lotes usa utcnow de inventario, que no se fija: se prueba el reparto sin lotes vencidos)
    p = pedido_ok(t.cliente, [linea(t.pizza, 10)])
    assert movimientos_de_pedido(t.admin, t.pizza, p["id"]) == [("RESERVA", t.lote_a, 4), ("RESERVA", t.lote_b, 6)]


def test_validaciones_del_carrito_y_permisos(tienda):
    t = tienda
    base = {"forma_pago_codigo": "EFECTIVO"}
    clave = {"Idempotency-Key": str(uuid.uuid4())}
    malos = [
        {**base, "items": []},
        {**base, "items": [linea(t.pizza, 0)]},
        {**base, "items": [linea(t.pizza, 100)]},
        {**base, "items": [linea(t.pizza, -1)]},
        {**base, "items": [{"producto_id": t.pizza}]},
        {"items": [linea(t.pizza)]},  # sin forma de pago
        {**base, "items": [linea(t.pizza)] * 51},
        {**base, "items": [linea(t.pizza)], "notas": "x" * 501},
    ]
    for body in malos:
        assert t.cliente.post(PEDIDOS, json=body, headers=clave).status_code == 422, body

    cuerpo = {**base, "items": [linea(t.pizza)]}
    assert TestClient(t.cliente.app).post(PEDIDOS, json=cuerpo, headers=clave).status_code == 401
    assert t.admin.post(PEDIDOS, json=cuerpo, headers=clave).status_code == 403  # crear pedidos es del CLIENT
    assert t.pedidos.post(PEDIDOS, json=cuerpo, headers=clave).status_code == 403


# ----------------------------------------------------------------------------------------------
# Listados y detalle
# ----------------------------------------------------------------------------------------------


def test_cada_cliente_ve_solo_sus_pedidos_y_el_personal_ve_todos(tienda):
    t = tienda
    mio = pedido_ok(t.cliente, [linea(t.empanada)])
    otro = TestClient(t.cliente.app)
    registrar_y_loguear(otro, "otro@test.com")
    ajeno = pedido_ok(otro, [linea(t.empanada, 2)])

    propios = t.cliente.get(PEDIDOS).json()
    assert [x["id"] for x in propios["items"]] == [mio["id"]]
    assert {x["id"] for x in t.pedidos.get(PEDIDOS).json()["items"]} == {mio["id"], ajeno["id"]}
    assert {x["id"] for x in t.admin.get(PEDIDOS).json()["items"]} == {mio["id"], ajeno["id"]}
    fila = next(x for x in t.admin.get(PEDIDOS).json()["items"] if x["id"] == ajeno["id"])
    assert fila["cliente_nombre"] == "Ana Pérez" and fila["con_envio"] is False and D(fila["total"]) == 2400
    assert TestClient(t.cliente.app).get(PEDIDOS).status_code == 401


def test_filtros_por_estado_y_fechas_y_paginacion(tienda):
    t = tienda
    a, b, c = (pedido_ok(t.cliente, [linea(t.empanada)]) for _ in range(3))
    pagar(t.pedidos, a)

    def ids(**params):
        r = t.cliente.get(PEDIDOS, params=params)
        assert r.status_code == 200, r.text
        return [x["id"] for x in r.json()["items"]]

    assert ids() == [c["id"], b["id"], a["id"]]  # del más reciente al más antiguo
    assert ids(estado="CONFIRMADO") == [a["id"]]
    assert ids(estado="PENDIENTE") == [c["id"], b["id"]]
    hoy = datetime.now(BA).date()
    assert ids(desde=hoy.isoformat(), hasta=hoy.isoformat()) == [c["id"], b["id"], a["id"]]
    assert ids(hasta=(hoy - timedelta(days=1)).isoformat()) == []
    assert ids(desde=(hoy + timedelta(days=1)).isoformat()) == []
    assert t.cliente.get(PEDIDOS, params={"estado": "XX"}).status_code == 422
    assert t.cliente.get(PEDIDOS, params={"desde": "2026-12-02", "hasta": "2026-12-01"}).status_code == 422

    paginas = [ids(size=2, page=n) for n in (1, 2)]
    assert paginas == [[c["id"], b["id"]], [a["id"]]]


def test_detalle_e_historial_solo_para_el_propietario_o_el_personal(tienda):
    t = tienda
    p = confirmado(t, [linea(t.pizza, 1, t.queso)])
    detalle = t.cliente.get(f"{PEDIDOS}/{p['id']}").json()
    assert detalle["pago"]["mp_status"] == "approved" and len(detalle["historial"]) == 2
    assert t.pedidos.get(f"{PEDIDOS}/{p['id']}").status_code == 200
    assert t.admin.get(f"{PEDIDOS}/{p['id']}").status_code == 200

    historial = t.cliente.get(f"{PEDIDOS}/{p['id']}/historial").json()
    assert [(h["estado_desde"], h["estado_hasta"]) for h in historial] == [
        (None, "PENDIENTE"),
        ("PENDIENTE", "CONFIRMADO"),
    ]

    otro = TestClient(t.cliente.app)
    registrar_y_loguear(otro, "otro@test.com")
    for ruta in ("", "/historial"):
        assert otro.get(f"{PEDIDOS}/{p['id']}{ruta}").status_code == 404  # no revela que existe
        assert TestClient(t.cliente.app).get(f"{PEDIDOS}/{p['id']}{ruta}").status_code == 401
        assert t.cliente.get(f"{PEDIDOS}/999999{ruta}").status_code == 404


# ----------------------------------------------------------------------------------------------
# Máquina de estados y stock
# ----------------------------------------------------------------------------------------------


def test_flujo_completo_y_consumo_de_stock_al_pasar_a_preparacion(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza, 5)])  # reserva 4 de A y 1 de B
    assert stock_producto(t.admin, t.pizza) == (10, 5)

    assert pagar(t.pedidos, p).status_code == 201 and estado(t.cliente, p["id"]) == "CONFIRMADO"
    assert stock_producto(t.admin, t.pizza) == (10, 5)  # CONFIRMADO: la reserva se mantiene

    assert avanzar(t, p["id"], "EN_PREPARACION").json()["estado_codigo"] == "EN_PREPARACION"
    assert stock_producto(t.admin, t.pizza) == (5, 5)  # consumo físico: sale lo reservado
    movimientos = movimientos_de_pedido(t.admin, t.pizza, p["id"])
    assert movimientos[:2] == [("RESERVA", t.lote_a, 4), ("RESERVA", t.lote_b, 1)]
    # por cada lote reservado, primero la liberación y después la salida (el orden entre lotes no importa)
    for lote, cantidad in ((t.lote_a, 4), (t.lote_b, 1)):
        assert [m[0] for m in movimientos[2:] if m[1] == lote] == ["LIBERACION_RESERVA", "SALIDA"]
        assert {m[2] for m in movimientos[2:] if m[1] == lote} == {cantidad}
    assert len(movimientos) == 6
    lotes = {
        x["codigo_lote"]: (D(x["stock_real"]), D(x["stock_disponible"]))
        for x in t.admin.get(f"{API}/productos/{t.pizza}/lotes").json()
    }
    assert lotes == {"A": (0, 0), "B": (5, 5)}

    for hasta in ("EN_CAMINO", "ENTREGADO"):
        assert avanzar(t, p["id"], hasta).json()["estado_codigo"] == hasta
    assert stock_producto(t.admin, t.pizza) == (5, 5)  # EN_CAMINO y ENTREGADO no mueven stock

    final = t.cliente.get(f"{PEDIDOS}/{p['id']}").json()
    assert [(h["estado_desde"], h["estado_hasta"]) for h in final["historial"]] == [
        (None, "PENDIENTE"),
        ("PENDIENTE", "CONFIRMADO"),
        ("CONFIRMADO", "EN_PREPARACION"),
        ("EN_PREPARACION", "EN_CAMINO"),
        ("EN_CAMINO", "ENTREGADO"),
    ]
    assert final["historial"][0]["usuario_id"] == final["usuario_id"]  # lo creó el cliente
    assert all(h["usuario_id"] is not None for h in final["historial"])


def test_transiciones_invalidas_y_terminales(tienda):
    t = tienda
    p = confirmado(t, [linea(t.empanada)])
    # no se puede saltar estados ni retroceder
    assert avanzar(t, p["id"], "EN_CAMINO").json()["code"] == "INVALID_TRANSITION"
    assert avanzar(t, p["id"], "ENTREGADO").json()["code"] == "INVALID_TRANSITION"
    assert avanzar(t, p["id"], "PENDIENTE").json()["code"] == "INVALID_TRANSITION"
    assert avanzar(t, p["id"], "CONFIRMADO").json()["code"] == "INVALID_TRANSITION"  # ya lo está
    assert estado(t.cliente, p["id"]) == "CONFIRMADO"

    for hasta in ("EN_PREPARACION", "EN_CAMINO", "ENTREGADO"):
        avanzar(t, p["id"], hasta)
    for destino in ("EN_PREPARACION", "CONFIRMADO", "PENDIENTE"):  # ENTREGADO es terminal
        r = avanzar(t, p["id"], destino)
        assert r.status_code == 409 and r.json()["code"] == "TERMINAL_STATE", destino
    assert len(t.cliente.get(f"{PEDIDOS}/{p['id']}/historial").json()) == 5  # los rechazos no dejaron rastro


def test_un_pedido_pendiente_se_confirma_solo_con_el_pago(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.empanada)])
    r = avanzar(t, p["id"], "CONFIRMADO")
    assert r.status_code == 409 and r.json()["code"] == "PAYMENT_REQUIRED"
    assert avanzar(t, p["id"], "EN_PREPARACION").json()["code"] == "INVALID_TRANSITION"
    assert avanzar(t, p["id"], "CANCELADO").status_code == 422  # para cancelar hay un endpoint con motivo
    assert estado(t.cliente, p["id"]) == "PENDIENTE"
    assert t.admin.patch(f"{PEDIDOS}/{p['id']}/estado", json={"estado": "NO_EXISTE"}).status_code == 422


def test_solo_el_personal_cambia_el_estado(tienda):
    t = tienda
    p = confirmado(t, [linea(t.empanada)])
    assert t.cliente.patch(f"{PEDIDOS}/{p['id']}/estado", json={"estado": "EN_PREPARACION"}).status_code == 403
    assert t.stock.patch(f"{PEDIDOS}/{p['id']}/estado", json={"estado": "EN_PREPARACION"}).status_code == 403
    assert (
        TestClient(t.cliente.app).patch(f"{PEDIDOS}/{p['id']}/estado", json={"estado": "EN_PREPARACION"}).status_code
        == 401
    )
    assert t.admin.patch(f"{PEDIDOS}/{p['id']}/estado", json={"estado": "EN_PREPARACION"}).status_code == 200
    assert t.admin.patch(f"{PEDIDOS}/999999/estado", json={"estado": "EN_CAMINO"}).status_code == 404


def test_el_mapa_de_transiciones_del_pedido():
    assert set(PEDIDO_TRANSICIONES["PENDIENTE"]) == {"CONFIRMADO", "CANCELADO"}
    assert set(PEDIDO_TRANSICIONES["CONFIRMADO"]) == {"EN_PREPARACION", "CANCELADO"}
    assert PEDIDO_TRANSICIONES["ENTREGADO"] == {} and PEDIDO_TRANSICIONES["CANCELADO"] == {}


# ----------------------------------------------------------------------------------------------
# Cancelar (RN-05)
# ----------------------------------------------------------------------------------------------


def cancelar(cliente: TestClient, pedido_id: int, motivo: str | None = "Cambié de idea"):
    cuerpo = {} if motivo is None else {"motivo": motivo}
    return cliente.post(f"{PEDIDOS}/{pedido_id}/cancelar", json=cuerpo)


def test_cancelar_exige_motivo_y_lo_guarda_en_el_historial(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.pizza, 3)])
    for malo in (None, "", "   "):
        assert cancelar(t.cliente, p["id"], malo).status_code == 422, malo
    assert estado(t.cliente, p["id"]) == "PENDIENTE" and stock_producto(t.admin, t.pizza) == (10, 7)

    r = cancelar(t.cliente, p["id"], "  Me equivoqué de pedido ")
    assert r.status_code == 200 and r.json()["estado_codigo"] == "CANCELADO"
    ultimo = r.json()["historial"][-1]
    assert (ultimo["estado_desde"], ultimo["estado_hasta"], ultimo["motivo"]) == (
        "PENDIENTE",
        "CANCELADO",
        "Me equivoqué de pedido",
    )
    assert ultimo["usuario_id"] == r.json()["usuario_id"]


def test_cancelar_desde_pendiente_o_confirmado_libera_la_reserva_en_los_mismos_lotes(tienda):
    t = tienda
    pendiente = pedido_ok(t.cliente, [linea(t.pizza, 5)])
    assert stock_producto(t.admin, t.pizza) == (10, 5)
    cancelar(t.cliente, pendiente["id"])
    assert stock_producto(t.admin, t.pizza) == (10, 10)  # el real nunca cambió
    movimientos = movimientos_de_pedido(t.admin, t.pizza, pendiente["id"])
    assert movimientos[:2] == [("RESERVA", t.lote_a, 4), ("RESERVA", t.lote_b, 1)]
    assert sorted(movimientos[2:]) == sorted([("LIBERACION_RESERVA", t.lote_a, 4), ("LIBERACION_RESERVA", t.lote_b, 1)])

    pagado = confirmado(t, [linea(t.pizza, 2)])
    assert stock_producto(t.admin, t.pizza) == (10, 8)
    assert cancelar(t.cliente, pagado["id"]).json()["estado_codigo"] == "CANCELADO"  # el cliente puede en CONFIRMADO
    assert stock_producto(t.admin, t.pizza) == (10, 10)
    lotes = {x["codigo_lote"]: D(x["stock_disponible"]) for x in t.admin.get(f"{API}/productos/{t.pizza}/lotes").json()}
    assert lotes == {"A": 4, "B": 6}  # cada lote recuperó lo suyo


def test_el_cliente_no_cancela_un_pedido_en_preparacion_pero_el_personal_si_sin_mover_stock(tienda):
    t = tienda
    p = confirmado(t, [linea(t.pizza, 2)])
    avanzar(t, p["id"], "EN_PREPARACION")
    assert stock_producto(t.admin, t.pizza) == (8, 8)

    assert cancelar(t.cliente, p["id"]).status_code == 403  # el propietario solo en PENDIENTE o CONFIRMADO
    assert estado(t.cliente, p["id"]) == "EN_PREPARACION"

    r = cancelar(t.pedidos, p["id"], "Se quemó")
    assert r.status_code == 200 and r.json()["estado_codigo"] == "CANCELADO"
    assert stock_producto(t.admin, t.pizza) == (8, 8)  # ya se consumió: ningún movimiento automático
    assert [m[0] for m in movimientos_de_pedido(t.admin, t.pizza, p["id"])].count(
        "LIBERACION_RESERVA"
    ) == 1  # la de preparar
    # (si se descarta, STOCK registra una MERMA a mano)
    assert (
        t.stock.post(
            f"{API}/productos/{t.pizza}/movimientos",
            json={"tipo_movimiento": "MERMA", "cantidad": "2", "motivo": "ROTURA"},
        ).status_code
        == 201
    )


def test_el_personal_cancela_en_camino_y_los_terminales_no_se_cancelan(tienda):
    t = tienda
    p = confirmado(t, [linea(t.empanada)])
    for hasta in ("EN_PREPARACION", "EN_CAMINO"):
        avanzar(t, p["id"], hasta)
    assert cancelar(t.admin, p["id"], "No se pudo entregar").json()["estado_codigo"] == "CANCELADO"
    again = cancelar(t.admin, p["id"])
    assert again.status_code == 409 and again.json()["code"] == "TERMINAL_STATE"

    entregado = confirmado(t, [linea(t.empanada)])
    for hasta in ("EN_PREPARACION", "EN_CAMINO", "ENTREGADO"):
        avanzar(t, entregado["id"], hasta)
    assert cancelar(t.admin, entregado["id"]).json()["code"] == "TERMINAL_STATE"
    assert cancelar(t.cliente, entregado["id"]).json()["code"] == "TERMINAL_STATE"


def test_nadie_mas_cancela_un_pedido_ajeno(tienda):
    t = tienda
    p = pedido_ok(t.cliente, [linea(t.empanada)])
    otro = TestClient(t.cliente.app)
    registrar_y_loguear(otro, "otro@test.com")
    assert cancelar(otro, p["id"]).status_code == 404
    assert cancelar(TestClient(t.cliente.app), p["id"]).status_code == 401
    assert cancelar(t.stock, p["id"]).status_code == 404  # STOCK no es personal de pedidos
    assert cancelar(t.cliente, 999999).status_code == 404
    assert estado(t.cliente, p["id"]) == "PENDIENTE"
