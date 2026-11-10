"""Direcciones de entrega (sección 6.2, RN-17)."""

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import API, registrar_y_loguear

CASA = {"alias": "Casa", "linea1": "Calle Falsa 123", "ciudad": "Buenos Aires", "lat": -34.6, "lng": -58.4}


def test_la_primera_direccion_queda_como_principal(client):
    registrar_y_loguear(client)
    r = client.post(f"{API}/direcciones", json=CASA)
    assert r.status_code == 201 and r.json()["es_principal"] is True
    r2 = client.post(f"{API}/direcciones", json={"linea1": "Otra 456"})
    assert r2.json()["es_principal"] is False


def test_solo_hay_una_principal_activa_por_usuario(client):
    registrar_y_loguear(client)
    a = client.post(f"{API}/direcciones", json=CASA).json()
    b = client.post(f"{API}/direcciones", json={"linea1": "Otra 456", "es_principal": True}).json()
    assert b["es_principal"] is True

    lista = client.get(f"{API}/direcciones").json()
    assert [d["es_principal"] for d in lista] == [True, False]  # la principal va primero
    assert lista[0]["id"] == b["id"]

    r = client.patch(f"{API}/direcciones/{a['id']}/principal")
    assert r.status_code == 200 and r.json()["es_principal"] is True
    assert sum(d["es_principal"] for d in client.get(f"{API}/direcciones").json()) == 1


def test_lat_y_lng_deben_ir_juntas_y_en_rango(client):
    registrar_y_loguear(client)
    assert client.post(f"{API}/direcciones", json={"linea1": "X", "lat": -34.6}).status_code == 422
    assert client.post(f"{API}/direcciones", json={"linea1": "X", "lat": 120, "lng": 0}).status_code == 422
    assert client.post(f"{API}/direcciones", json={"linea1": ""}).status_code == 422
    d = client.post(f"{API}/direcciones", json=CASA).json()
    r = client.put(f"{API}/direcciones/{d['id']}", json={"lat": None})  # dejaría lng sin lat
    assert r.status_code == 422 and r.json()["code"] == "INVALID_COORDINATES"


def test_edicion_parcial_y_baja_logica(client):
    registrar_y_loguear(client)
    d = client.post(f"{API}/direcciones", json=CASA).json()

    r = client.put(f"{API}/direcciones/{d['id']}", json={"alias": "Trabajo"})
    assert r.json()["alias"] == "Trabajo" and r.json()["linea1"] == CASA["linea1"]

    assert client.delete(f"{API}/direcciones/{d['id']}").status_code == 204
    assert client.get(f"{API}/direcciones").json() == []
    assert client.delete(f"{API}/direcciones/{d['id']}").status_code == 404


def test_una_direccion_eliminada_libera_el_lugar_de_principal(client):
    registrar_y_loguear(client)
    a = client.post(f"{API}/direcciones", json=CASA).json()
    client.delete(f"{API}/direcciones/{a['id']}")
    nueva = client.post(f"{API}/direcciones", json={"linea1": "Nueva 1"}).json()
    assert nueva["es_principal"] is True


def test_un_usuario_no_accede_a_las_direcciones_de_otro(client):
    registrar_y_loguear(client, "dueno@test.com")
    d = client.post(f"{API}/direcciones", json=CASA).json()

    with TestClient(app) as intruso:
        registrar_y_loguear(intruso, "intruso@test.com")
        assert intruso.get(f"{API}/direcciones").json() == []
        assert intruso.put(f"{API}/direcciones/{d['id']}", json={"alias": "Hack"}).status_code == 404
        assert intruso.delete(f"{API}/direcciones/{d['id']}").status_code == 404
        assert intruso.patch(f"{API}/direcciones/{d['id']}/principal").status_code == 404


def test_requiere_autenticacion(client):
    assert client.get(f"{API}/direcciones").status_code == 401
    assert client.post(f"{API}/direcciones", json=CASA).status_code == 401
