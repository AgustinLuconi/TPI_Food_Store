"""ABM de usuarios (sección 6.2): solo ADMIN."""

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from tests.helpers import API, PASSWORD, login, login_admin, registrar_y_loguear


def crear_usuario(email: str) -> int:
    with TestClient(app) as anon:
        return registrar_y_loguear(anon, email)["id"]


def test_listado_paginado_con_filtros(client):
    crear_usuario("uno@test.com")
    crear_usuario("dos@test.com")
    login_admin(client)

    r = client.get(f"{API}/usuarios", params={"size": 2})
    body = r.json()
    assert r.status_code == 200
    assert set(body) == {"items", "total", "page", "size", "pages"}
    assert body["total"] == 3 and body["pages"] == 2 and len(body["items"]) == 2

    assert client.get(f"{API}/usuarios", params={"search": "uno@"}).json()["total"] == 1
    assert client.get(f"{API}/usuarios", params={"rol": "ADMIN"}).json()["total"] == 1
    assert client.get(f"{API}/usuarios", params={"rol": "INEXISTENTE"}).status_code == 422


def test_el_listado_nunca_expone_el_hash(client):
    login_admin(client)
    assert "password" not in client.get(f"{API}/usuarios").text


def test_baja_logica_filtro_de_estado_y_reactivacion(client):
    uid = crear_usuario("baja@test.com")
    login_admin(client)

    assert client.delete(f"{API}/usuarios/{uid}").status_code == 204
    activos = client.get(f"{API}/usuarios").json()["items"]
    assert all(u["id"] != uid for u in activos)  # por defecto excluye dados de baja

    inactivos = client.get(f"{API}/usuarios", params={"estado": "inactivos"}).json()["items"]
    assert [u["id"] for u in inactivos] == [uid] and inactivos[0]["deleted_at"]
    assert client.get(f"{API}/usuarios", params={"incluir_inactivos": True}).json()["total"] == 2

    r = client.patch(f"{API}/usuarios/{uid}/reactivar")
    assert r.status_code == 200 and r.json()["deleted_at"] is None
    assert client.patch(f"{API}/usuarios/{uid}/reactivar").status_code == 409  # ya está activo


def test_usuario_dado_de_baja_no_puede_iniciar_sesion_ni_reusar_su_email(client):
    uid = crear_usuario("baja@test.com")
    login_admin(client)
    client.delete(f"{API}/usuarios/{uid}")

    with TestClient(app) as otro:
        assert login(otro, "baja@test.com", PASSWORD).status_code == 400
        r = otro.post(
            f"{API}/auth/register",
            json={"nombre": "X", "apellido": "Y", "email": "baja@test.com", "password": PASSWORD},
        )
        assert r.status_code == 409  # el email sigue siendo único tras la baja


def test_sesion_activa_de_un_usuario_dado_de_baja_deja_de_funcionar(client):
    with TestClient(app) as victima:
        uid = registrar_y_loguear(victima, "victima@test.com")["id"]
        assert victima.get(f"{API}/auth/me").status_code == 200
        login_admin(client)
        client.delete(f"{API}/usuarios/{uid}")
        assert victima.get(f"{API}/auth/me").status_code == 401


def test_actualizar_datos_y_conflicto_de_email(client):
    uid = crear_usuario("editar@test.com")
    crear_usuario("ocupado@test.com")
    login_admin(client)

    r = client.put(f"{API}/usuarios/{uid}", json={"nombre": "Nuevo", "telefono": "261-555"})
    assert r.status_code == 200 and r.json()["nombre"] == "Nuevo" and r.json()["telefono"] == "261-555"
    assert r.json()["email"] == "editar@test.com"  # no enviado: no cambia

    r = client.put(f"{API}/usuarios/{uid}", json={"email": "OCUPADO@test.com"})
    assert r.status_code == 409 and r.json()["code"] == "EMAIL_TAKEN"
    assert client.put(f"{API}/usuarios/999999", json={"nombre": "X"}).status_code == 404


