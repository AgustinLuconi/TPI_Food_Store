"""Escenario común de pedidos y pagos: tienda con stock, un cliente con direcciones y personal de cada rol."""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from tests.helpers import API, login_admin, registrar_y_loguear
from tests.test_catalogo import cliente_con_rol, ingrediente, producto
from tests.test_inventario import en_dias, mover

BA = ZoneInfo("America/Argentina/Buenos_Aires")
LUNES = date(2026, 11, 16)
DENTRO = (-34.6037, -58.3716)  # dentro de la Zona Centro del seed (pedido mínimo 3000)
FUERA = (-34.70, -58.30)


def instante_local(hora: int, dia: date = LUNES) -> datetime:
    return datetime.combine(dia, time(hora), tzinfo=BA).astimezone(UTC)


@pytest.fixture
def reloj(monkeypatch):
    """Fija la hora del servidor. Por defecto, lunes 15:00 en Buenos Aires: el local (11 a 23) está abierto."""

    def fijar(momento: datetime) -> None:
        monkeypatch.setattr("app.modules.config.service.utcnow", lambda: momento)

    fijar(instante_local(15))
    return fijar


@dataclass
class Tienda:
    admin: TestClient
    cliente: TestClient
    pedidos: TestClient  # rol PEDIDOS
    stock: TestClient  # rol STOCK
    pizza: int  # $9.500, con receta (queso removible, harina no)
    empanada: int  # $1.200, sin receta
    queso: int
    harina: int
    cebolla: int  # ingrediente que no está en ninguna receta
    dentro: int  # dirección dentro de la zona
    fuera: int  # dirección fuera de toda zona
    sin_coords: int
    lote_a: int  # pizza: vence primero (4 u.)
    lote_b: int  # pizza: vence después (6 u.)


@pytest.fixture
def tienda(client, reloj) -> Tienda:
    admin = login_admin(client)
    queso, harina, cebolla = (ingrediente(admin, n)["id"] for n in ("Queso", "Harina", "Cebolla"))
    pizza = producto(admin, "Pizza muzzarella", "9500.00")["id"]
    empanada = producto(admin, "Empanada", "1200.00")["id"]
    receta = [
        {"ingrediente_id": queso, "cantidad_requerida": "0.2", "unidad_medida": "KG", "es_removible": True},
        {"ingrediente_id": harina, "cantidad_requerida": "0.3", "unidad_medida": "KG", "es_removible": False},
    ]
    assert admin.put(f"{API}/productos/{pizza}/ingredientes", json={"items": receta}).status_code == 200

    # Pizza: 4 en el lote que vence antes y 6 en el que vence después. Empanadas: 20 sin lote.
    mover(admin, "productos", pizza, "ENTRADA", "6", codigo_lote="B", fecha_vencimiento=en_dias(10))
    mover(admin, "productos", pizza, "ENTRADA", "4", codigo_lote="A", fecha_vencimiento=en_dias(3))
    mover(admin, "productos", empanada, "ENTRADA", "20")
    lotes = {x["codigo_lote"]: x["id"] for x in admin.get(f"{API}/productos/{pizza}/lotes").json()}

    cliente = TestClient(client.app)
    registrar_y_loguear(cliente)

    def direccion(lat: float | None, lng: float | None) -> int:
        cuerpo = {"linea1": "Calle 123", "lat": lat, "lng": lng}
        r = cliente.post(f"{API}/direcciones", json=cuerpo)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    return Tienda(
        admin=admin,
        cliente=cliente,
        pedidos=cliente_con_rol(admin, "PEDIDOS", "pedidos@foodstore.com"),
        stock=cliente_con_rol(admin, "STOCK", "stock@foodstore.com"),
        pizza=pizza,
        empanada=empanada,
        queso=queso,
        harina=harina,
        cebolla=cebolla,
        dentro=direccion(*DENTRO),
        fuera=direccion(*FUERA),
        sin_coords=direccion(None, None),
        lote_a=lotes["A"],
        lote_b=lotes["B"],
    )


def linea(producto_id: int, cantidad: int = 1, *exclusiones: int) -> dict:
    return {"producto_id": producto_id, "cantidad": cantidad, "exclusiones": list(exclusiones)}


def crear_pedido(cliente: TestClient, items: list[dict], *, clave: str | None = None, **extra):
    cuerpo = {"items": items, "forma_pago_codigo": "EFECTIVO", **extra}
    return cliente.post(f"{API}/pedidos", json=cuerpo, headers={"Idempotency-Key": clave or str(uuid.uuid4())})


def pedido_ok(cliente: TestClient, items: list[dict], **extra) -> dict:
    r = crear_pedido(cliente, items, **extra)
    assert r.status_code == 201, r.text
    return r.json()


def pagar(personal: TestClient, pedido: dict, *, clave: str | None = None, monto: str | None = None):
    return personal.post(
        f"{API}/pagos/{pedido['id']}",
        json={"monto": monto or pedido["total"]},
        headers={"Idempotency-Key": clave or str(uuid.uuid4())},
    )


def estado(cliente: TestClient, pedido_id: int) -> str:
    return cliente.get(f"{API}/pedidos/{pedido_id}").json()["estado_codigo"]


def stock_producto(admin: TestClient, producto_id: int) -> tuple[Decimal, Decimal]:
    r = admin.get(f"{API}/productos/{producto_id}/stock").json()
    return Decimal(r["stock_real"]), Decimal(r["stock_disponible"])


def movimientos_de_pedido(admin: TestClient, producto_id: int, pedido_id: int) -> list[tuple[str, int | None, Decimal]]:
    """(tipo, lote_id, cantidad) de los movimientos del producto con ese pedido_id, del más antiguo al más nuevo."""
    items = admin.get(f"{API}/productos/{producto_id}/movimientos", params={"size": 100}).json()["items"]
    propios = [m for m in items if m["pedido_id"] == pedido_id]
    return [(m["tipo_movimiento"], m["lote_id"], Decimal(m["cantidad"])) for m in reversed(propios)]
