"""Catálogo (sección 6.3): productos, ingredientes, recetas (RN-10, RN-11) e imágenes."""

import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.modules.productos.recetas import hay_ciclo
from tests.helpers import API, PASSWORD, login, login_admin, registrar_y_loguear

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"0" * 64


# ----------------------------------------------------------------------------------------------
# Ayudas
# ----------------------------------------------------------------------------------------------


def categoria(client: TestClient, nombre: str, parent_id: int | None = None) -> int:
    r = client.post(f"{API}/categorias", json={"nombre": nombre, "parent_id": parent_id})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def producto(client: TestClient, nombre: str = "Pizza", precio: str = "9500.00", **extra) -> dict:
    r = client.post(f"{API}/productos", json={"nombre": nombre, "precio_base": precio, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def ingrediente(client: TestClient, nombre: str, **extra) -> dict:
    # La unidad se define al crear el ingrediente (RN-10); por defecto KG, salvo que el test pida otra.
    r = client.post(f"{API}/ingredientes", json={"nombre": nombre, "unidad_medida": "KG", **extra})
    assert r.status_code == 201, r.text
    return r.json()


def cliente_con_rol(admin: TestClient, rol: str, email: str) -> TestClient:
    """Un cliente HTTP nuevo, logueado con un usuario del rol indicado (lo da de alta el ADMIN)."""
    body = {"nombre": "Test", "apellido": rol, "email": email, "password": PASSWORD, "roles": [rol]}
    assert admin.post(f"{API}/usuarios", json=body).status_code == 201
    otro = TestClient(app)
    assert login(otro, email, PASSWORD).status_code == 200
    return otro


def ids(items: list[dict]) -> list[int]:
    return [i["id"] for i in items]


# ----------------------------------------------------------------------------------------------
# Productos
# ----------------------------------------------------------------------------------------------


def test_abm_de_productos_es_solo_para_admin(client):
    registrar_y_loguear(client)  # CLIENT
    assert client.post(f"{API}/productos", json={"nombre": "X", "precio_base": "1"}).status_code == 403
    assert client.put(f"{API}/productos/1", json={"nombre": "X"}).status_code == 403
    assert client.delete(f"{API}/productos/1").status_code == 403
    assert client.put(f"{API}/productos/1/ingredientes", json={"items": []}).status_code == 403
    assert client.get(f"{API}/productos").status_code == 200  # el catálogo es público


def test_crear_producto_con_categorias_y_principal(client):
    login_admin(client)
    comidas, pizzas = categoria(client, "Comidas"), categoria(client, "Pizzas")

    p = producto(client, categoria_ids=[comidas, pizzas], categoria_principal_id=pizzas)
    assert p["precio_base"] == "9500.00" and p["disponible"] is True and p["imagen_url"] is None
    principales = {c["nombre"]: c["es_principal"] for c in p["categorias"]}
    assert principales == {"Comidas": False, "Pizzas": True}

    # sin principal explícita, lo es la primera
    q = producto(client, "Empanada", categoria_ids=[comidas, pizzas])
    assert [c["nombre"] for c in q["categorias"] if c["es_principal"]] == ["Comidas"]


def test_validaciones_de_alta(client):
    login_admin(client)
    assert client.post(f"{API}/productos", json={"nombre": "X", "precio_base": "-1"}).status_code == 422
    assert client.post(f"{API}/productos", json={"nombre": "X", "precio_base": "10.123"}).status_code == 422
    assert client.post(f"{API}/productos", json={"nombre": "  ", "precio_base": "1"}).status_code == 422
    assert (
        client.post(f"{API}/productos", json={"nombre": "X", "precio_base": "1", "stock_minimo": -1}).status_code == 422
    )
    r = client.post(f"{API}/productos", json={"nombre": "X", "precio_base": "1", "categoria_ids": [999999]})
    assert r.status_code == 422 and r.json()["code"] == "INVALID_CATEGORY"
    r = client.post(
        f"{API}/productos",
        json={"nombre": "X", "precio_base": "1", "categoria_ids": [], "categoria_principal_id": 5},
    )
    assert r.status_code == 422  # la principal debe estar entre las categorías


def test_no_se_puede_clasificar_en_una_categoria_dada_de_baja(client):
    login_admin(client)
    baja = categoria(client, "Vieja")
    client.delete(f"{API}/categorias/{baja}")
    r = client.post(f"{API}/productos", json={"nombre": "X", "precio_base": "1", "categoria_ids": [baja]})
    assert r.status_code == 422 and r.json()["field"] == "categoria_ids"


def test_edicion_parcial_y_reemplazo_de_categorias(client):
    login_admin(client)
    a, b = categoria(client, "A"), categoria(client, "B")
    p = producto(client, categoria_ids=[a])

    r = client.put(f"{API}/productos/{p['id']}", json={"precio_base": "12000.50"})
    assert r.json()["precio_base"] == "12000.50" and r.json()["nombre"] == "Pizza"
    assert [c["nombre"] for c in r.json()["categorias"]] == ["A"]  # sin categoria_ids: no cambian

    r = client.put(f"{API}/productos/{p['id']}", json={"categoria_ids": [b]})
    assert [c["nombre"] for c in r.json()["categorias"]] == ["B"]
    assert client.put(f"{API}/productos/{p['id']}", json={"nombre": None}).status_code == 422
    assert client.put(f"{API}/productos/999999", json={"nombre": "X"}).status_code == 404


def test_el_listado_publico_oculta_los_dados_de_baja_y_la_gestion_los_ve(client):
    login_admin(client)
    activo, viejo = producto(client, "Activo"), producto(client, "Viejo")
    assert client.delete(f"{API}/productos/{viejo['id']}").status_code == 204

    anonimo = TestClient(app)
    assert ids(anonimo.get(f"{API}/productos").json()["items"]) == [activo["id"]]
    # incluir_inactivos y estado solo rigen para los roles de gestión: el público sigue viendo activos
    assert ids(anonimo.get(f"{API}/productos", params={"incluir_inactivos": True}).json()["items"]) == [activo["id"]]
    assert anonimo.get(f"{API}/productos/{viejo['id']}").status_code == 404

    assert ids(client.get(f"{API}/productos", params={"incluir_inactivos": True}).json()["items"]) == [
        activo["id"],
        viejo["id"],
    ]
    assert ids(client.get(f"{API}/productos", params={"estado": "inactivos"}).json()["items"]) == [viejo["id"]]
    assert client.get(f"{API}/productos/{viejo['id']}").json()["deleted_at"] is not None


def test_la_baja_deja_el_producto_no_disponible_y_se_puede_reactivar(client):
    login_admin(client)
    p = producto(client)
    assert client.delete(f"{API}/productos/{p['id']}").status_code == 204
    detalle = client.get(f"{API}/productos/{p['id']}").json()
    assert detalle["disponible"] is False and detalle["deleted_at"] is not None
    assert client.delete(f"{API}/productos/{p['id']}").status_code == 404  # ya está de baja

    r = client.patch(f"{API}/productos/{p['id']}/reactivar")
    assert r.status_code == 200 and r.json()["deleted_at"] is None
    assert r.json()["disponible"] is False  # vuelve oculto: habilitarlo es decisión comercial
    assert client.patch(f"{API}/productos/{p['id']}/reactivar").status_code == 409


def test_filtros_busqueda_disponibilidad_orden_y_categoria_con_subcategorias(client):
    login_admin(client)
    comidas = categoria(client, "Comidas")
    pizzas = categoria(client, "Pizzas", comidas)
    bebidas = categoria(client, "Bebidas")
    muzza = producto(client, "Pizza muzzarella", "9500", categoria_ids=[pizzas])
    coca = producto(client, "Coca Cola", "2500", categoria_ids=[bebidas], disponible=False)
    flan = producto(client, "Flan", "4000", categoria_ids=[comidas])

    def listar(**params):
        return ids(client.get(f"{API}/productos", params=params).json()["items"])

    assert listar(search="piz") == [muzza["id"]]
    assert listar(disponible=False) == [coca["id"]]
    assert listar(disponible=True) == [flan["id"], muzza["id"]]  # por nombre
    # "Comidas" incluye a sus subcategorías (las pizzas)
    assert sorted(listar(categoria_id=comidas)) == sorted([muzza["id"], flan["id"]])
    assert listar(categoria_id=pizzas) == [muzza["id"]]
    assert listar(orden="precio") == [coca["id"], flan["id"], muzza["id"]]
    assert listar(orden="precio", sentido="desc") == [muzza["id"], flan["id"], coca["id"]]
    assert client.get(f"{API}/productos", params={"orden": "stock"}).status_code == 422

    pagina = client.get(f"{API}/productos", params={"size": 2, "page": 2}).json()
    assert pagina["total"] == 3 and pagina["pages"] == 2 and len(pagina["items"]) == 1


def test_la_disponibilidad_la_cambian_admin_y_stock(client):
    login_admin(client)
    p = producto(client)
    stock = cliente_con_rol(client, "STOCK", "stock@test.com")
    pedidos = cliente_con_rol(client, "PEDIDOS", "pedidos@test.com")

    r = stock.patch(f"{API}/productos/{p['id']}/disponibilidad", json={"disponible": False})
    assert r.status_code == 200 and r.json()["disponible"] is False
    assert client.patch(f"{API}/productos/{p['id']}/disponibilidad", json={"disponible": True}).json()["disponible"]
    assert pedidos.patch(f"{API}/productos/{p['id']}/disponibilidad", json={"disponible": False}).status_code == 403
    assert (
        TestClient(app).patch(f"{API}/productos/{p['id']}/disponibilidad", json={"disponible": False}).status_code
        == 401
    )


def test_stock_ve_los_dados_de_baja_pero_no_edita_el_catalogo(client):
    login_admin(client)
    p = producto(client)
    client.delete(f"{API}/productos/{p['id']}")
    stock = cliente_con_rol(client, "STOCK", "stock@test.com")
    assert ids(stock.get(f"{API}/productos", params={"estado": "todos"}).json()["items"]) == [p["id"]]
    assert stock.post(f"{API}/productos", json={"nombre": "X", "precio_base": "1"}).status_code == 403


# ----------------------------------------------------------------------------------------------
# Imágenes
# ----------------------------------------------------------------------------------------------


def subir(client: TestClient, producto_id: int, contenido: bytes, nombre: str = "foto.png", tipo: str = "image/png"):
    return client.post(f"{API}/productos/{producto_id}/imagen", files={"archivo": (nombre, contenido, tipo)})


def archivo_de(url: str) -> Path:
    return Path(os.environ["MEDIA_DIR"]) / url.removeprefix("/media/")


def test_subir_imagen_valida_renombra_con_uuid_y_guarda_solo_la_url(client):
    login_admin(client)
    p = producto(client)
    for contenido, nombre, ext in ((PNG, "mi foto.png", "png"), (JPEG, "x.jpeg", "jpg"), (WEBP, "y.webp", "webp")):
        r = subir(client, p["id"], contenido, nombre)
        assert r.status_code == 200, r.text
        url = r.json()["imagen_url"]
        assert url.startswith("/media/productos/") and url.endswith(f".{ext}")
        assert nombre.split(".")[0] not in url  # el nombre original no se conserva
        assert archivo_de(url).read_bytes() == contenido
        # el archivo se sirve como estático
        assert client.get(url).status_code == 200


def test_la_imagen_se_valida_por_su_contenido_no_por_la_extension(client):
    login_admin(client)
    p = producto(client)
    falsa = subir(client, p["id"], b"<?php echo 1; ?>", "malicioso.png", "image/png")
    assert falsa.status_code == 422 and falsa.json()["code"] == "INVALID_IMAGE_TYPE"
    # un PNG real con extensión y content-type engañosos sí es válido: manda la firma
    assert subir(client, p["id"], PNG, "foto.txt", "text/plain").status_code == 200
    assert subir(client, p["id"], b"", "vacio.png").json()["code"] == "EMPTY_FILE"


def test_la_imagen_no_puede_superar_2_mb(client):
    login_admin(client)
    p = producto(client)
    justo = PNG + b"0" * (2 * 1024 * 1024 - len(PNG))
    assert subir(client, p["id"], justo).status_code == 200
    r = subir(client, p["id"], justo + b"0")
    assert r.status_code == 422 and r.json()["code"] == "FILE_TOO_LARGE"


def test_al_reemplazar_la_imagen_se_borra_la_anterior(client):
    login_admin(client)
    p = producto(client)
    primera = subir(client, p["id"], PNG).json()["imagen_url"]
    segunda = subir(client, p["id"], JPEG).json()["imagen_url"]
    assert primera != segunda
    assert not archivo_de(primera).exists() and archivo_de(segunda).exists()


def test_subir_imagen_es_solo_admin_y_el_producto_debe_existir(client):
    login_admin(client)
    p = producto(client)
    assert subir(client, 999999, PNG).status_code == 404
    stock = cliente_con_rol(client, "STOCK", "stock@test.com")
    assert subir(stock, p["id"], PNG).status_code == 403
    assert subir(TestClient(app), p["id"], PNG).status_code == 401


# ----------------------------------------------------------------------------------------------
# Ingredientes
# ----------------------------------------------------------------------------------------------


def test_abm_de_ingredientes_admin_escribe_y_stock_lee(client):
    login_admin(client)
    harina = ingrediente(client, "Harina", es_alergeno=True, stock_minimo=5)
    assert harina["es_alergeno"] is True and harina["es_elaborado"] is False

    stock = cliente_con_rol(client, "STOCK", "stock@test.com")
    assert stock.get(f"{API}/ingredientes").status_code == 200
    assert stock.get(f"{API}/ingredientes/{harina['id']}").status_code == 200
    assert stock.post(f"{API}/ingredientes", json={"nombre": "X"}).status_code == 403
    assert stock.put(f"{API}/ingredientes/{harina['id']}", json={"nombre": "X"}).status_code == 403
    assert stock.get(f"{API}/ingredientes/{harina['id']}/receta").status_code == 403

    cliente = TestClient(app)
    registrar_y_loguear(cliente, "cli@test.com")
    assert cliente.get(f"{API}/ingredientes").status_code == 403
    assert TestClient(app).get(f"{API}/ingredientes").status_code == 401


def test_el_nombre_del_ingrediente_es_unico_incluso_tras_la_baja(client):
    login_admin(client)
    queso = ingrediente(client, "Queso")
    r = client.post(f"{API}/ingredientes", json={"nombre": "queso"})  # sin distinguir mayúsculas
    assert r.status_code == 409 and r.json()["code"] == "DUPLICATE_NAME"

    client.delete(f"{API}/ingredientes/{queso['id']}")
    r = client.post(f"{API}/ingredientes", json={"nombre": "Queso"})
    assert r.status_code == 409 and r.json()["code"] == "INGREDIENT_INACTIVE_NAME"  # se ofrece reactivar

    r = client.patch(f"{API}/ingredientes/{queso['id']}/reactivar")
    assert r.status_code == 200 and r.json()["deleted_at"] is None
    assert client.patch(f"{API}/ingredientes/{queso['id']}/reactivar").status_code == 409

    otro = ingrediente(client, "Jamón")
    assert client.put(f"{API}/ingredientes/{otro['id']}", json={"nombre": "Queso"}).status_code == 409
    assert client.put(f"{API}/ingredientes/{otro['id']}", json={"nombre": "Jamón"}).status_code == 200  # el suyo, no


def test_listado_de_ingredientes_con_filtros_y_estado(client):
    login_admin(client)
    ingrediente(client, "Harina", es_alergeno=True)
    salsa = ingrediente(client, "Salsa base", es_elaborado=True)
    viejo = ingrediente(client, "Viejo")
    client.delete(f"{API}/ingredientes/{viejo['id']}")

    def nombres(**params):
        return [i["nombre"] for i in client.get(f"{API}/ingredientes", params=params).json()["items"]]

    assert nombres() == ["Harina", "Salsa base"]
    assert nombres(estado="inactivos") == ["Viejo"]
    assert nombres(estado="todos", sentido="desc") == ["Viejo", "Salsa base", "Harina"]
    assert nombres(es_alergeno=True) == ["Harina"]
    assert nombres(es_elaborado=True) == [salsa["nombre"]]
    assert nombres(search="sal") == ["Salsa base"]


def test_no_se_anula_un_ingrediente_que_esta_en_una_receta_activa(client):
    login_admin(client)
    harina, salsa = ingrediente(client, "Harina"), ingrediente(client, "Salsa", es_elaborado=True)
    tomate = ingrediente(client, "Tomate")
    p = producto(client)
    client.put(
        f"{API}/productos/{p['id']}/ingredientes",
        json={"items": [{"ingrediente_id": harina["id"], "cantidad_requerida": "1"}]},
    )
    client.put(
        f"{API}/ingredientes/{salsa['id']}/receta",
        json={"items": [{"componente_id": tomate["id"], "cantidad_requerida": "1"}]},
    )

    r = client.delete(f"{API}/ingredientes/{harina['id']}")
    assert r.status_code == 409 and r.json()["code"] == "INGREDIENT_IN_USE"
    assert client.delete(f"{API}/ingredientes/{tomate['id']}").status_code == 409  # lo usa un elaborado

    client.delete(f"{API}/productos/{p['id']}")  # ya no hay productos activos que lo usen
    assert client.delete(f"{API}/ingredientes/{harina['id']}").status_code == 204


def test_un_ingrediente_con_receta_no_deja_de_ser_elaborado(client):
    login_admin(client)
    salsa, tomate = ingrediente(client, "Salsa", es_elaborado=True), ingrediente(client, "Tomate")
    client.put(
        f"{API}/ingredientes/{salsa['id']}/receta",
        json={"items": [{"componente_id": tomate["id"], "cantidad_requerida": "2"}]},
    )
    r = client.put(f"{API}/ingredientes/{salsa['id']}", json={"es_elaborado": False})
    assert r.status_code == 409 and r.json()["code"] == "HAS_RECIPE"
    client.put(f"{API}/ingredientes/{salsa['id']}/receta", json={"items": []})  # vaciada, ya puede
    assert client.put(f"{API}/ingredientes/{salsa['id']}", json={"es_elaborado": False}).status_code == 200


# ----------------------------------------------------------------------------------------------
# Receta de venta
# ----------------------------------------------------------------------------------------------


def item(ing_id: int, cantidad: str = "1", unidad: str | None = None, removible: bool = True) -> dict:
    fila = {"ingrediente_id": ing_id, "cantidad_requerida": cantidad, "es_removible": removible}
    if unidad is not None:  # si se omite, la receta toma la unidad del ingrediente
        fila["unidad_medida"] = unidad
    return fila


def test_receta_de_venta_con_alergenos_y_lectura_publica(client):
    login_admin(client)
    harina = ingrediente(client, "Harina", es_alergeno=True)
    cebolla = ingrediente(client, "Cebolla")
    p = producto(client)

    r = client.put(
        f"{API}/productos/{p['id']}/ingredientes",
        json={"items": [item(harina["id"], "0.300", "kg", removible=False), item(cebolla["id"], "0.050", "KG")]},
    )
    assert r.status_code == 200, r.text
    por_nombre = {i["nombre"]: i for i in r.json()}
    assert por_nombre["Harina"]["unidad_medida"] == "KG"  # se normaliza a mayúsculas
    assert por_nombre["Harina"]["es_removible"] is False and por_nombre["Cebolla"]["es_removible"] is True

    anonimo = TestClient(app)
    assert len(anonimo.get(f"{API}/productos/{p['id']}/ingredientes").json()) == 2
    detalle = anonimo.get(f"{API}/productos/{p['id']}").json()
    assert detalle["alergenos"] == ["Harina"] and len(detalle["ingredientes"]) == 2

    # PUT reemplaza: la receta nueva es solo la enviada
    r = client.put(f"{API}/productos/{p['id']}/ingredientes", json={"items": [item(cebolla["id"], "0.1", "KG")]})
    assert [i["nombre"] for i in r.json()] == ["Cebolla"]
    assert anonimo.get(f"{API}/productos/{p['id']}").json()["alergenos"] == []


def test_validaciones_de_la_receta_de_venta(client):
    login_admin(client)
    harina, viejo = ingrediente(client, "Harina"), ingrediente(client, "Viejo")
    client.delete(f"{API}/ingredientes/{viejo['id']}")
    p = producto(client)
    url = f"{API}/productos/{p['id']}/ingredientes"

    r = client.put(url, json={"items": [item(harina["id"]), item(harina["id"])]})
    assert r.status_code == 422 and r.json()["code"] == "DUPLICATE_INGREDIENT"
    assert client.put(url, json={"items": [item(999999)]}).json()["code"] == "UNKNOWN_INGREDIENT"
    assert client.put(url, json={"items": [item(viejo["id"])]}).json()["code"] == "UNKNOWN_INGREDIENT"  # dado de baja
    assert client.put(url, json={"items": [item(harina["id"], "0")]}).status_code == 422  # cantidad > 0
    assert client.put(url, json={"items": [item(harina["id"], "-1")]}).status_code == 422
    assert client.put(f"{API}/productos/999999/ingredientes", json={"items": []}).status_code == 404


def test_rn10_la_unidad_se_define_al_crear_el_ingrediente(client):
    login_admin(client)
    # Sin indicarla se mide en UN (el valor por defecto del ERD); se normaliza a mayúsculas.
    sin_unidad = client.post(f"{API}/ingredientes", json={"nombre": "Caja"})
    assert sin_unidad.status_code == 201 and sin_unidad.json()["unidad_medida"] == "UN"
    assert ingrediente(client, "Harina", unidad_medida="kg")["unidad_medida"] == "KG"
    # La unidad no puede quedar vacía.
    assert client.post(f"{API}/ingredientes", json={"nombre": "Sal", "unidad_medida": "  "}).status_code == 422
    # La lectura la devuelve.
    por_nombre = {i["nombre"]: i["unidad_medida"] for i in client.get(f"{API}/ingredientes").json()["items"]}
    assert por_nombre == {"Caja": "UN", "Harina": "KG"}


def test_rn10_las_recetas_toman_la_unidad_del_ingrediente(client):
    login_admin(client)
    harina = ingrediente(client, "Harina")  # KG
    pizza, pan = producto(client, "Pizza"), producto(client, "Pan")

    # Sin enviar la unidad, la receta queda en la del ingrediente.
    r = client.put(f"{API}/productos/{pizza['id']}/ingredientes", json={"items": [item(harina["id"], "0.3")]})
    assert r.status_code == 200, r.text
    assert r.json()[0]["unidad_medida"] == "KG"
    # Enviar la misma (en cualquier capitalización) también vale.
    r = client.put(f"{API}/productos/{pan['id']}/ingredientes", json={"items": [item(harina["id"], "0.5", "kg")]})
    assert r.status_code == 200 and r.json()[0]["unidad_medida"] == "KG"
    # Enviar otra se rechaza aunque no se pase por el formulario.
    r = client.put(f"{API}/productos/{pan['id']}/ingredientes", json={"items": [item(harina["id"], "300", "G")]})
    assert r.status_code == 422 and r.json()["code"] == "UNIT_MISMATCH"
    assert "KG" in r.json()["detail"]


def test_rn10_tambien_rige_para_la_receta_de_un_elaborado(client):
    login_admin(client)
    tomate, salsa = ingrediente(client, "Tomate"), ingrediente(client, "Salsa", es_elaborado=True)
    url = f"{API}/ingredientes/{salsa['id']}/receta"
    r = client.put(url, json={"items": [comp(tomate["id"], "1", "UN")]})
    assert r.status_code == 422 and r.json()["code"] == "UNIT_MISMATCH"
    r = client.put(url, json={"items": [comp(tomate["id"], "2")]})
    assert r.status_code == 200 and r.json()[0]["unidad_medida"] == "KG"


def test_rn10_la_unidad_se_cambia_solo_mientras_no_tenga_recetas_ni_stock(client):
    login_admin(client)
    harina, sal = ingrediente(client, "Harina"), ingrediente(client, "Sal")
    url = f"{API}/ingredientes/{harina['id']}"

    # Recién creado: se puede corregir.
    r = client.put(url, json={"unidad_medida": "g"})
    assert r.status_code == 200 and r.json()["unidad_medida"] == "G"

    # Con una receta que la usa, queda bloqueada…
    p = producto(client)
    assert (
        client.put(f"{API}/productos/{p['id']}/ingredientes", json={"items": [item(harina["id"])]}).status_code == 200
    )
    r = client.put(url, json={"unidad_medida": "KG"})
    assert r.status_code == 409 and r.json()["code"] == "UNIT_LOCKED"
    # …pero reenviar la misma (como hace el formulario al editar otro campo) no es un cambio.
    assert client.put(url, json={"unidad_medida": "G", "stock_minimo": 3}).status_code == 200

    # El stock cargado también la bloquea: las cantidades ya existentes se leerían en otra unidad.
    assert (
        client.post(
            f"{API}/ingredientes/{sal['id']}/movimientos", json={"tipo_movimiento": "ENTRADA", "cantidad": "5"}
        ).status_code
        == 201
    )
    r = client.put(f"{API}/ingredientes/{sal['id']}", json={"unidad_medida": "G"})
    assert r.status_code == 409 and r.json()["code"] == "UNIT_LOCKED"
    assert client.put(f"{API}/ingredientes/{sal['id']}", json={"unidad_medida": None}).status_code == 422


# ----------------------------------------------------------------------------------------------
# Receta de un ingrediente elaborado (RN-11)
# ----------------------------------------------------------------------------------------------


def comp(ing_id: int, cantidad: str = "1", unidad: str | None = None) -> dict:
    fila = {"componente_id": ing_id, "cantidad_requerida": cantidad}
    if unidad is not None:
        fila["unidad_medida"] = unidad
    return fila


def test_rn11_solo_un_elaborado_puede_tener_receta(client):
    login_admin(client)
    harina, tomate = ingrediente(client, "Harina"), ingrediente(client, "Tomate")
    r = client.put(f"{API}/ingredientes/{harina['id']}/receta", json={"items": [comp(tomate["id"])]})
    assert r.status_code == 422 and r.json()["code"] == "NOT_ELABORATED"


def test_receta_de_un_elaborado_se_reemplaza_y_se_lee(client):
    login_admin(client)
    salsa = ingrediente(client, "Salsa", es_elaborado=True)
    tomate, sal = ingrediente(client, "Tomate"), ingrediente(client, "Sal")
    url = f"{API}/ingredientes/{salsa['id']}/receta"
    assert client.get(url).json() == []

    r = client.put(url, json={"items": [comp(tomate["id"], "2.5", "kg"), comp(sal["id"], "0.01", "kg")]})
    assert r.status_code == 200, r.text
    assert {i["nombre"]: i["unidad_medida"] for i in client.get(url).json()} == {"Tomate": "KG", "Sal": "KG"}
    assert [i["nombre"] for i in client.put(url, json={"items": [comp(sal["id"], "1", "KG")]}).json()] == ["Sal"]
    assert client.get(f"{API}/ingredientes/999999/receta").status_code == 404


def test_rn11_un_ingrediente_no_puede_ser_componente_de_si_mismo(client):
    login_admin(client)
    salsa = ingrediente(client, "Salsa", es_elaborado=True)
    r = client.put(f"{API}/ingredientes/{salsa['id']}/receta", json={"items": [comp(salsa["id"])]})
    assert r.status_code == 422 and r.json()["code"] == "SELF_REFERENCE"


def test_rn11_la_receta_no_puede_tener_ciclos(client):
    login_admin(client)
    a, b, c = (ingrediente(client, n, es_elaborado=True) for n in ("A", "B", "C"))
    harina = ingrediente(client, "Harina")
    put = lambda padre, comp_id: client.put(  # noqa: E731
        f"{API}/ingredientes/{padre['id']}/receta", json={"items": [comp(comp_id)]}
    )
    assert put(a, b["id"]).status_code == 200  # A usa B
    assert put(b, c["id"]).status_code == 200  # B usa C
    r = put(c, a["id"])  # C usa A: cerraría A → B → C → A
    assert r.status_code == 422 and r.json()["code"] == "RECIPE_CYCLE"
    assert put(c, b["id"]).status_code == 422  # C usa B: B → C → B
    assert put(c, harina["id"]).status_code == 200  # una hoja sí
    # los sub-ensambles anidados son válidos (la cadena no es un ciclo)
    assert client.get(f"{API}/ingredientes/{a['id']}/receta").json()[0]["componente_id"] == b["id"]


def test_hay_ciclo_es_una_funcion_pura():
    aristas = [(1, 2), (2, 3), (4, 5)]
    assert hay_ciclo(aristas, padre_id=3, componentes=[1]) is True  # 3 → 1 → 2 → 3
    assert hay_ciclo(aristas, padre_id=3, componentes=[4]) is False
    assert hay_ciclo(aristas, padre_id=1, componentes=[5, 6]) is False
    assert hay_ciclo([], padre_id=1, componentes=[2]) is False
    assert hay_ciclo([(2, 3), (3, 2)], padre_id=1, componentes=[2]) is False  # un ciclo ajeno no cuenta
