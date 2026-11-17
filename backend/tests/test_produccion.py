"""Producción (sección 8.3): planificar, iniciar, completar y cancelar órdenes con sus movimientos."""

from collections import Counter
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.fsm import ORDEN_TRANSICIONES
from tests.helpers import API, login_admin
from tests.test_catalogo import cliente_con_rol, ingrediente, producto
from tests.test_inventario import D, en_dias, mover, stock

PRODUCCION = f"{API}/produccion"


def pizzeria(client: TestClient) -> dict[str, int]:
    """El ejemplo 8.4: pizza = 0,300 KG de harina + 0,250 KG de queso + 1 caja. Stock inicial 10 / 5 / 50."""
    ids = {
        "harina": ingrediente(client, "Harina")["id"],
        "queso": ingrediente(client, "Queso")["id"],
        "caja": ingrediente(client, "Caja")["id"],
        "pizza": producto(client, "Pizza muzzarella")["id"],
    }
    receta = [
        {"ingrediente_id": ids["harina"], "cantidad_requerida": "0.300", "unidad_medida": "KG"},
        {"ingrediente_id": ids["queso"], "cantidad_requerida": "0.250", "unidad_medida": "KG"},
        {"ingrediente_id": ids["caja"], "cantidad_requerida": "1", "unidad_medida": "UN"},
    ]
    assert client.put(f"{API}/productos/{ids['pizza']}/ingredientes", json={"items": receta}).status_code == 200
    for clave, cantidad in (("harina", "10"), ("queso", "5"), ("caja", "50")):
        assert mover(client, "ingredientes", ids[clave], "ENTRADA", cantidad).status_code == 201
    return ids


def estado_insumos(client: TestClient, ids: dict[str, int]) -> dict[str, tuple[Decimal, Decimal]]:
    return {k: stock(client, "ingredientes", ids[k]) for k in ("harina", "queso", "caja")}


def orden(client: TestClient, cantidad: str = "10", **destino) -> dict:
    r = client.post(PRODUCCION, json={"cantidad_a_producir": cantidad, **destino})
    assert r.status_code == 201, r.text
    return r.json()


def accion(client: TestClient, orden_id: int, nombre: str, **body):
    return client.patch(f"{PRODUCCION}/{orden_id}/{nombre}", json=body or None)


def movimientos_de_orden(client: TestClient, ids: dict[str, int], orden_id: int) -> list[tuple[str, str]]:
    """(insumo, tipo) de los movimientos con orden_produccion_id = orden_id."""
    resultado = []
    for nombre in ("harina", "queso", "caja"):
        items = client.get(f"{API}/ingredientes/{ids[nombre]}/movimientos", params={"size": 100}).json()["items"]
        resultado += [(nombre, m["tipo_movimiento"]) for m in items if m["orden_produccion_id"] == orden_id]
    return resultado


# ----------------------------------------------------------------------------------------------
# Prueba de aceptación: el ejemplo de la sección 8.4
# ----------------------------------------------------------------------------------------------


def test_ejemplo_10_pizzas_muzzarella(client):
    login_admin(client)
    ids = pizzeria(client)
    assert estado_insumos(client, ids) == {"harina": (10, 10), "queso": (5, 5), "caja": (50, 50)}

    o = orden(client, producto_id=ids["pizza"])
    assert o["estado"] == "PLANIFICADA" and o["nombre"] == "Pizza muzzarella"
    assert {c["nombre"]: D(c["cantidad"]) for c in o["componentes"]} == {"Harina": 3, "Queso": D("2.5"), "Caja": 10}
    # tras planificar: el real no se toca, el disponible baja
    assert estado_insumos(client, ids) == {"harina": (10, 7), "queso": (5, D("2.5")), "caja": (50, 40)}

    assert accion(client, o["id"], "iniciar").json()["estado"] == "EN_PROCESO"
    assert estado_insumos(client, ids) == {
        "harina": (10, 7),
        "queso": (5, D("2.5")),
        "caja": (50, 40),
    }  # iniciar no mueve

    assert accion(client, o["id"], "completar").json()["estado"] == "COMPLETADA"
    assert estado_insumos(client, ids) == {"harina": (7, 7), "queso": (D("2.5"), D("2.5")), "caja": (40, 40)}
    assert stock(client, "productos", ids["pizza"]) == (10, 10)  # entró el producto terminado

    # 7 movimientos: 3 liberaciones + 3 salidas de insumos (+ la entrada del producto), más las 3 reservas
    de_la_orden = Counter(tipo for _, tipo in movimientos_de_orden(client, ids, o["id"]))
    assert de_la_orden == {"RESERVA": 3, "LIBERACION_RESERVA": 3, "SALIDA": 3}
    entradas = [m for m in client.get(f"{API}/productos/{ids['pizza']}/movimientos").json()["items"]]
    assert [(m["tipo_movimiento"], m["orden_produccion_id"]) for m in entradas] == [("ENTRADA", o["id"])]


