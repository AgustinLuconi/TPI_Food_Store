"""Métricas del panel (sección 6.8): todo se agrega en la base y cada endpoint valida el rol."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.modules.metricas import service
from app.modules.metricas.fechas import dias_entre, hoy_local, limites_del_dia, limites_del_rango
from app.modules.metricas.uow import MetricasUnitOfWork
from tests.helpers import API
from tests.pedidos_helpers import Tienda, linea, pagar, pedido_ok
from tests.test_inventario import D, mover

M = f"{API}/admin/metrics"
BA = ZoneInfo("America/Argentina/Buenos_Aires")


def vender(t: Tienda) -> dict[str, dict]:
    """Un día de actividad: dos ventas, un pedido pendiente y uno pagado que después se canceló."""
    a = pedido_ok(t.cliente, [linea(t.pizza, 2)])  # 19.000
    b = pedido_ok(t.cliente, [linea(t.empanada, 1)])  # 1.200
    c = pedido_ok(t.cliente, [linea(t.empanada, 1)])  # pendiente
    d = pedido_ok(t.cliente, [linea(t.empanada, 3)])  # 3.600, se paga y se cancela
    for p in (a, b, d):
        assert pagar(t.pedidos, p).status_code == 201
    assert t.cliente.post(f"{API}/pedidos/{d['id']}/cancelar", json={"motivo": "prueba"}).status_code == 200
    return {"a": a, "b": b, "c": c, "d": d}


# ----------------------------------------------------------------------------------------------
# Fechas puras
# ----------------------------------------------------------------------------------------------


def test_los_limites_del_dia_son_los_de_la_zona_del_local():
    inicio, fin = limites_del_dia(date(2026, 11, 17), BA)
    assert inicio.astimezone(ZoneInfo("UTC")).hour == 3 and fin - inicio == timedelta(days=1)  # medianoche = 03:00 UTC
    desde, hasta = limites_del_rango(date(2026, 11, 1), date(2026, 11, 3), BA)
    assert hasta - desde == timedelta(days=3)  # `hasta` es un día inclusivo
    # 01:00 UTC del martes sigue siendo lunes en Buenos Aires
    assert hoy_local(datetime(2026, 11, 17, 1, 0, tzinfo=ZoneInfo("UTC")), BA) == date(2026, 11, 16)
    assert dias_entre(date(2026, 11, 1), date(2026, 11, 3)) == [date(2026, 11, d) for d in (1, 2, 3)]
    assert dias_entre(date(2026, 11, 1), date(2026, 11, 1)) == [date(2026, 11, 1)]


# ----------------------------------------------------------------------------------------------
# Permisos
# ----------------------------------------------------------------------------------------------


def test_cada_metrica_valida_el_rol(tienda):
    t = tienda
    solo_admin = ["/resumen", "/ventas", "/top-productos"]
    admin_o_stock = ["/stock-bajo", "/mermas"]
    anonimo = TestClient(t.cliente.app)
    for ruta in solo_admin + admin_o_stock:
        assert t.admin.get(f"{M}{ruta}").status_code == 200, ruta
        assert t.cliente.get(f"{M}{ruta}").status_code == 403, ruta
        assert t.pedidos.get(f"{M}{ruta}").status_code == 403, ruta
        assert anonimo.get(f"{M}{ruta}").status_code == 401, ruta
    for ruta in solo_admin:
        assert t.stock.get(f"{M}{ruta}").status_code == 403, ruta
    for ruta in admin_o_stock:
        assert t.stock.get(f"{M}{ruta}").status_code == 200, ruta


# ----------------------------------------------------------------------------------------------
# Resumen
# ----------------------------------------------------------------------------------------------


def test_resumen_sin_actividad_viene_en_cero_con_todos_los_estados(tienda):
    r = tienda.admin.get(f"{M}/resumen").json()
    assert (D(r["ventas_del_dia"]), r["pedidos_pagados_del_dia"], D(r["ticket_promedio"]), r["pedidos_del_dia"]) == (
        0,
        0,
        0,
        0,
    )
    assert r["pedidos_por_estado"] == {
        e: 0 for e in ("PENDIENTE", "CONFIRMADO", "EN_PREPARACION", "EN_CAMINO", "ENTREGADO", "CANCELADO")
    }
    assert r["pagos_por_estado"] == {}


def test_resumen_del_dia(tienda):
    t = tienda
    vender(t)
    r = t.admin.get(f"{M}/resumen").json()
    # una venta es un pedido con pago aprobado que NO se canceló: 19.000 + 1.200
    assert D(r["ventas_del_dia"]) == 20200 and r["pedidos_pagados_del_dia"] == 2
    assert D(r["ticket_promedio"]) == 10100
    assert r["pedidos_del_dia"] == 4  # todos los creados hoy, en cualquier estado
    assert r["pedidos_por_estado"] == {
        "PENDIENTE": 1,
        "CONFIRMADO": 2,
        "EN_PREPARACION": 0,
        "EN_CAMINO": 0,
        "ENTREGADO": 0,
        "CANCELADO": 1,
    }
    assert r["pagos_por_estado"] == {"approved": 3}  # incluye el del pedido cancelado: el pago existió
    assert r["fecha"] == datetime.now(BA).date().isoformat()


def test_el_ticket_promedio_se_redondea_a_centavos(tienda):
    t = tienda
    for _ in range(3):
        assert pagar(t.pedidos, pedido_ok(t.cliente, [linea(t.empanada, 1)])).status_code == 201
    assert D(t.admin.get(f"{M}/resumen").json()["ticket_promedio"]) == D("1200.00")


def test_el_dia_se_mide_en_la_zona_del_local(tienda, uow_factory):
    vender(tienda)
    hoy = datetime.now(ZoneInfo("UTC"))
    en_dos_dias = service.resumen(uow_factory(MetricasUnitOfWork), hoy + timedelta(days=2))
    assert en_dos_dias.ventas_del_dia == 0 and en_dos_dias.pedidos_del_dia == 0  # otro día: sin ventas
    ahora = service.resumen(uow_factory(MetricasUnitOfWork), hoy)
    assert ahora.ventas_del_dia == 20200


# ----------------------------------------------------------------------------------------------
# Ventas
# ----------------------------------------------------------------------------------------------


def test_serie_de_ventas_con_los_dias_sin_ventas_en_cero(tienda):
    t = tienda
    vender(t)
    r = t.admin.get(f"{M}/ventas").json()
    assert len(r["serie"]) == 30  # por defecto, los últimos 30 días
    hoy = datetime.now(BA).date()
    assert r["hasta"] == hoy.isoformat() and r["desde"] == (hoy - timedelta(days=29)).isoformat()
    por_dia = {p["fecha"]: p for p in r["serie"]}
    assert D(por_dia[hoy.isoformat()]["total"]) == 20200 and por_dia[hoy.isoformat()]["pedidos"] == 2
    assert all(D(p["total"]) == 0 for p in r["serie"] if p["fecha"] != hoy.isoformat())
    assert D(r["total"]) == 20200 and r["pedidos"] == 2
    assert [p["fecha"] for p in r["serie"]] == sorted(por_dia)  # en orden cronológico


def test_ventas_con_rango_propio_y_validaciones(tienda):
    t = tienda
    vender(t)
    hoy = datetime.now(BA).date()
    r = t.admin.get(f"{M}/ventas", params={"desde": hoy.isoformat(), "hasta": hoy.isoformat()}).json()
    assert len(r["serie"]) == 1 and D(r["total"]) == 20200
    ayer = (hoy - timedelta(days=1)).isoformat()
    pasado = t.admin.get(f"{M}/ventas", params={"desde": ayer, "hasta": ayer}).json()
    assert D(pasado["total"]) == 0 and pasado["pedidos"] == 0

    invertido = t.admin.get(f"{M}/ventas", params={"desde": hoy.isoformat(), "hasta": ayer})
    assert invertido.status_code == 422 and invertido.json()["code"] == "INVALID_RANGE"
    largo = t.admin.get(
        f"{M}/ventas", params={"desde": (hoy - timedelta(days=400)).isoformat(), "hasta": hoy.isoformat()}
    )
    assert largo.status_code == 422 and largo.json()["code"] == "RANGE_TOO_LARGE"
    exacto = t.admin.get(
        f"{M}/ventas", params={"desde": (hoy - timedelta(days=365)).isoformat(), "hasta": hoy.isoformat()}
    )
    assert exacto.status_code == 200 and len(exacto.json()["serie"]) == 366
    assert t.admin.get(f"{M}/ventas", params={"desde": "no-es-fecha"}).status_code == 422


# ----------------------------------------------------------------------------------------------
# Top de productos
# ----------------------------------------------------------------------------------------------


def test_top_de_productos_solo_cuenta_ventas(tienda):
    t = tienda
    vender(t)
    top = t.admin.get(f"{M}/top-productos").json()
    # la pizza (2) le gana a la empanada: de la empanada solo cuenta la venta pagada (1); el pendiente y el cancelado no
    assert [(x["nombre"], x["unidades"], D(x["ingresos"])) for x in top] == [
        ("Pizza muzzarella", 2, 19000),
        ("Empanada", 1, 1200),
    ]
    assert len(t.admin.get(f"{M}/top-productos", params={"limit": 1}).json()) == 1
    for malo in (0, 51, -1):
        assert t.admin.get(f"{M}/top-productos", params={"limit": malo}).status_code == 422, malo
    assert t.admin.get(f"{M}/top-productos").json()[0]["producto_id"] == t.pizza


def test_top_de_productos_vacio(tienda):
    assert tienda.admin.get(f"{M}/top-productos").json() == []


# ----------------------------------------------------------------------------------------------
# Stock bajo y lotes por vencer
# ----------------------------------------------------------------------------------------------


def test_stock_bajo_compara_el_disponible_con_el_minimo(tienda):
    t = tienda
    nombres = lambda r, clave: {x["nombre"] for x in r[clave]}  # noqa: E731
    base = t.admin.get(f"{M}/stock-bajo").json()
    assert "Pizza muzzarella" not in nombres(base, "productos")  # 10 en stock y mínimo 0

    t.admin.put(f"{API}/productos/{t.pizza}", json={"stock_minimo": 6})
    pedido_ok(t.cliente, [linea(t.pizza, 5)])  # real 10, disponible 5 ≤ 6
    r = t.admin.get(f"{M}/stock-bajo").json()
    pizza = next(x for x in r["productos"] if x["nombre"] == "Pizza muzzarella")
    assert (D(pizza["stock_real"]), D(pizza["stock_disponible"]), pizza["stock_minimo"]) == (10, 5, 6)
    assert "Empanada" not in nombres(r, "productos")

    # los insumos sin stock (mínimo 0) también cuentan: 0 <= 0
    assert {"Queso", "Harina"} <= nombres(r, "insumos")
    # Los insumos traen su unidad (RN-10) para poder leer las cantidades; los productos no la tienen.
    unidades = {x["nombre"]: x["unidad_medida"] for x in r["insumos"]}
    assert unidades["Queso"] == "KG" and unidades["Harina"] == "KG"
    assert all(x["unidad_medida"] is None for x in r["productos"])
    mover(t.admin, "ingredientes", t.queso, "ENTRADA", "5")
    assert "Queso" not in nombres(t.admin.get(f"{M}/stock-bajo").json(), "insumos")


def test_stock_bajo_ordena_del_mas_comprometido_y_excluye_los_anulados(tienda):
    t = tienda
    t.admin.put(f"{API}/productos/{t.pizza}", json={"stock_minimo": 10})  # 10 ≤ 10
    t.admin.put(f"{API}/productos/{t.empanada}", json={"stock_minimo": 30})  # 20 ≤ 30 (más corto)
    nombres = [x["nombre"] for x in t.admin.get(f"{M}/stock-bajo").json()["productos"]]
    assert nombres == ["Empanada", "Pizza muzzarella"]  # primero la que está más por debajo del mínimo
    t.admin.delete(f"{API}/productos/{t.empanada}")
    assert [x["nombre"] for x in t.admin.get(f"{M}/stock-bajo").json()["productos"]] == ["Pizza muzzarella"]


def test_lotes_por_vencer_en_el_panel(tienda):
    t = tienda
    # la pizza tiene el lote A (vence en 3 días, 4 u.) y el B (en 10 días, 6 u.)
    r = t.admin.get(f"{M}/stock-bajo", params={"dias": 7}).json()
    assert [(x["codigo_lote"], x["producto_nombre"]) for x in r["lotes_por_vencer"]] == [("A", "Pizza muzzarella")]
    assert r["dias"] == 7
    assert len(t.admin.get(f"{M}/stock-bajo", params={"dias": 30}).json()["lotes_por_vencer"]) == 2
    assert t.admin.get(f"{M}/stock-bajo", params={"dias": 1}).json()["lotes_por_vencer"] == []
    for malo in (-1, 366):
        assert t.admin.get(f"{M}/stock-bajo", params={"dias": malo}).status_code == 422


# ----------------------------------------------------------------------------------------------
# Mermas
# ----------------------------------------------------------------------------------------------


def test_mermas_por_motivo_separadas_en_productos_e_insumos(tienda):
    t = tienda
    mover(t.admin, "productos", t.pizza, "MERMA", "2", motivo="ROTURA")
    mover(t.admin, "productos", t.pizza, "MERMA", "1", motivo="VENCIMIENTO")
    mover(t.admin, "productos", t.pizza, "MERMA", "1", motivo="ROTURA")
    mover(t.admin, "productos", t.empanada, "AJUSTE_NEGATIVO", "4")  # un ajuste NO es una merma
    mover(t.admin, "ingredientes", t.queso, "ENTRADA", "10")
    mover(t.admin, "ingredientes", t.queso, "MERMA", "0.5", motivo="CONSUMO_INTERNO")

    for quien in (t.admin, t.stock):
        r = quien.get(f"{M}/mermas").json()
        assert [(m["motivo"], D(m["cantidad"]), m["movimientos"]) for m in r["productos"]] == [
            ("ROTURA", 3, 2),
            ("VENCIMIENTO", 1, 1),
        ]  # la mayor primero
        assert [(m["motivo"], D(m["cantidad"])) for m in r["insumos"]] == [("CONSUMO_INTERNO", D("0.5"))]


def test_mermas_respetan_el_periodo(tienda):
    t = tienda
    mover(t.admin, "productos", t.pizza, "MERMA", "2", motivo="ROTURA")
    hoy = datetime.now(BA).date()
    ayer = (hoy - timedelta(days=1)).isoformat()
    assert t.admin.get(f"{M}/mermas", params={"desde": ayer, "hasta": ayer}).json()["productos"] == []
    en_rango = t.admin.get(f"{M}/mermas", params={"desde": ayer, "hasta": hoy.isoformat()}).json()
    assert [m["motivo"] for m in en_rango["productos"]] == ["ROTURA"]
    assert t.admin.get(f"{M}/mermas", params={"desde": hoy.isoformat(), "hasta": ayer}).status_code == 422
    assert t.admin.get(f"{M}/mermas", params={"desde": "x"}).status_code == 422
    vacio = t.admin.get(
        f"{M}/mermas",
        params={"desde": (hoy + timedelta(days=1)).isoformat(), "hasta": (hoy + timedelta(days=2)).isoformat()},
    )
    assert vacio.json()["productos"] == [] and vacio.json()["insumos"] == []
    _ = Decimal


def test_una_venta_cerca_de_la_medianoche_cuenta_en_el_dia_del_local(tienda, uow_factory):
    """El pago se aprobó a la 01:30 UTC del 17/11, que en Buenos Aires son las 22:30 del 16/11: es una venta del
    día 16. (Los demás tests usan la hora real, en la que el día UTC y el del local casi siempre coinciden.)"""
    from sqlalchemy import text

    pedido = pedido_ok(tienda.cliente, [linea(tienda.pizza, 1)])
    assert pagar(tienda.pedidos, pedido).status_code == 201
    uow = uow_factory(MetricasUnitOfWork)
    with uow:
        uow.session.execute(
            text("update pago set created_at = :t where pedido_id = :p"),
            {"t": datetime(2026, 11, 17, 1, 30, tzinfo=ZoneInfo("UTC")), "p": pedido["id"]},
        )

    serie = tienda.admin.get(f"{M}/ventas", params={"desde": "2026-11-16", "hasta": "2026-11-17"}).json()["serie"]
    assert [(p["fecha"], D(p["total"])) for p in serie] == [("2026-11-16", 9500), ("2026-11-17", 0)]

    ese_dia = service.resumen(uow_factory(MetricasUnitOfWork), datetime(2026, 11, 16, 12, tzinfo=BA))
    otro_dia = service.resumen(uow_factory(MetricasUnitOfWork), datetime(2026, 11, 17, 12, tzinfo=BA))
    assert (ese_dia.ventas_del_dia, otro_dia.ventas_del_dia) == (9500, 0)
