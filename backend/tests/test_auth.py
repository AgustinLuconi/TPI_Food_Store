"""Autenticación y autorización (secciones 5 y 6.1)."""

from fastapi.testclient import TestClient

from app.main import app

API = "/api/v1"
PASSWORD = "Password-Segura-1"
ADMIN = ("admin@foodstore.com", "FoodStore2026!")


def registrar(client: TestClient, email: str = "cliente@test.com", password: str = PASSWORD, **extra):
    body = {"nombre": "Ana", "apellido": "Pérez", "email": email, "password": password, **extra}
    return client.post(f"{API}/auth/register", json=body)


def login(client: TestClient, email: str, password: str):
    return client.post(f"{API}/auth/token", data={"username": email, "password": password})


# --- Registro -------------------------------------------------------------------------------


def test_registro_asigna_cliente_y_no_expone_el_hash(client):
    r = registrar(client)
    assert r.status_code == 201
    body = r.json()
    assert body["roles"] == ["CLIENT"]
    assert "password" not in body and "password_hash" not in body


def test_registro_publico_ignora_roles_enviados(client):
    """RN-15: aunque el body traiga roles, el registro público siempre asigna CLIENT."""
    r = registrar(client, roles=["ADMIN"])
    assert r.status_code == 201
    assert r.json()["roles"] == ["CLIENT"]


def test_registro_email_duplicado_devuelve_409(client):
    registrar(client)
    r = registrar(client, email="CLIENTE@test.com")  # mismo email, distinto caso
    assert r.status_code == 409
    assert r.json()["code"] == "EMAIL_TAKEN"


def test_registro_valida_politica_de_contrasenia(client):
    for debil in ("corta1!A", "sinmayuscula-123!", "SinDigitoAqui-!!", "SinEspecial1234A"):
        r = registrar(client, password=debil)
        assert r.status_code == 422, debil
        assert r.json()["field"] == "password"
        assert r.json()["code"] == "VALIDATION_ERROR"


# --- Login y cookies ------------------------------------------------------------------------


def test_login_deja_cookies_httponly_y_no_devuelve_tokens_en_el_cuerpo(client):
    registrar(client)
    r = login(client, "cliente@test.com", PASSWORD)
    assert r.status_code == 200
    assert "token" not in r.text.lower()
    cookies = r.headers.get_list("set-cookie")
    assert len(cookies) == 2
    for c in cookies:
        assert "HttpOnly" in c and "SameSite=lax" in c
    assert any(c.startswith("access_token=") for c in cookies)
    assert any(c.startswith("refresh_token=") and "Path=/api/v1/auth" in c for c in cookies)


def test_login_con_credenciales_invalidas_devuelve_401_generico(client):
    registrar(client)
    mala_clave = login(client, "cliente@test.com", "Otra-Clave-123!")
    sin_usuario = login(client, "noexiste@test.com", PASSWORD)
    assert mala_clave.status_code == sin_usuario.status_code == 401
    assert mala_clave.json() == sin_usuario.json()  # no revela si el email existe
    assert "Bearer" in mala_clave.headers["www-authenticate"]


def test_login_de_usuario_bloqueado_devuelve_400(client):
    registrar(client)
    login(client, *ADMIN)
    uid = next(u["id"] for u in client.get(f"{API}/usuarios").json()["items"] if u["email"] == "cliente@test.com")
    assert client.patch(f"{API}/usuarios/{uid}/estado", json={"disabled": True}).status_code == 200

    with TestClient(app) as otro:
        r = login(otro, "cliente@test.com", PASSWORD)
    assert r.status_code == 400
    assert r.json()["code"] == "ACCOUNT_DISABLED"


def test_login_exceso_de_intentos_fallidos_devuelve_429_con_retry_after(client):
    for _ in range(5):
        assert login(client, "x@test.com", "Mala-Clave-123!").status_code == 401
    r = login(client, "x@test.com", "Mala-Clave-123!")
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) > 0
    assert r.json()["code"] == "TOO_MANY_LOGIN_ATTEMPTS"


def test_login_exitoso_no_consume_el_limite(client):
    registrar(client)
    for _ in range(4):
        login(client, "cliente@test.com", "Mala-Clave-123!")
    assert login(client, "cliente@test.com", PASSWORD).status_code == 200


# --- Sesión ---------------------------------------------------------------------------------


