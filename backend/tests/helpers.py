from fastapi.testclient import TestClient

API = "/api/v1"
PASSWORD = "Password-Segura-1"
ADMIN = ("admin@foodstore.com", "FoodStore2026!")


def login(client: TestClient, email: str, password: str):
    return client.post(f"{API}/auth/token", data={"username": email, "password": password})


def login_admin(client: TestClient) -> TestClient:
    assert login(client, *ADMIN).status_code == 200
    return client


def registrar_y_loguear(client: TestClient, email: str = "cliente@test.com") -> dict:
    body = {"nombre": "Ana", "apellido": "Pérez", "email": email, "password": PASSWORD}
    r = client.post(f"{API}/auth/register", json=body)
    assert r.status_code == 201, r.text
    assert login(client, email, PASSWORD).status_code == 200
    return r.json()
