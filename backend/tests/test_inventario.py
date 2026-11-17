"""Inventario (sección 8): doble ledger, stock derivado, lotes y FEFO (RN-06 a RN-09)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.repository import AppendOnlyRepository
from app.modules.inventario import service
from app.modules.inventario.repository import MovimientoIngredienteRepository, MovimientoStockRepository
from app.modules.inventario.stock import (
    SIGNO_DISPONIBLE,
    SIGNO_REAL,
    TIPOS_MANUALES,
    LoteDisponible,
    repartir_fefo,
)
from app.modules.inventario.uow import InventarioUnitOfWork
from app.modules.productos.models import Lote, MovimientoStock, TipoMovimiento
from tests.helpers import API, login_admin, registrar_y_loguear
from tests.test_catalogo import cliente_con_rol, ingrediente, producto

D = Decimal


def en_dias(dias: float) -> str:
    return (datetime.now(UTC) + timedelta(days=dias)).isoformat()


def mover(client: TestClient, recurso: str, rid: int, tipo: str, cantidad: str, **extra):
    return client.post(
        f"{API}/{recurso}/{rid}/movimientos", json={"tipo_movimiento": tipo, "cantidad": cantidad, **extra}
    )


def stock(client: TestClient, recurso: str, rid: int) -> tuple[Decimal, Decimal]:
    r = client.get(f"{API}/{recurso}/{rid}/stock")
    assert r.status_code == 200, r.text
    return D(r.json()["stock_real"]), D(r.json()["stock_disponible"])


def lote_vencido(uow_factory, producto_id: int, codigo: str, cantidad: str, dias_atras: int = 3) -> int:
    """Un lote ya vencido con su ENTRADA (la API no deja ingresarlo así: se prepara por el UoW)."""
    uow = uow_factory(InventarioUnitOfWork)
    with uow:
        lote = uow.lotes.create(
            Lote(
                producto_id=producto_id,
                codigo_lote=codigo,
                fecha_vencimiento=datetime.now(UTC) - timedelta(days=dias_atras),
                cantidad_inicial=D(cantidad),
            )
        )
        uow.mov_productos.create(
            MovimientoStock(
                producto_id=producto_id, lote_id=lote.id, tipo_movimiento=TipoMovimiento.ENTRADA, cantidad=D(cantidad)
            )
        )
        return lote.id  # type: ignore[return-value]


def reservar(uow_factory, producto_id: int, cantidad: str, tipo=TipoMovimiento.RESERVA):
    """Un movimiento del sistema (lo que harán pedidos y producción)."""
    uow = uow_factory(InventarioUnitOfWork)
    with uow:
        return service.consumir_producto(uow, producto_id, D(cantidad), tipo, pedido_id=None)


# ----------------------------------------------------------------------------------------------
# Reglas puras
# ----------------------------------------------------------------------------------------------


def test_signos_segun_la_spec():
    assert SIGNO_REAL == {"ENTRADA": 1, "AJUSTE_POSITIVO": 1, "SALIDA": -1, "MERMA": -1, "AJUSTE_NEGATIVO": -1}
    assert SIGNO_DISPONIBLE == {**SIGNO_REAL, "RESERVA": -1, "LIBERACION_RESERVA": 1}
    assert TIPOS_MANUALES == {"ENTRADA", "MERMA", "AJUSTE_POSITIVO", "AJUSTE_NEGATIVO"}


def test_repartir_fefo_toma_primero_el_que_vence_antes():
    ahora = datetime.now(UTC)
    tarde = LoteDisponible(1, ahora + timedelta(days=9), D(10))
    pronto = LoteDisponible(2, ahora + timedelta(days=2), D(4))

    plan, faltante = repartir_fefo([tarde, pronto], D(6))
    assert plan == [(2, D(4)), (1, D(2))] and faltante == 0

    plan, faltante = repartir_fefo([tarde, pronto], D(20))  # no alcanza: devuelve lo que falta
    assert plan == [(2, D(4)), (1, D(10))] and faltante == 6
    assert repartir_fefo([], D(3)) == ([], D(3))
    assert repartir_fefo([LoteDisponible(3, ahora, D(0))], D(1)) == ([], D(1))


def test_el_ledger_es_append_only():
    for repo in (MovimientoStockRepository, MovimientoIngredienteRepository):
        assert issubclass(repo, AppendOnlyRepository)
        for prohibido in ("update", "delete", "soft_delete", "hard_delete", "restore"):
            assert not hasattr(repo, prohibido)


# ----------------------------------------------------------------------------------------------
# Permisos
# ----------------------------------------------------------------------------------------------


def test_el_inventario_exige_admin_o_stock(client):
    login_admin(client)
    p, i = producto(client)["id"], ingrediente(client, "Harina")["id"]
    rutas = [
        ("get", f"/productos/{p}/stock"),
        ("get", f"/productos/{p}/movimientos"),
        ("get", f"/productos/{p}/lotes"),
        ("get", f"/ingredientes/{i}/stock"),
        ("get", f"/ingredientes/{i}/movimientos"),
        ("get", "/inventario/por-vencer"),
    ]
    stock_user = cliente_con_rol(client, "STOCK", "stock@foodstore.com")
    cliente_user = cliente_con_rol(client, "CLIENT", "cliente@foodstore.com")
    anonimo = TestClient(client.app)
    for metodo, ruta in rutas:
        assert getattr(stock_user, metodo)(f"{API}{ruta}").status_code == 200, ruta
        assert getattr(cliente_user, metodo)(f"{API}{ruta}").status_code == 403, ruta
        assert getattr(anonimo, metodo)(f"{API}{ruta}").status_code == 401, ruta
    assert mover(cliente_user, "productos", p, "ENTRADA", "1").status_code == 403
    assert mover(stock_user, "productos", p, "ENTRADA", "1").status_code == 201  # STOCK sí puede cargar


# ----------------------------------------------------------------------------------------------
# Stock derivado (RN-06)
# ----------------------------------------------------------------------------------------------


def test_stock_se_deriva_del_ledger(client, uow_factory):
    login_admin(client)
    p = producto(client)["id"]
    assert stock(client, "productos", p) == (0, 0)  # sin movimientos

    assert mover(client, "productos", p, "ENTRADA", "10").status_code == 201
    assert mover(client, "productos", p, "MERMA", "2", motivo="ROTURA").status_code == 201
    assert mover(client, "productos", p, "AJUSTE_POSITIVO", "1.5").status_code == 201
    assert mover(client, "productos", p, "AJUSTE_NEGATIVO", "3").status_code == 201
    assert stock(client, "productos", p) == (D("6.5"), D("6.5"))  # 10 − 2 + 1,5 − 3

    reservar(uow_factory, p, "2")  # una RESERVA del sistema baja solo el disponible
    assert stock(client, "productos", p) == (D("6.5"), D("4.5"))


def test_el_detalle_del_producto_muestra_el_stock_solo_a_la_gestion(client):
    login_admin(client)
    p = producto(client)["id"]
    mover(client, "productos", p, "ENTRADA", "4")

    detalle = client.get(f"{API}/productos/{p}").json()
    assert (D(detalle["stock_real"]), D(detalle["stock_disponible"])) == (4, 4)
    fila = next(x for x in client.get(f"{API}/productos").json()["items"] if x["id"] == p)
    assert D(fila["stock_real"]) == 4

    publico = TestClient(client.app)
    assert publico.get(f"{API}/productos/{p}").json()["stock_real"] is None
    assert publico.get(f"{API}/productos").json()["items"][0]["stock_real"] is None


def test_el_listado_de_ingredientes_incluye_el_stock(client):
    login_admin(client)
    i = ingrediente(client, "Harina")["id"]
    mover(client, "ingredientes", i, "ENTRADA", "7.250")
    fila = next(x for x in client.get(f"{API}/ingredientes").json()["items"] if x["id"] == i)
    assert D(fila["stock_real"]) == D("7.25") and D(fila["stock_disponible"]) == D("7.25")
    assert D(client.get(f"{API}/ingredientes/{i}").json()["stock_real"]) == D("7.25")


# ----------------------------------------------------------------------------------------------
# Movimientos manuales (RN-07, RN-08)
# ----------------------------------------------------------------------------------------------


def test_rn07_solo_cuatro_tipos_se_cargan_a_mano(client):
    login_admin(client)
    p, i = producto(client)["id"], ingrediente(client, "Harina")["id"]
    for tipo in ("SALIDA", "RESERVA", "LIBERACION_RESERVA"):
        for recurso, rid in (("productos", p), ("ingredientes", i)):
            r = mover(client, recurso, rid, tipo, "1")
            assert r.status_code == 422 and r.json()["code"] == "MOVEMENT_NOT_MANUAL", (tipo, recurso)
    assert mover(client, "productos", p, "NO_EXISTE", "1").status_code == 422
    assert client.get(f"{API}/productos/{p}/movimientos").json()["total"] == 0  # nada se registró


def test_rn08_la_merma_exige_un_motivo_valido(client):
    login_admin(client)
    p = producto(client)["id"]
    mover(client, "productos", p, "ENTRADA", "10")
    for extra in ({}, {"motivo": "porque sí"}, {"motivo": "  "}):
        r = mover(client, "productos", p, "MERMA", "1", **extra)
        assert r.status_code == 422 and r.json()["code"] == "MERMA_REASON_REQUIRED", extra
    for motivo in ("VENCIMIENTO", "ROTURA", "CONSUMO_INTERNO", "ERROR_PRODUCCION"):
        assert mover(client, "productos", p, "MERMA", "1", motivo=motivo).status_code == 201
    assert stock(client, "productos", p)[0] == 6


def test_cantidad_siempre_positiva_y_con_tres_decimales(client):
    login_admin(client)
    p = producto(client)["id"]
    for cantidad in ("0", "-1", "1.2345", "abc"):
        assert mover(client, "productos", p, "ENTRADA", cantidad).status_code == 422, cantidad
    assert mover(client, "productos", p, "ENTRADA", "0.001").status_code == 201


def test_no_se_puede_restar_mas_de_lo_disponible_ni_lo_reservado(client, uow_factory):
    login_admin(client)
    p = producto(client)["id"]
    mover(client, "productos", p, "ENTRADA", "10")
    reservar(uow_factory, p, "6")  # real 10, disponible 4

    r = mover(client, "productos", p, "MERMA", "5", motivo="ROTURA")
    assert r.status_code == 409 and r.json()["code"] == "INSUFFICIENT_STOCK"
    assert mover(client, "productos", p, "AJUSTE_NEGATIVO", "5").status_code == 409
    assert mover(client, "productos", p, "MERMA", "4", motivo="ROTURA").status_code == 201
    assert stock(client, "productos", p) == (6, 0)


def test_el_ledger_se_lista_del_mas_reciente_al_mas_antiguo_con_filtro_y_paginas(client):
    login_admin(client)
    p = producto(client)["id"]
    mover(client, "productos", p, "ENTRADA", "10")
    for _ in range(3):
        mover(client, "productos", p, "MERMA", "1", motivo="ROTURA")
    mover(client, "productos", p, "AJUSTE_POSITIVO", "2")

    todos = client.get(f"{API}/productos/{p}/movimientos").json()
    assert todos["total"] == 5
    assert [m["tipo_movimiento"] for m in todos["items"]][0] == "AJUSTE_POSITIVO"
    assert [m["tipo_movimiento"] for m in todos["items"]][-1] == "ENTRADA"

    mermas = client.get(f"{API}/productos/{p}/movimientos", params={"tipo": "MERMA"}).json()
    assert mermas["total"] == 3 and {m["motivo"] for m in mermas["items"]} == {"ROTURA"}

    paginas = [client.get(f"{API}/productos/{p}/movimientos", params={"size": 2, "page": n}).json() for n in (1, 2, 3)]
    vistos = [m["id"] for pg in paginas for m in pg["items"]]
    assert len(vistos) == 5 and len(set(vistos)) == 5  # sin repetidos ni faltantes


def test_producto_inexistente_o_dado_de_baja(client):
    login_admin(client)
    assert client.get(f"{API}/productos/999999/stock").status_code == 404
    assert mover(client, "productos", 999999, "ENTRADA", "1").status_code == 404
    p = producto(client)["id"]
    mover(client, "productos", p, "ENTRADA", "3")
    assert client.delete(f"{API}/productos/{p}").status_code == 204
    assert stock(client, "productos", p)[0] == 3  # se puede consultar para auditar
    assert mover(client, "productos", p, "ENTRADA", "1").status_code == 404  # pero no mover
    assert client.get(f"{API}/ingredientes/999999/stock").status_code == 404


# ----------------------------------------------------------------------------------------------
# Lotes y FEFO (RN-09)
# ----------------------------------------------------------------------------------------------


def test_una_entrada_con_lote_lo_crea(client):
    login_admin(client)
    p = producto(client)["id"]
    r = mover(client, "productos", p, "ENTRADA", "12", codigo_lote="L-001", fecha_vencimiento=en_dias(10))
    assert r.status_code == 201
    lote_id = r.json()[0]["lote_id"]
    assert lote_id is not None

    lotes = client.get(f"{API}/productos/{p}/lotes").json()
    assert len(lotes) == 1
    assert lotes[0]["id"] == lote_id and lotes[0]["codigo_lote"] == "L-001" and lotes[0]["vencido"] is False
    assert D(lotes[0]["cantidad_inicial"]) == 12 and D(lotes[0]["stock_real"]) == 12


def test_reglas_de_alta_de_lote(client):
    login_admin(client)
    p = producto(client)["id"]
    solo_codigo = mover(client, "productos", p, "ENTRADA", "1", codigo_lote="L-1")
    solo_fecha = mover(client, "productos", p, "ENTRADA", "1", fecha_vencimiento=en_dias(5))
    assert solo_codigo.json()["code"] == solo_fecha.json()["code"] == "LOTE_INCOMPLETE"

    en_merma = mover(client, "productos", p, "AJUSTE_POSITIVO", "1", codigo_lote="L-1", fecha_vencimiento=en_dias(5))
    assert en_merma.status_code == 422 and en_merma.json()["code"] == "LOTE_ONLY_IN_ENTRADA"

    vencido = mover(client, "productos", p, "ENTRADA", "1", codigo_lote="L-1", fecha_vencimiento=en_dias(-1))
    assert vencido.status_code == 422 and vencido.json()["code"] == "LOTE_EXPIRED"

    assert (
        mover(client, "productos", p, "ENTRADA", "1", codigo_lote="L-1", fecha_vencimiento=en_dias(5)).status_code
        == 201
    )
    repetido = mover(client, "productos", p, "ENTRADA", "1", codigo_lote="l-1", fecha_vencimiento=en_dias(9))
    assert repetido.status_code == 409 and repetido.json()["code"] == "LOTE_DUPLICATED"
    assert len(client.get(f"{API}/productos/{p}/lotes").json()) == 1  # los rechazados no dejaron nada

    # el mismo código en OTRO producto es válido
    otro = producto(client, "Flan")["id"]
    assert (
        mover(client, "productos", otro, "ENTRADA", "1", codigo_lote="L-1", fecha_vencimiento=en_dias(5)).status_code
        == 201
    )


def test_rn09_la_merma_consume_primero_el_lote_que_vence_antes(client):
    login_admin(client)
    p = producto(client)["id"]
    mover(client, "productos", p, "ENTRADA", "5", codigo_lote="TARDE", fecha_vencimiento=en_dias(20))
    mover(
        client, "productos", p, "ENTRADA", "5", codigo_lote="PRONTO", fecha_vencimiento=en_dias(2)
    )  # se cargó después
    mover(client, "productos", p, "ENTRADA", "3")  # stock sin lote

    r = mover(client, "productos", p, "MERMA", "7", motivo="ROTURA")
    assert r.status_code == 201
    partes = r.json()
    assert [D(m["cantidad"]) for m in partes] == [5, 2]  # un movimiento por lote
    por_codigo = {x["codigo_lote"]: x for x in client.get(f"{API}/productos/{p}/lotes").json()}
    assert D(por_codigo["PRONTO"]["stock_real"]) == 0 and D(por_codigo["TARDE"]["stock_real"]) == 3
    assert [x["codigo_lote"] for x in client.get(f"{API}/productos/{p}/lotes").json()] == ["PRONTO", "TARDE"]

    # lo que los lotes no cubren sale del stock sin lote
    r = mover(client, "productos", p, "MERMA", "5", motivo="ROTURA")
    assert [(m["lote_id"] is None, D(m["cantidad"])) for m in r.json()] == [(False, 3), (True, 2)]
    assert stock(client, "productos", p) == (1, 1)

    assert mover(client, "productos", p, "MERMA", "2", motivo="ROTURA").status_code == 409  # solo queda 1


def test_la_reserva_de_un_lote_lo_deja_sin_disponible_para_el_siguiente_movimiento(client, uow_factory):
    login_admin(client)
    p = producto(client)["id"]
    mover(client, "productos", p, "ENTRADA", "4", codigo_lote="A", fecha_vencimiento=en_dias(3))
    mover(client, "productos", p, "ENTRADA", "4", codigo_lote="B", fecha_vencimiento=en_dias(9))
    reservar(uow_factory, p, "4")  # FEFO: reserva todo el lote A

    por_codigo = {x["codigo_lote"]: x for x in client.get(f"{API}/productos/{p}/lotes").json()}
    assert (D(por_codigo["A"]["stock_real"]), D(por_codigo["A"]["stock_disponible"])) == (4, 0)
    assert (D(por_codigo["B"]["stock_real"]), D(por_codigo["B"]["stock_disponible"])) == (4, 4)

    r = mover(client, "productos", p, "AJUSTE_NEGATIVO", "2")  # sale de B, no de lo reservado en A
    assert [m["lote_id"] for m in r.json()] == [int(por_codigo["B"]["id"])]


def test_los_lotes_vencidos_no_se_venden_pero_se_dan_de_baja_con_merma(client, uow_factory):
    login_admin(client)
    p = producto(client)["id"]
    vencido = lote_vencido(uow_factory, p, "VIEJO", "5")
    mover(client, "productos", p, "ENTRADA", "3", codigo_lote="FRESCO", fecha_vencimiento=en_dias(8))

    lotes = {x["codigo_lote"]: x for x in client.get(f"{API}/productos/{p}/lotes").json()}
    assert lotes["VIEJO"]["vencido"] is True and lotes["FRESCO"]["vencido"] is False

    # una salida (venta) solo puede usar lotes vigentes: 3 sí, 4 no
    assert [D(m.cantidad) for m in reservar(uow_factory, p, "3", TipoMovimiento.SALIDA)] == [3]
    try:
        reservar(uow_factory, p, "1", TipoMovimiento.SALIDA)
    except Exception as e:  # noqa: BLE001
        assert getattr(e, "code", None) == "INSUFFICIENT_STOCK"
    else:
        raise AssertionError("vendió un lote vencido")

    # la MERMA por vencimiento sí los alcanza
    r = mover(client, "productos", p, "MERMA", "5", motivo="VENCIMIENTO")
    assert r.status_code == 201 and [m["lote_id"] for m in r.json()] == [vencido]
    assert stock(client, "productos", p) == (0, 0)


def test_por_vencer_lista_lotes_con_stock_proximos_o_vencidos(client, uow_factory):
    login_admin(client)
    p = producto(client)["id"]
    mover(client, "productos", p, "ENTRADA", "2", codigo_lote="EN-3-DIAS", fecha_vencimiento=en_dias(3))
    mover(client, "productos", p, "ENTRADA", "2", codigo_lote="EN-30-DIAS", fecha_vencimiento=en_dias(30))
    mover(client, "productos", p, "ENTRADA", "2", codigo_lote="AGOTADO", fecha_vencimiento=en_dias(1))
    mover(client, "productos", p, "AJUSTE_NEGATIVO", "2")  # FEFO: consume el que vence antes (AGOTADO)
    lote_vencido(uow_factory, p, "VENCIDO", "1")

    por_vencer = client.get(f"{API}/inventario/por-vencer").json()  # dias=7 por defecto
    assert [x["codigo_lote"] for x in por_vencer] == ["VENCIDO", "EN-3-DIAS"]
    assert por_vencer[0]["vencido"] is True and por_vencer[0]["dias_restantes"] < 0
    assert por_vencer[1]["dias_restantes"] in (2, 3) and por_vencer[1]["producto_nombre"] == "Pizza"

    amplio = client.get(f"{API}/inventario/por-vencer", params={"dias": 60}).json()
    assert [x["codigo_lote"] for x in amplio] == ["VENCIDO", "EN-3-DIAS", "EN-30-DIAS"]
    assert client.get(f"{API}/inventario/por-vencer", params={"dias": -1}).status_code == 422
    assert client.get(f"{API}/inventario/por-vencer", params={"dias": 366}).status_code == 422


# ----------------------------------------------------------------------------------------------
# Ingredientes
# ----------------------------------------------------------------------------------------------


def test_ledger_de_insumos(client):
    login_admin(client)
    i = ingrediente(client, "Harina")["id"]
    assert mover(client, "ingredientes", i, "ENTRADA", "10").status_code == 201
    r = mover(client, "ingredientes", i, "MERMA", "2.5", motivo="CONSUMO_INTERNO")
    assert r.status_code == 201 and D(r.json()["cantidad"]) == D("2.5")
    assert stock(client, "ingredientes", i) == (D("7.5"), D("7.5"))

    sin_motivo = mover(client, "ingredientes", i, "MERMA", "1")
    assert sin_motivo.status_code == 422 and sin_motivo.json()["code"] == "MERMA_REASON_REQUIRED"
    assert mover(client, "ingredientes", i, "SALIDA", "1").json()["code"] == "MOVEMENT_NOT_MANUAL"
    excede = mover(client, "ingredientes", i, "AJUSTE_NEGATIVO", "8")
    assert excede.status_code == 409 and excede.json()["code"] == "INSUFFICIENT_STOCK"

    movimientos = client.get(f"{API}/ingredientes/{i}/movimientos").json()
    assert movimientos["total"] == 2 and movimientos["items"][0]["tipo_movimiento"] == "MERMA"
    assert movimientos["items"][0]["lote_id"] is None  # los insumos no tienen lotes


def test_registrar_movimiento_exige_sesion_valida_de_stock_o_admin(client):
    registrar_y_loguear(client)  # CLIENT
    assert mover(client, "ingredientes", 1, "ENTRADA", "1").status_code == 403