# ----------------------------------------------------------------------------------------------
# Planificar
# ----------------------------------------------------------------------------------------------


def test_planificar_sin_stock_alcanza_da_409_y_no_deja_nada(client):
    login_admin(client)
    ids = pizzeria(client)
    # 25 pizzas necesitan 7,5 KG de harina (hay 10) y 6,25 KG de queso (hay 5)
    r = client.post(PRODUCCION, json={"producto_id": ids["pizza"], "cantidad_a_producir": "25"})
    assert r.status_code == 409 and r.json()["code"] == "INSUFFICIENT_STOCK" and "Queso" in r.json()["detail"]
    assert estado_insumos(client, ids) == {"harina": (10, 10), "queso": (5, 5), "caja": (50, 50)}
    assert client.get(PRODUCCION).json()["total"] == 0  # ni la orden ni las reservas quedaron


def test_dos_ordenes_no_pueden_reservar_el_mismo_insumo(client):
    login_admin(client)
    ids = pizzeria(client)
    orden(client, "15", producto_id=ids["pizza"])  # 3,75 KG de queso de los 5
    r = client.post(PRODUCCION, json={"producto_id": ids["pizza"], "cantidad_a_producir": "10"})  # necesita 2,5
    assert r.status_code == 409  # queda 1,25 disponible aunque el real sea 5
    assert stock(client, "ingredientes", ids["queso"]) == (5, D("1.25"))


def test_validaciones_de_alta(client):
    login_admin(client)
    ids = pizzeria(client)
    cantidad = {"cantidad_a_producir": "1"}
    # exactamente uno de producto_id / ingrediente_id
    assert client.post(PRODUCCION, json=cantidad).status_code == 422
    assert client.post(PRODUCCION, json={**cantidad, "producto_id": 1, "ingrediente_id": 1}).status_code == 422
    for malo in ("0", "-2", "1.2345"):
        assert (
            client.post(PRODUCCION, json={"producto_id": ids["pizza"], "cantidad_a_producir": malo}).status_code == 422
        )

    assert client.post(PRODUCCION, json={**cantidad, "producto_id": 999999}).status_code == 404
    assert client.post(PRODUCCION, json={**cantidad, "ingrediente_id": 999999}).status_code == 404

    sin_receta = producto(client, "Agua")["id"]
    r = client.post(PRODUCCION, json={**cantidad, "producto_id": sin_receta})
    assert r.status_code == 422 and r.json()["code"] == "NO_RECIPE"

    r = client.post(PRODUCCION, json={**cantidad, "ingrediente_id": ids["harina"]})  # no es elaborado
    assert r.status_code == 422 and r.json()["code"] == "INGREDIENT_NOT_ELABORATED"


def test_las_cantidades_se_redondean_hacia_arriba_a_la_milesima(client):
    login_admin(client)
    sal = ingrediente(client, "Sal")["id"]
    p = producto(client, "Pan")["id"]
    client.put(
        f"{API}/productos/{p}/ingredientes",
        json={"items": [{"ingrediente_id": sal, "cantidad_requerida": "0.333", "unidad_medida": "KG"}]},
    )
    mover(client, "ingredientes", sal, "ENTRADA", "10")
    o = orden(client, "0.5", producto_id=p)  # 0,333 × 0,5 = 0,1665 → 0,167: nunca se reserva de menos
    assert D(o["componentes"][0]["cantidad"]) == D("0.167")


# ----------------------------------------------------------------------------------------------
# Cancelar y máquina de estados
# ----------------------------------------------------------------------------------------------


def test_cancelar_libera_las_reservas_y_exige_motivo(client):
    login_admin(client)
    ids = pizzeria(client)
    o = orden(client, producto_id=ids["pizza"])
    assert accion(client, o["id"], "cancelar").status_code == 422  # sin motivo
    assert accion(client, o["id"], "cancelar", motivo="   ").status_code == 422
    assert estado_insumos(client, ids)["harina"] == (10, 7)

    r = accion(client, o["id"], "cancelar", motivo="Se rompió el horno")
    assert r.status_code == 200 and r.json()["estado"] == "CANCELADA"
    assert r.json()["motivo_cancelacion"] == "Se rompió el horno"
    assert estado_insumos(client, ids) == {
        "harina": (10, 10),
        "queso": (5, 5),
        "caja": (50, 50),
    }  # el real nunca se tocó
    assert Counter(t for _, t in movimientos_de_orden(client, ids, o["id"])) == {"RESERVA": 3, "LIBERACION_RESERVA": 3}
    assert stock(client, "productos", ids["pizza"]) == (0, 0)


