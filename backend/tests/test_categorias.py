"""Categorías (sección 6.3): árbol, baja lógica validada y ABM."""

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from tests.helpers import API, login_admin, registrar_y_loguear


def crear(client: TestClient, nombre: str, parent_id: int | None = None) -> dict:
    r = client.post(f"{API}/categorias", json={"nombre": nombre, "parent_id": parent_id})
    assert r.status_code == 201, r.text
    return r.json()


def test_arbol_publico_anidado_y_ordenado(client):
    login_admin(client)
    comidas = crear(client, "Comidas")
    crear(client, "Bebidas")
    pizzas = crear(client, "Pizzas", comidas["id"])
    crear(client, "Muzzarella", pizzas["id"])
    crear(client, "Empanadas", comidas["id"])

    with TestClient(app) as anon:  # público: sin sesión
        arbol = anon.get(f"{API}/categorias").json()
    assert [n["nombre"] for n in arbol] == ["Bebidas", "Comidas"]
    comidas_n = arbol[1]
    assert [h["nombre"] for h in comidas_n["children"]] == ["Empanadas", "Pizzas"]
    assert comidas_n["children"][1]["children"][0]["nombre"] == "Muzzarella"


def test_el_arbol_excluye_dadas_de_baja_y_sus_descendientes(client):
    login_admin(client)
    a = crear(client, "A")
    b = crear(client, "B", a["id"])
    assert client.delete(f"{API}/categorias/{b['id']}").status_code == 204
    assert client.delete(f"{API}/categorias/{a['id']}").status_code == 204
    assert client.get(f"{API}/categorias").json() == []


def test_baja_falla_con_409_si_tiene_subcategorias_activas(client):
    login_admin(client)
    padre = crear(client, "Padre")
    hija = crear(client, "Hija", padre["id"])
    r = client.delete(f"{API}/categorias/{padre['id']}")
    assert r.status_code == 409 and r.json()["code"] == "CATEGORY_HAS_CHILDREN"

    client.delete(f"{API}/categorias/{hija['id']}")  # sin hijas activas, ahora sí se puede
    assert client.delete(f"{API}/categorias/{padre['id']}").status_code == 204


def test_baja_falla_con_409_si_tiene_productos_activos(client, session_factory):
    login_admin(client)
    cat = crear(client, "Con productos")
    with session_factory() as s:
        pid = s.exec(
            text(  # type: ignore[call-overload]
                "insert into producto (nombre, precio_base) values ('Pizza', 100) returning id"
            )
        ).one()[0]
        s.exec(
            text("insert into producto_categoria (producto_id, cat_id) values (:p, :c)"),
            params={"p": pid, "c": cat["id"]},
        )  # type: ignore[call-overload]
        s.commit()

    r = client.delete(f"{API}/categorias/{cat['id']}")
    assert r.status_code == 409 and r.json()["code"] == "CATEGORY_HAS_PRODUCTS"

    with session_factory() as s:  # el producto se da de baja: ya no bloquea
        s.exec(text("update producto set deleted_at = now() where id = :p"), params={"p": pid})  # type: ignore[call-overload]
        s.commit()
    assert client.delete(f"{API}/categorias/{cat['id']}").status_code == 204


def test_validaciones_de_alta_y_edicion(client):
    login_admin(client)
    raiz = crear(client, "Raiz")
    hija = crear(client, "Hija", raiz["id"])

    assert client.post(f"{API}/categorias", json={"nombre": "X", "parent_id": 99999}).json()["code"] == "INVALID_PARENT"
    assert client.post(f"{API}/categorias", json={"nombre": "   "}).status_code == 422
    dup = client.post(f"{API}/categorias", json={"nombre": "raiz"})  # mismo nombre, mismo nivel, distinto caso
    assert dup.status_code == 409 and dup.json()["code"] == "DUPLICATE_NAME"
    crear(client, "Hija")  # mismo nombre pero en otro nivel: permitido

    # Ciclos: no puede ser su propio padre ni colgar de un descendiente.
    assert (
        client.put(f"{API}/categorias/{raiz['id']}", json={"parent_id": raiz["id"]}).json()["code"] == "CATEGORY_CYCLE"
    )
    assert (
        client.put(f"{API}/categorias/{raiz['id']}", json={"parent_id": hija["id"]}).json()["code"] == "CATEGORY_CYCLE"
    )


def test_mover_a_la_raiz_requiere_parent_id_null_explicito(client):
    login_admin(client)
    raiz = crear(client, "Raiz")
    hija = crear(client, "Hija", raiz["id"])

    r = client.put(f"{API}/categorias/{hija['id']}", json={"descripcion": "Solo descripción"})
    assert r.json()["parent_id"] == raiz["id"]  # parent_id omitido: no cambia

    r = client.put(f"{API}/categorias/{hija['id']}", json={"parent_id": None})
    assert r.json()["parent_id"] is None


def test_lista_plana_para_el_abm_con_filtros(client):
    login_admin(client)
    for n in ("Pizzas", "Pastas", "Postres"):
        crear(client, n)
    baja = crear(client, "Pasteles")
    client.delete(f"{API}/categorias/{baja['id']}")

    r = client.get(f"{API}/categorias/lista", params={"search": "pa"}).json()
    assert [c["nombre"] for c in r["items"]] == ["Pastas"]  # activos por defecto
    assert client.get(f"{API}/categorias/lista", params={"estado": "inactivos"}).json()["total"] == 1
    assert client.get(f"{API}/categorias/lista", params={"estado": "todos"}).json()["total"] == 4
    assert client.get(f"{API}/categorias/lista", params={"size": 2}).json()["pages"] == 2


def test_reactivar(client):
    login_admin(client)
    padre = crear(client, "Padre")
    hija = crear(client, "Hija", padre["id"])
    client.delete(f"{API}/categorias/{hija['id']}")
    client.delete(f"{API}/categorias/{padre['id']}")

    r = client.patch(f"{API}/categorias/{hija['id']}/reactivar")
    assert r.status_code == 409 and r.json()["code"] == "PARENT_INACTIVE"
    assert client.patch(f"{API}/categorias/{padre['id']}/reactivar").json()["deleted_at"] is None
    assert client.patch(f"{API}/categorias/{hija['id']}/reactivar").status_code == 200


def test_el_abm_es_solo_para_admin(client):
    registrar_y_loguear(client)
    assert client.post(f"{API}/categorias", json={"nombre": "X"}).status_code == 403
    assert client.delete(f"{API}/categorias/1").status_code == 403
    assert client.get(f"{API}/categorias/lista").status_code == 403
    assert client.get(f"{API}/categorias").status_code == 200  # el árbol sí es público


def test_la_lista_incluye_el_nombre_del_padre_aunque_este_en_otra_pagina(client):
    login_admin(client)
    padre = crear(client, "Aaa padre")
    for n in ("Bbb 1", "Bbb 2", "Bbb 3"):
        crear(client, n, padre["id"])

    # size=2 deja al padre en la página 1 y a "Bbb 3" en la 2: igual debe traer el nombre del padre.
    pagina2 = client.get(f"{API}/categorias/lista", params={"size": 2, "page": 2}).json()["items"]
    assert pagina2, "se esperaba una segunda página"
    hijas = [c for c in pagina2 if c["parent_id"] == padre["id"]]
    assert hijas and all(c["parent_nombre"] == "Aaa padre" for c in hijas)
    assert all(c["parent_nombre"] is None for c in pagina2 if c["parent_id"] is None)
