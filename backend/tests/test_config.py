"""Configuración y cobertura (secciones 6.7, 10.1 y 10.2): horarios, días bloqueados, zonas y envío."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.core.errors import ConflictError
from app.modules.config import service
from app.modules.config.geo import distancia_haversine_km, punto_en_poligono
from app.modules.config.horarios import Bloqueo, Franja, esta_abierto, proxima_apertura
from app.modules.config.uow import ConfigUnitOfWork
from tests.helpers import API, login_admin, registrar_y_loguear
from tests.test_inventario import D

CONFIG = f"{API}/config"
BA = ZoneInfo("America/Argentina/Buenos_Aires")

# El seed deja el local en Buenos Aires, abierto todos los días de 11:00 a 23:00, y la «Zona Centro».
LUNES = date(2026, 11, 16)
CUADRADO = [[-34.0, -58.0], [-34.0, -57.0], [-35.0, -57.0], [-35.0, -58.0]]


def local_a(dia: date, hora: int, minuto: int = 0) -> datetime:
    return datetime.combine(dia, time(hora, minuto), tzinfo=BA)


def franja(dia: int, a: str, c: str) -> Franja:
    return Franja(dia, time.fromisoformat(a), time.fromisoformat(c))


def cliente(client: TestClient) -> TestClient:
    otro = TestClient(client.app)
    registrar_y_loguear(otro)
    return otro


# ----------------------------------------------------------------------------------------------
# Geometría pura
# ----------------------------------------------------------------------------------------------


def test_ray_casting_en_un_cuadrado():
    assert punto_en_poligono((-34.5, -57.5), CUADRADO) is True
    for afuera in ((-33.9, -57.5), (-35.1, -57.5), (-34.5, -56.9), (-34.5, -58.1)):
        assert punto_en_poligono(afuera, CUADRADO) is False, afuera
    assert punto_en_poligono((-34.0, -57.5), CUADRADO) is True  # sobre un lado
    assert punto_en_poligono((-34.0, -58.0), CUADRADO) is True  # en un vértice


def test_ray_casting_en_un_poligono_concavo_y_degenerado():
    ele = [[0, 0], [0, 10], [5, 10], [5, 5], [10, 5], [10, 0]]  # una L: el hueco está arriba a la derecha
    assert punto_en_poligono((2, 2), ele) is True
    assert punto_en_poligono((2, 8), ele) is True
    assert punto_en_poligono((8, 2), ele) is True
    assert punto_en_poligono((8, 8), ele) is False  # dentro del rectángulo envolvente pero fuera de la L
    assert punto_en_poligono((1, 1), [[0, 0], [5, 5]]) is False  # menos de 3 vértices


def test_haversine():
    obelisco, la_plata = (-34.6037, -58.3816), (-34.9215, -57.9545)
    assert distancia_haversine_km(obelisco, obelisco) == 0
    d = distancia_haversine_km(obelisco, la_plata)
    assert 51 < d < 54 and d == distancia_haversine_km(la_plata, obelisco)
    assert abs(distancia_haversine_km((0, 0), (1, 0)) - 111.19) < 0.05  # un grado de latitud


# ----------------------------------------------------------------------------------------------
# Horarios pura
# ----------------------------------------------------------------------------------------------


def test_abierto_en_los_bordes_de_la_franja():
    franjas = [franja(0, "11:00", "23:00")]  # lunes
    assert esta_abierto(local_a(LUNES, 11), franjas, []) is True  # la apertura es inclusiva
    assert esta_abierto(local_a(LUNES, 22, 59), franjas, []) is True
    assert esta_abierto(local_a(LUNES, 23), franjas, []) is False  # el cierre es exclusivo
    assert esta_abierto(local_a(LUNES, 10, 59), franjas, []) is False
    assert esta_abierto(local_a(LUNES + timedelta(days=1), 12), franjas, []) is False  # martes: sin franja


def test_varias_franjas_en_un_dia():
    franjas = [franja(0, "12:00", "15:00"), franja(0, "20:00", "23:30")]
    assert [esta_abierto(local_a(LUNES, h), franjas, []) for h in (11, 13, 16, 21, 23)] == [
        False,
        True,
        False,
        True,
        True,
    ]


def test_dias_bloqueados_totales_y_parciales():
    franjas = [franja(0, "11:00", "23:00")]
    total = Bloqueo(LUNES, True)
    parcial = Bloqueo(LUNES, False, time(14), time(16))
    assert esta_abierto(local_a(LUNES, 12), franjas, [total]) is False
    assert esta_abierto(local_a(LUNES, 12), franjas, [parcial]) is True
    assert esta_abierto(local_a(LUNES, 14), franjas, [parcial]) is False
    assert esta_abierto(local_a(LUNES, 15, 59), franjas, [parcial]) is False
    assert esta_abierto(local_a(LUNES, 16), franjas, [parcial]) is True  # hasta es exclusivo
    assert esta_abierto(local_a(LUNES + timedelta(days=7), 12), franjas, [total]) is True  # otro lunes


def test_proxima_apertura():
    franjas = [franja(d, "11:00", "23:00") for d in range(7)]
    martes = LUNES + timedelta(days=1)
    assert proxima_apertura(local_a(LUNES, 3), franjas, []) == local_a(LUNES, 11)  # antes de abrir: hoy
    assert proxima_apertura(local_a(LUNES, 23, 30), franjas, []) == local_a(martes, 11)  # después de cerrar: mañana
    # mañana cerrado todo el día: pasado mañana
    assert proxima_apertura(local_a(LUNES, 23, 30), franjas, [Bloqueo(martes, True)]) == local_a(
        LUNES + timedelta(days=2), 11
    )
    # cierre parcial en plena franja: reabre cuando termina
    assert proxima_apertura(local_a(LUNES, 15), franjas, [Bloqueo(LUNES, False, time(14), time(17))]) == local_a(
        LUNES, 17
    )
    # con dos franjas el mismo día, la siguiente
    dos = [franja(0, "12:00", "15:00"), franja(0, "20:00", "23:00")]
    assert proxima_apertura(local_a(LUNES, 16), dos, []) == local_a(LUNES, 20)
    assert proxima_apertura(local_a(LUNES, 16), [], []) is None  # sin franjas nunca abre
    assert (
        proxima_apertura(local_a(LUNES, 16), franjas, [Bloqueo(LUNES + timedelta(days=i), True) for i in range(30)])
        is None
    )


# ----------------------------------------------------------------------------------------------
# Permisos
# ----------------------------------------------------------------------------------------------


def test_lecturas_publicas_y_el_resto_solo_admin(client):
    anonimo = TestClient(client.app)
    assert anonimo.get(f"{CONFIG}/estado-local").status_code == 200
    assert anonimo.get(f"{CONFIG}/horarios").status_code == 200

    otro = cliente(client)
    protegidos = [
        ("get", "/config/local", None),
        ("put", "/config/local", {"nombre": "X", "zona_horaria": "UTC"}),
        ("put", "/config/horarios", {"items": []}),
        ("get", "/config/dias-bloqueados", None),
        ("post", "/config/dias-bloqueados", {"fecha": "2030-01-01"}),
        ("delete", "/config/dias-bloqueados/1", None),
        ("get", "/config/zonas", None),
        ("post", "/config/zonas", {"nombre": "X", "poligono": CUADRADO}),
        ("get", "/config/zonas/1", None),
        ("put", "/config/zonas/1", {"nombre": "X"}),
        ("delete", "/config/zonas/1", None),
    ]
    for metodo, ruta, body in protegidos:
        kw = {"json": body} if body is not None else {}
        assert getattr(otro, metodo)(f"{API}{ruta}", **kw).status_code == 403, ruta
        assert getattr(anonimo, metodo)(f"{API}{ruta}", **kw).status_code == 401, ruta


# ----------------------------------------------------------------------------------------------
# Local
# ----------------------------------------------------------------------------------------------


def test_datos_del_local(client):
    login_admin(client)
    local = client.get(f"{CONFIG}/local").json()
    assert local["zona_horaria"] == "America/Argentina/Buenos_Aires" and local["lat_origen"] == -34.6037

    nuevo = {
        "nombre": "  Mi local ",
        "zona_horaria": "America/Argentina/Cordoba",
        "lat_origen": -31.4,
        "lng_origen": -64.2,
    }
    r = client.put(f"{CONFIG}/local", json=nuevo)
    assert r.status_code == 200 and r.json()["nombre"] == "Mi local" and r.json()["direccion_origen"] is None
    assert client.get(f"{CONFIG}/local").json()["zona_horaria"] == "America/Argentina/Cordoba"


def test_validaciones_del_local(client):
    login_admin(client)
    base = {"nombre": "X", "zona_horaria": "America/Argentina/Buenos_Aires"}
    malos = [
        {**base, "zona_horaria": "Marte/Olympus"},
        {**base, "zona_horaria": ""},
        {**base, "nombre": "   "},
        {**base, "lat_origen": -34.6},  # latitud sin longitud
        {**base, "lat_origen": 91, "lng_origen": 0},
        {**base, "lat_origen": 0, "lng_origen": 181},
    ]
    for body in malos:
        assert client.put(f"{CONFIG}/local", json=body).status_code == 422, body


# ----------------------------------------------------------------------------------------------
# Estado del local (RN-13)
# ----------------------------------------------------------------------------------------------


def estado(ahora: datetime, uow_factory) -> dict:
    return service.estado_local(uow_factory(ConfigUnitOfWork), ahora).model_dump()


def test_estado_local_con_el_horario_del_seed(client, uow_factory):
    # el seed abre todos los días de 11 a 23 (hora de Buenos Aires)
    cerrado = estado(local_a(LUNES, 10), uow_factory)
    assert cerrado["abierto"] is False and cerrado["proxima_apertura"] == local_a(LUNES, 11)
    abierto = estado(local_a(LUNES, 12), uow_factory)
    assert abierto["abierto"] is True and abierto["proxima_apertura"] is None
    assert estado(local_a(LUNES, 23, 30), uow_factory)["proxima_apertura"] == local_a(LUNES + timedelta(days=1), 11)


def test_la_hora_se_evalua_en_la_zona_del_local_no_en_utc(client, uow_factory):
    # 01:00 UTC del martes son las 22:00 del lunes en Buenos Aires: abierto, aunque en UTC sería de madrugada
    instante = datetime(2026, 11, 17, 1, 0, tzinfo=UTC)
    assert estado(instante, uow_factory)["abierto"] is True

    login_admin(client)
    r = client.put(f"{CONFIG}/local", json={"nombre": "X", "zona_horaria": "UTC"})
    assert r.status_code == 200
    assert estado(instante, uow_factory)["abierto"] is False  # con el local en UTC, la 01:00 está cerrado


def test_el_endpoint_publico_informa_el_estado(client):
    login_admin(client)
    todo_el_dia = {"items": [{"dia_semana": d, "hora_apertura": "00:00", "hora_cierre": "23:59"} for d in range(7)]}
    client.put(f"{CONFIG}/horarios", json=todo_el_dia)
    publico = TestClient(client.app)
    r = publico.get(f"{CONFIG}/estado-local").json()
    # a las 23:59 en punto cerraría, pero cualquier otro momento está abierto
    assert r["zona_horaria"] == "America/Argentina/Buenos_Aires" and set(r) == {
        "abierto",
        "proxima_apertura",
        "zona_horaria",
    }
    client.put(f"{CONFIG}/horarios", json={"items": []})
    cerrado = publico.get(f"{CONFIG}/estado-local").json()
    assert cerrado["abierto"] is False and cerrado["proxima_apertura"] is None


def test_exigir_local_abierto(client, uow_factory):
    uow = uow_factory(ConfigUnitOfWork)
    with uow:
        service.exigir_local_abierto(uow, local_a(LUNES, 12))  # abierto: no pasa nada
        try:
            service.exigir_local_abierto(uow, local_a(LUNES, 8))
        except ConflictError as e:
            assert e.code == "LOCAL_CLOSED" and "16/11/2026 11:00" in e.detail
        else:
            raise AssertionError("dejó pedir con el local cerrado")


# ----------------------------------------------------------------------------------------------
# Horarios
# ----------------------------------------------------------------------------------------------


def test_reemplazar_horarios(client):
    login_admin(client)
    assert len(client.get(f"{CONFIG}/horarios").json()) == 7  # los del seed
    items = [
        {"dia_semana": 4, "hora_apertura": "20:00", "hora_cierre": "23:30"},
        {"dia_semana": 4, "hora_apertura": "12:00", "hora_cierre": "15:00"},
        {"dia_semana": 0, "hora_apertura": "10:00", "hora_cierre": "14:00", "activo": False},
    ]
    r = client.put(f"{CONFIG}/horarios", json={"items": items})
    assert r.status_code == 200
    assert [(h["dia_semana"], h["hora_apertura"], h["activo"]) for h in r.json()] == [
        (0, "10:00:00", False),
        (4, "12:00:00", True),
        (4, "20:00:00", True),
    ]
    assert len(TestClient(client.app).get(f"{CONFIG}/horarios").json()) == 3  # reemplazó, no sumó


def test_validaciones_de_horarios(client):
    login_admin(client)
    antes = client.get(f"{CONFIG}/horarios").json()

    def franja_json(dia=1, a="10:00", c="12:00", **extra):
        return {"dia_semana": dia, "hora_apertura": a, "hora_cierre": c, **extra}

    for item in (
        franja_json(dia=7),
        franja_json(dia=-1),
        franja_json(a="12:00", c="10:00"),
        franja_json(a="10:00", c="10:00"),
    ):
        assert client.put(f"{CONFIG}/horarios", json={"items": [item]}).status_code == 422, item
    solapadas = client.put(
        f"{CONFIG}/horarios", json={"items": [franja_json(a="10:00", c="14:00"), franja_json(a="13:00", c="16:00")]}
    )
    assert solapadas.status_code == 422 and solapadas.json()["code"] == "SCHEDULE_OVERLAP"
    # una franja inactiva no cuenta para el solapamiento, y pegadas (cierre = apertura) no se solapan
    ok = client.put(
        f"{CONFIG}/horarios",
        json={
            "items": [
                franja_json(a="10:00", c="14:00"),
                franja_json(a="13:00", c="16:00", activo=False),
                franja_json(a="14:00", c="18:00"),
            ]
        },
    )
    assert ok.status_code == 200
    assert (
        client.put(
            f"{CONFIG}/horarios", json={"items": [franja_json(a="10:00", c="14:00"), franja_json(a="13:00", c="15:00")]}
        ).status_code
        == 422
    )
    assert antes != ok.json()  # y los rechazos no habían tocado nada: recién ahora cambió


# ----------------------------------------------------------------------------------------------
# Días bloqueados
# ----------------------------------------------------------------------------------------------


def test_abm_de_dias_bloqueados(client):
    login_admin(client)
    r = client.post(f"{CONFIG}/dias-bloqueados", json={"fecha": "2026-12-25", "motivo": " Navidad "})
    assert r.status_code == 201
    dia = r.json()
    assert dia["fecha"] == "2026-12-25" and dia["motivo"] == "Navidad" and dia["todo_el_dia"] is True
    parcial = client.post(
        f"{CONFIG}/dias-bloqueados",
        json={"fecha": "2026-12-24", "todo_el_dia": False, "hora_desde": "18:00", "hora_hasta": "23:00"},
    )
    assert parcial.status_code == 201 and parcial.json()["hora_desde"] == "18:00:00"

    fechas = [d["fecha"] for d in client.get(f"{CONFIG}/dias-bloqueados").json()]
    assert fechas == ["2026-12-24", "2026-12-25"]  # ordenados por fecha
    assert [d["fecha"] for d in client.get(f"{CONFIG}/dias-bloqueados", params={"desde": "2026-12-25"}).json()] == [
        "2026-12-25"
    ]

    repetido = client.post(f"{CONFIG}/dias-bloqueados", json={"fecha": "2026-12-25"})
    assert repetido.status_code == 409 and repetido.json()["code"] == "DAY_ALREADY_BLOCKED"

    assert client.delete(f"{CONFIG}/dias-bloqueados/{dia['id']}").status_code == 204
    assert client.delete(f"{CONFIG}/dias-bloqueados/{dia['id']}").status_code == 404
    assert [d["fecha"] for d in client.get(f"{CONFIG}/dias-bloqueados").json()] == ["2026-12-24"]


def test_validaciones_de_dias_bloqueados(client):
    login_admin(client)
    malos = [
        {"fecha": "no-es-fecha"},
        {"fecha": "2026-12-25", "todo_el_dia": False},  # parcial sin horas
        {"fecha": "2026-12-25", "todo_el_dia": False, "hora_desde": "10:00"},
        {"fecha": "2026-12-25", "todo_el_dia": False, "hora_desde": "12:00", "hora_hasta": "10:00"},
        {"fecha": "2026-12-25", "todo_el_dia": True, "hora_desde": "10:00", "hora_hasta": "12:00"},
    ]
    for body in malos:
        assert client.post(f"{CONFIG}/dias-bloqueados", json=body).status_code == 422, body


def test_un_dia_bloqueado_cierra_el_local(client, uow_factory):
    login_admin(client)
    assert estado(local_a(LUNES, 12), uow_factory)["abierto"] is True
    client.post(f"{CONFIG}/dias-bloqueados", json={"fecha": LUNES.isoformat(), "motivo": "Feriado"})
    cerrado = estado(local_a(LUNES, 12), uow_factory)
    assert cerrado["abierto"] is False and cerrado["proxima_apertura"] == local_a(LUNES + timedelta(days=1), 11)

    client.post(
        f"{CONFIG}/dias-bloqueados",
        json={
            "fecha": (LUNES + timedelta(days=1)).isoformat(),
            "todo_el_dia": False,
            "hora_desde": "11:00",
            "hora_hasta": "13:00",
        },
    )
    # el martes abre recién a las 13 por el cierre parcial
    assert estado(local_a(LUNES, 12), uow_factory)["proxima_apertura"] == local_a(LUNES + timedelta(days=1), 13)


# ----------------------------------------------------------------------------------------------
# Zonas
# ----------------------------------------------------------------------------------------------


def zona(client: TestClient, nombre: str = "Norte", poligono=None, **extra) -> dict:
    r = client.post(f"{CONFIG}/zonas", json={"nombre": nombre, "poligono": poligono or CUADRADO, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def test_abm_de_zonas(client):
    login_admin(client)
    assert [z["nombre"] for z in client.get(f"{CONFIG}/zonas").json()] == ["Zona Centro"]  # la del seed

    z = zona(client, "  Norte ", tarifa_base="300", tarifa_por_km="90.5", pedido_minimo="2500")
    assert z["nombre"] == "Norte" and z["activo"] is True and D(z["tarifa_por_km"]) == D("90.5")
    assert z["poligono"][0] == [-34.0, -58.0]
    assert client.get(f"{CONFIG}/zonas/{z['id']}").json()["nombre"] == "Norte"

    r = client.put(f"{CONFIG}/zonas/{z['id']}", json={"tarifa_base": "400"})  # cambia solo lo enviado
    assert D(r.json()["tarifa_base"]) == 400 and r.json()["nombre"] == "Norte" and D(r.json()["pedido_minimo"]) == 2500

    assert client.delete(f"{CONFIG}/zonas/{z['id']}").status_code == 204
    assert client.get(f"{CONFIG}/zonas/{z['id']}").json()["activo"] is False  # baja por activo, no se borra
    assert [x["nombre"] for x in client.get(f"{CONFIG}/zonas", params={"activo": True}).json()] == ["Zona Centro"]
    assert [x["nombre"] for x in client.get(f"{CONFIG}/zonas", params={"activo": False}).json()] == ["Norte"]
    assert len(client.get(f"{CONFIG}/zonas").json()) == 2

    assert client.put(f"{CONFIG}/zonas/{z['id']}", json={"activo": True}).json()["activo"] is True  # reactivar
    assert client.get(f"{CONFIG}/zonas/999999").status_code == 404
    assert client.put(f"{CONFIG}/zonas/999999", json={"nombre": "X"}).status_code == 404
    assert client.delete(f"{CONFIG}/zonas/999999").status_code == 404


def test_validaciones_de_zonas(client):
    login_admin(client)
    base = {"nombre": "X", "poligono": CUADRADO}
    malos = [
        {**base, "poligono": [[-34, -58], [-34, -57]]},  # 2 vértices
        {**base, "poligono": [[-34, -58], [-34, -58], [-34, -58]]},  # 1 vértice repetido
        {**base, "poligono": [[91, 0], [0, 0], [0, 1]]},  # latitud fuera de rango
        {**base, "poligono": [[0, 181], [0, 0], [1, 0]]},  # longitud fuera de rango
        {**base, "poligono": [[0, 0, 0], [1, 1, 1], [2, 2, 2]]},  # vértices con 3 coordenadas
        {**base, "nombre": "  "},
        {**base, "tarifa_base": "-1"},
        {**base, "tarifa_por_km": "1.234"},
        {**base, "pedido_minimo": "abc"},
    ]
    for body in malos:
        assert client.post(f"{CONFIG}/zonas", json=body).status_code == 422, body
    z = zona(client)
    assert client.put(f"{CONFIG}/zonas/{z['id']}", json={"poligono": [[1, 1]]}).status_code == 422
    assert client.put(f"{CONFIG}/zonas/{z['id']}", json={"nombre": None}).status_code == 422
    assert client.put(f"{CONFIG}/zonas/{z['id']}", json={"activo": None}).status_code == 422


def test_el_nombre_de_una_zona_activa_es_unico(client):
    login_admin(client)
    norte = zona(client, "Norte")
    repetida = client.post(f"{CONFIG}/zonas", json={"nombre": "norte", "poligono": CUADRADO})
    assert repetida.status_code == 409 and repetida.json()["code"] == "ZONE_NAME_TAKEN"
    otra = zona(client, "Sur")
    assert client.put(f"{CONFIG}/zonas/{otra['id']}", json={"nombre": "NORTE"}).status_code == 409
    assert (
        client.put(f"{CONFIG}/zonas/{norte['id']}", json={"nombre": "Norte"}).status_code == 200
    )  # el propio no choca

    client.delete(f"{CONFIG}/zonas/{norte['id']}")
    nueva = zona(client, "Norte")  # con la anterior dada de baja, el nombre se libera
    reactivar = client.put(f"{CONFIG}/zonas/{norte['id']}", json={"activo": True})
    assert reactivar.status_code == 409  # pero no puede reactivarse si ahora hay otra activa con ese nombre
    assert nueva["id"] != norte["id"]


# ----------------------------------------------------------------------------------------------
# Cotización de envío (RN-14)
# ----------------------------------------------------------------------------------------------

ORIGEN = (-34.6037, -58.3816)
DENTRO = (-34.6037, -58.3716)  # ~0,9 km al este del local, dentro de la Zona Centro del seed


def cotizar(client: TestClient, lat: float, lng: float, subtotal: str = "5000"):
    return client.post(f"{API}/envio/cotizar", json={"lat": lat, "lng": lng, "subtotal": subtotal})


def test_cotizar_dentro_de_la_zona(client):
    comprador = cliente(client)
    r = cotizar(comprador, *DENTRO)
    assert r.status_code == 200, r.text
    c = r.json()
    km = round(distancia_haversine_km(ORIGEN, DENTRO), 2)
    assert c["dentro_de_cobertura"] is True and c["zona"]["nombre"] == "Zona Centro"
    assert c["distancia_km"] == km and 0.8 < km < 1.1
    assert D(c["costo_envio"]) == D("500") + D(str(km)) * 150  # tarifa_base + km × tarifa_por_km (seed: 500 y 150)
    assert c["cumple_minimo"] is True and D(c["zona"]["pedido_minimo"]) == 3000


def test_pedido_minimo_de_la_zona(client):
    comprador = cliente(client)
    assert cotizar(comprador, *DENTRO, "2999.99").json()["cumple_minimo"] is False
    assert cotizar(comprador, *DENTRO, "3000").json()["cumple_minimo"] is True  # llegar justo alcanza
    assert cotizar(comprador, *DENTRO, "0").json()["cumple_minimo"] is False


def test_cotizar_fuera_de_toda_zona_es_422(client):
    """Sección 10.2: «Fuera de toda zona: 422». Sin zona no hay distancia ni costo que calcular."""
    comprador = cliente(client)
    r = cotizar(comprador, -34.70, -58.30)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "OUTSIDE_COVERAGE" and r.json()["field"] == "lat"
    assert "dentro_de_cobertura" not in r.json()  # el error usa el formato estándar {detail, code, field}

    # una zona dada de baja no cubre: el mismo punto que antes cotizaba ahora es 422
    assert cotizar(comprador, *DENTRO).status_code == 200
    admin = login_admin(TestClient(client.app))
    centro = next(z for z in admin.get(f"{CONFIG}/zonas").json() if z["nombre"] == "Zona Centro")
    admin.delete(f"{CONFIG}/zonas/{centro['id']}")
    r = cotizar(comprador, *DENTRO)
    assert (r.status_code, r.json()["code"]) == (422, "OUTSIDE_COVERAGE")


def test_el_pedido_minimo_solo_se_informa_en_la_cotizacion(client):
    """Debajo del mínimo la cotización existe (200) y lo avisa con cumple_minimo; no es un error."""
    r = cotizar(cliente(client), *DENTRO, "100")
    assert r.status_code == 200 and r.json()["cumple_minimo"] is False and r.json()["dentro_de_cobertura"] is True


def test_zonas_superpuestas_gana_la_de_menor_id_y_cada_una_tiene_su_tarifa(client):
    admin = login_admin(TestClient(client.app))
    comprador = cliente(client)
    grande = [[-34.5, -58.5], [-34.5, -58.3], [-34.7, -58.3], [-34.7, -58.5]]  # contiene a DENTRO y al seed
    zona(admin, "Grande", grande, tarifa_base="100", tarifa_por_km="10")
    assert cotizar(comprador, *DENTRO).json()["zona"]["nombre"] == "Zona Centro"  # el seed tiene menor id
    # el punto está en la grande pero ya no en la del seed: gana la grande con su tarifa
    fuera_del_centro = (-34.52, -58.45)
    c = cotizar(comprador, *fuera_del_centro).json()
    assert c["zona"]["nombre"] == "Grande"
    km = round(distancia_haversine_km(ORIGEN, fuera_del_centro), 2)
    assert D(c["costo_envio"]) == D("100") + D(str(km)) * 10


def test_cotizar_validaciones_y_permisos(client):
    comprador = cliente(client)
    assert comprador.post(f"{API}/envio/cotizar", json={"lat": 91, "lng": 0, "subtotal": "1"}).status_code == 422
    assert comprador.post(f"{API}/envio/cotizar", json={"lat": 0, "lng": 181, "subtotal": "1"}).status_code == 422
    assert comprador.post(f"{API}/envio/cotizar", json={"lat": 0, "lng": 0, "subtotal": "-1"}).status_code == 422
    assert comprador.post(f"{API}/envio/cotizar", json={"lat": 0, "lng": 0}).status_code == 422  # sin subtotal
    assert (
        comprador.post(f"{API}/envio/cotizar", json={"lng": 0, "subtotal": "1"}).status_code == 422
    )  # sin coordenadas

    assert cotizar(TestClient(client.app), *DENTRO).status_code == 401
    assert cotizar(login_admin(TestClient(client.app)), *DENTRO).status_code == 403  # es del CLIENT


def test_no_se_cotiza_sin_punto_de_origen(client):
    admin = login_admin(TestClient(client.app))
    admin.put(f"{CONFIG}/local", json={"nombre": "X", "zona_horaria": "UTC"})  # sin lat/lng de origen
    r = cotizar(cliente(client), *DENTRO)
    assert r.status_code == 409 and r.json()["code"] == "ORIGIN_NOT_SET"