def test_me_sin_cookie_devuelve_401(client):
    r = client.get(f"{API}/auth/me")
    assert r.status_code == 401
    assert r.json()["code"] == "NOT_AUTHENTICATED"
    assert "Bearer" in r.headers["www-authenticate"]


def test_me_con_token_basura_devuelve_401(client):
    client.cookies.set("access_token", "no-es-un-jwt")
    assert client.get(f"{API}/auth/me").status_code == 401


def test_me_devuelve_el_usuario_con_sus_roles(client):
    registrar(client)
    login(client, "cliente@test.com", PASSWORD)
    r = client.get(f"{API}/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "cliente@test.com" and r.json()["roles"] == ["CLIENT"]


def test_refresh_rota_el_token_y_revoca_el_anterior(client):
    registrar(client)
    login(client, "cliente@test.com", PASSWORD)
    viejo = client.cookies.get("refresh_token", path="/api/v1/auth")

    assert client.post(f"{API}/auth/refresh").status_code == 200
    nuevo = client.cookies.get("refresh_token", path="/api/v1/auth")
    assert nuevo and nuevo != viejo

    with TestClient(app) as atacante:  # reutiliza el refresh token ya rotado
        atacante.cookies.set("refresh_token", viejo, path="/api/v1/auth")
        assert atacante.post(f"{API}/auth/refresh").status_code == 401


def test_refresh_sin_cookie_devuelve_401(client):
    assert client.post(f"{API}/auth/refresh").status_code == 401


def test_logout_borra_cookies_y_revoca_el_refresh_token(client):
    registrar(client)
    login(client, "cliente@test.com", PASSWORD)
    refresh_token = client.cookies.get("refresh_token", path="/api/v1/auth")

    r = client.post(f"{API}/auth/logout")
    assert r.status_code == 204

    with TestClient(app) as otro:
        otro.cookies.set("refresh_token", refresh_token, path="/api/v1/auth")
        assert otro.post(f"{API}/auth/refresh").status_code == 401


def test_logout_requiere_autenticacion(client):
    assert client.post(f"{API}/auth/logout").status_code == 401


# --- Cambio de contraseña -------------------------------------------------------------------


def test_cambio_de_contrasenia(client):
    registrar(client)
    login(client, "cliente@test.com", PASSWORD)
    nueva = "Nueva-Clave-Segura-9"

    assert (
        client.put(f"{API}/auth/password", json={"password_actual": "incorrecta", "password_nueva": nueva}).json()[
            "code"
        ]
        == "WRONG_PASSWORD"
    )
    assert (
        client.put(f"{API}/auth/password", json={"password_actual": PASSWORD, "password_nueva": "debil"}).status_code
        == 422
    )

    assert (
        client.put(f"{API}/auth/password", json={"password_actual": PASSWORD, "password_nueva": nueva}).status_code
        == 200
    )
    assert client.get(f"{API}/auth/me").status_code == 200  # la sesión actual sigue activa

    with TestClient(app) as otro:
        assert login(otro, "cliente@test.com", PASSWORD).status_code == 401
        assert login(otro, "cliente@test.com", nueva).status_code == 200


# --- Autorización por rol -------------------------------------------------------------------


def test_cliente_recibe_403_en_endpoints_de_admin(client):
    registrar(client)
    login(client, "cliente@test.com", PASSWORD)
    r = client.get(f"{API}/usuarios")
    assert r.status_code == 403
    assert r.json()["code"] == "INSUFFICIENT_ROLE"


def test_quitar_un_rol_rige_desde_el_siguiente_request(client):
    """Invariante de seguridad: el rol se verifica contra la base, no contra el token."""
    registrar(client, email="jefe@test.com")
    login(client, *ADMIN)
    jefe_id = next(u["id"] for u in client.get(f"{API}/usuarios").json()["items"] if u["email"] == "jefe@test.com")
    assert client.put(f"{API}/usuarios/{jefe_id}/roles", json={"roles": ["ADMIN"]}).status_code == 200

    with TestClient(app) as jefe:
        login(jefe, "jefe@test.com", PASSWORD)
        assert jefe.get(f"{API}/usuarios").status_code == 200  # el token ya existe y es válido

        assert client.put(f"{API}/usuarios/{jefe_id}/roles", json={"roles": ["CLIENT"]}).status_code == 200
        assert jefe.get(f"{API}/usuarios").status_code == 403  # mismo token, rol nuevo