def test_tambien_se_cancela_una_orden_en_proceso(client):
    login_admin(client)
    ids = pizzeria(client)
    o = orden(client, producto_id=ids["pizza"])
    accion(client, o["id"], "iniciar")
    assert accion(client, o["id"], "cancelar", motivo="Cambio de menú").json()["estado"] == "CANCELADA"
    assert estado_insumos(client, ids)["caja"] == (50, 50)


def test_transiciones_invalidas_dan_409(client):
    login_admin(client)
    ids = pizzeria(client)
    nueva = orden(client, "1", producto_id=ids["pizza"])["id"]
    assert accion(client, nueva, "completar").json()["code"] == "INVALID_TRANSITION"  # PLANIFICADA no se completa

    accion(client, nueva, "iniciar")
    assert accion(client, nueva, "iniciar").json()["code"] == "INVALID_TRANSITION"  # ya está en proceso
    accion(client, nueva, "completar")
    # COMPLETADA y CANCELADA son terminales
    for nombre, body in (("iniciar", {}), ("completar", {}), ("cancelar", {"motivo": "x"})):
        r = accion(client, nueva, nombre, **body)
        assert r.status_code == 409 and r.json()["code"] == "TERMINAL_STATE", nombre

    cancelada = orden(client, "1", producto_id=ids["pizza"])["id"]
    accion(client, cancelada, "cancelar", motivo="x")
    assert accion(client, cancelada, "iniciar").json()["code"] == "TERMINAL_STATE"
    # una orden terminada no vuelve a mover stock
    assert estado_insumos(client, ids)["harina"] == (D("9.7"), D("9.7"))


def test_el_mapa_de_transiciones_de_la_orden():
    assert set(ORDEN_TRANSICIONES["PLANIFICADA"]) == {"EN_PROCESO", "CANCELADA"}
    assert set(ORDEN_TRANSICIONES["EN_PROCESO"]) == {"COMPLETADA", "CANCELADA"}
    assert ORDEN_TRANSICIONES["COMPLETADA"] == {} and ORDEN_TRANSICIONES["CANCELADA"] == {}


# ----------------------------------------------------------------------------------------------
# Completar: lotes, sub-ensambles y recetas que cambian
# ----------------------------------------------------------------------------------------------


def test_completar_con_lote_crea_el_lote_del_producto_terminado(client):
    login_admin(client)
    ids = pizzeria(client)
    o = orden(client, "4", producto_id=ids["pizza"])
    accion(client, o["id"], "iniciar")
    r = accion(client, o["id"], "completar", codigo_lote="PZ-01", fecha_vencimiento=en_dias(3))
    assert r.status_code == 200
    lotes = client.get(f"{API}/productos/{ids['pizza']}/lotes").json()
    assert [(x["codigo_lote"], D(x["stock_real"])) for x in lotes] == [("PZ-01", 4)]


def test_lote_incompleto_o_en_un_ingrediente_se_rechaza_sin_tocar_nada(client):
    login_admin(client)
    ids = pizzeria(client)
    o = orden(client, "4", producto_id=ids["pizza"])
    accion(client, o["id"], "iniciar")
    assert accion(client, o["id"], "completar", codigo_lote="X").json()["code"] == "LOTE_INCOMPLETE"
    vencido = accion(client, o["id"], "completar", codigo_lote="X", fecha_vencimiento=en_dias(-1))
    assert vencido.status_code == 422 and vencido.json()["code"] == "LOTE_EXPIRED"
    # el rechazo revirtió todo: la orden sigue en proceso y los insumos reservados
    assert client.get(f"{PRODUCCION}/{o['id']}").json()["estado"] == "EN_PROCESO"
    assert estado_insumos(client, ids)["harina"] == (10, D("8.8"))
    assert stock(client, "productos", ids["pizza"]) == (0, 0)
    assert accion(client, o["id"], "completar").status_code == 200  # sin lote, ahora sí