def test_reemplazo_de_roles_registra_quien_asigno(client, session_factory):
    uid = crear_usuario("roles@test.com")
    login_admin(client)

    r = client.put(f"{API}/usuarios/{uid}/roles", json={"roles": ["STOCK", "PEDIDOS", "STOCK"]})
    assert r.status_code == 200 and r.json()["roles"] == ["PEDIDOS", "STOCK"]  # reemplaza y deduplica

    with session_factory() as s:
        asignadores = s.exec(  # type: ignore[call-overload]
            text("select distinct asignado_por_id from usuario_rol where usuario_id = :u"), params={"u": uid}
        ).all()
    assert len(asignadores) == 1 and asignadores[0][0] is not None

    assert client.put(f"{API}/usuarios/{uid}/roles", json={"roles": []}).status_code == 422  # al menos un rol
    assert client.put(f"{API}/usuarios/{uid}/roles", json={"roles": ["HACKER"]}).json()["code"] == "UNKNOWN_ROLE"


def test_bloqueo_y_desbloqueo(client):
    uid = crear_usuario("bloqueo@test.com")
    login_admin(client)
    assert client.patch(f"{API}/usuarios/{uid}/estado", json={"disabled": True}).json()["disabled"] is True
    with TestClient(app) as otro:
        assert login(otro, "bloqueo@test.com", PASSWORD).status_code == 400
    assert client.patch(f"{API}/usuarios/{uid}/estado", json={"disabled": False}).json()["disabled"] is False
    with TestClient(app) as otro:
        assert login(otro, "bloqueo@test.com", PASSWORD).status_code == 200


def test_no_se_puede_dejar_el_sistema_sin_administrador(client):
    login_admin(client)
    me = client.get(f"{API}/auth/me").json()
    for r in (
        client.delete(f"{API}/usuarios/{me['id']}"),
        client.patch(f"{API}/usuarios/{me['id']}/estado", json={"disabled": True}),
    ):
        assert r.status_code == 409 and r.json()["code"] == "SELF_ACTION"
    r = client.put(f"{API}/usuarios/{me['id']}/roles", json={"roles": ["CLIENT"]})
    assert r.status_code == 409 and r.json()["code"] == "LAST_ADMIN"


def test_solo_admin_accede(client):
    registrar_y_loguear(client)
    for r in (
        client.get(f"{API}/usuarios"),
        client.delete(f"{API}/usuarios/1"),
        client.put(f"{API}/usuarios/1/roles", json={"roles": ["ADMIN"]}),
    ):
        assert r.status_code == 403
    with TestClient(app) as anon:
        assert anon.get(f"{API}/usuarios").status_code == 401


def test_alta_por_un_administrador(client):
    login_admin(client)
    body = {
        "nombre": "Sofía",
        "apellido": "Gómez",
        "email": "Sofia@Test.com",
        "password": PASSWORD,
        "roles": ["STOCK", "PEDIDOS"],
    }
    r = client.post(f"{API}/usuarios", json=body)
    assert r.status_code == 201
    assert r.json()["roles"] == ["PEDIDOS", "STOCK"] and r.json()["email"] == "sofia@test.com"
    assert "password" not in r.text

    with TestClient(app) as otro:  # la contraseña indicada funciona para iniciar sesión
        assert login(otro, "sofia@test.com", PASSWORD).status_code == 200

    assert client.post(f"{API}/usuarios", json=body).json()["code"] == "EMAIL_TAKEN"
    assert client.post(f"{API}/usuarios", json={**body, "email": "x@test.com", "roles": ["HACKER"]}).status_code == 422
    assert client.post(f"{API}/usuarios", json={**body, "email": "y@test.com", "password": "debil"}).status_code == 422
    assert client.post(f"{API}/usuarios", json={**body, "email": "z@test.com", "roles": []}).status_code == 422


def test_el_alta_de_usuarios_es_solo_para_admin(client):
    registrar_y_loguear(client)
    body = {"nombre": "A", "apellido": "B", "email": "a@test.com", "password": PASSWORD, "roles": ["CLIENT"]}
    assert client.post(f"{API}/usuarios", json=body).status_code == 403