def test_sub_ensamble_primero_la_salsa_y_despues_el_producto(client):
    """Sección 8.4: la orden de un elaborado deja su ENTRADA en MovimientoIngrediente; luego se consume."""
    login_admin(client)
    tomate = ingrediente(client, "Tomate")["id"]
    salsa = ingrediente(client, "Salsa base", es_elaborado=True)["id"]
    pizza = producto(client, "Pizza")["id"]
    client.put(
        f"{API}/ingredientes/{salsa}/receta",
        json={"items": [{"componente_id": tomate, "cantidad_requerida": "2", "unidad_medida": "KG"}]},
    )
    client.put(
        f"{API}/productos/{pizza}/ingredientes",
        json={"items": [{"ingrediente_id": salsa, "cantidad_requerida": "0.5", "unidad_medida": "KG"}]},
    )
    mover(client, "ingredientes", tomate, "ENTRADA", "20")

    # sin salsa en stock no se puede planificar la pizza
    sin_salsa = client.post(PRODUCCION, json={"producto_id": pizza, "cantidad_a_producir": "4"})
    assert sin_salsa.status_code == 409 and "Salsa base" in sin_salsa.json()["detail"]

    o_salsa = orden(client, "5", ingrediente_id=salsa)  # 5 KG de salsa = 10 KG de tomate
    assert o_salsa["ingrediente_id"] == salsa and o_salsa["nombre"] == "Salsa base"
    assert stock(client, "ingredientes", tomate) == (20, 10)
    accion(client, o_salsa["id"], "iniciar")
    assert accion(client, o_salsa["id"], "completar").status_code == 200
    assert stock(client, "ingredientes", tomate) == (10, 10) and stock(client, "ingredientes", salsa) == (5, 5)

    o_pizza = orden(client, "4", producto_id=pizza)  # 4 × 0,5 = 2 KG de salsa
    assert stock(client, "ingredientes", salsa) == (5, 3)
    accion(client, o_pizza["id"], "iniciar")
    accion(client, o_pizza["id"], "completar")
    assert stock(client, "ingredientes", salsa) == (3, 3) and stock(client, "productos", pizza) == (4, 4)

    o_otra = orden(client, "1", ingrediente_id=salsa)["id"]
    assert accion(client, o_otra, "iniciar").status_code == 200
    r = accion(client, o_otra, "completar", codigo_lote="S-1", fecha_vencimiento=en_dias(2))
    assert r.status_code == 422 and r.json()["code"] == "LOTE_ONLY_FOR_PRODUCT"


def test_completar_consume_lo_planificado_aunque_la_receta_cambie(client):
    login_admin(client)
    ids = pizzeria(client)
    o = orden(client, "10", producto_id=ids["pizza"])
    accion(client, o["id"], "iniciar")
    nueva = [{"ingrediente_id": ids["harina"], "cantidad_requerida": "1", "unidad_medida": "KG"}]
    client.put(f"{API}/productos/{ids['pizza']}/ingredientes", json={"items": nueva})
    accion(client, o["id"], "completar")
    assert estado_insumos(client, ids) == {"harina": (7, 7), "queso": (D("2.5"), D("2.5")), "caja": (40, 40)}


# ----------------------------------------------------------------------------------------------
# Listado, detalle y permisos
# ----------------------------------------------------------------------------------------------


def test_listado_filtra_por_estado_y_va_de_la_mas_reciente_a_la_mas_antigua(client):
    login_admin(client)
    ids = pizzeria(client)
    a = orden(client, "1", producto_id=ids["pizza"])["id"]
    b = orden(client, "1", producto_id=ids["pizza"])["id"]
    accion(client, a, "iniciar")

    todas = client.get(PRODUCCION).json()
    assert [o["id"] for o in todas["items"]] == [b, a] and todas["total"] == 2
    assert all(o["componentes"] == [] for o in todas["items"])  # el listado no carga el detalle
    en_proceso = client.get(PRODUCCION, params={"estado": "EN_PROCESO"}).json()
    assert [o["id"] for o in en_proceso["items"]] == [a]
    assert client.get(PRODUCCION, params={"estado": "NO_EXISTE"}).status_code == 422
    assert client.get(f"{PRODUCCION}/999999").status_code == 404
    assert accion(client, 999999, "iniciar").status_code == 404


def test_produccion_es_solo_para_admin_y_stock(client):
    login_admin(client)
    ids = pizzeria(client)
    o = orden(client, "1", producto_id=ids["pizza"])["id"]
    cliente = cliente_con_rol(client, "CLIENT", "c@foodstore.com")
    pedidos = cliente_con_rol(client, "PEDIDOS", "p@foodstore.com")
    anonimo = TestClient(client.app)
    for otro in (cliente, pedidos):
        assert otro.get(PRODUCCION).status_code == 403
        assert otro.post(PRODUCCION, json={"producto_id": ids["pizza"], "cantidad_a_producir": "1"}).status_code == 403
        assert otro.patch(f"{PRODUCCION}/{o}/iniciar").status_code == 403
    assert anonimo.get(PRODUCCION).status_code == 401

    stock_user = cliente_con_rol(client, "STOCK", "s@foodstore.com")
    assert stock_user.patch(f"{PRODUCCION}/{o}/iniciar").status_code == 200
