"""Concurrencia real: varias conexiones a la vez, cada una con su propia transacción confirmada.

Los demás tests corren todos en UNA conexión (con SAVEPOINTs), así que no pueden ver deadlocks ni carreras entre
transacciones. Estos usan hilos y una base propia (`foodstore_concurrencia`), que se recrea al empezar el módulo.

Encontraron un deadlock real: crear un pedido insertaba las líneas (que referencian al producto y toman un bloqueo
compartido sobre su fila) ANTES de pedir el bloqueo exclusivo, y dos pedidos simultáneos se esperaban entre sí.
"""

import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import psycopg
import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from app.core.deps import CurrentUser
from app.core.errors import ConflictError
from app.core.uow import UnitOfWork
from app.db import base  # noqa: F401  (registra todos los modelos)
from app.db.seed import seed
from app.modules.inventario import service as inventario
from app.modules.inventario.schemas import MovimientoProductoCreate
from app.modules.inventario.uow import InventarioUnitOfWork
from app.modules.pagos import service as pagos
from app.modules.pagos.schemas import PagoCreate
from app.modules.pedidos import service as pedidos
from app.modules.pedidos.schemas import LineaCreate, PedidoCreate
from app.modules.pedidos.uow import PedidosUnitOfWork
from app.modules.productos import service as productos
from app.modules.productos.schemas import ProductoCreate
from app.modules.productos.uow import ProductosUnitOfWork
from app.modules.usuarios.models import Usuario, UsuarioRol
from tests.conftest import TEST_DB_URL

NOMBRE_BD = "foodstore_concurrencia"
URL = TEST_DB_URL.rsplit("/", 1)[0] + "/" + NOMBRE_BD
# Lunes 15:00 en Buenos Aires: el local del seed (11 a 23) está abierto.
ABIERTO = datetime.combine(datetime(2026, 11, 16).date(), time(15), tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
HILOS = 12


@pytest.fixture(scope="module")
def factory():
    admin_url = TEST_DB_URL.replace("+psycopg", "").rsplit("/", 1)[0] + "/postgres"
    with psycopg.connect(admin_url, autocommit=True) as conn:
        if not conn.execute("select 1 from pg_database where datname = %s", (NOMBRE_BD,)).fetchone():
            conn.execute(f'create database "{NOMBRE_BD}"')
    engine = create_engine(URL, pool_size=HILOS + 2)
    SQLModel.metadata.drop_all(engine)  # base propia de este módulo: siempre parte vacía
    SQLModel.metadata.create_all(engine)
    crear: Callable[[], Session] = lambda: Session(engine, expire_on_commit=False)  # noqa: E731
    seed(UnitOfWork(crear))
    yield crear
    engine.dispose()


def _usuario(factory, email: str, rol: str) -> CurrentUser:
    uow = UnitOfWork(factory)
    with uow:
        u = Usuario(nombre="Test", apellido=rol, email=email, password_hash="x" * 60)
        uow.session.add(u)
        uow.session.flush()
        uow.session.add(UsuarioRol(usuario_id=u.id, rol_codigo=rol))
        return CurrentUser(u.id, email, "Test", rol, frozenset({rol}))  # type: ignore[arg-type]


def _producto(factory, nombre: str, unidades: int) -> int:
    p = productos.crear_producto(
        ProductosUnitOfWork(factory), ProductoCreate(nombre=nombre, precio_base=Decimal("1000"), categoria_ids=[])
    )
    inventario.registrar_movimiento_producto(
        InventarioUnitOfWork(factory),
        p.id,
        MovimientoProductoCreate(tipo_movimiento="ENTRADA", cantidad=Decimal(unidades)),
    )
    return p.id


def _stock(factory, producto_id: int) -> tuple[Decimal, Decimal]:
    s = inventario.obtener_stock_producto(InventarioUnitOfWork(factory), producto_id)
    return s.stock_real, s.stock_disponible


def _en_paralelo(tareas: list[Callable[[], object]]) -> list[object]:
    """Corre todas a la vez; devuelve el resultado o la excepción de cada una."""

    def correr(t: Callable[[], object]) -> object:
        try:
            return t()
        except Exception as e:  # noqa: BLE001
            return e

    with ThreadPoolExecutor(max_workers=len(tareas)) as pool:
        return list(pool.map(correr, tareas))


def test_pedidos_simultaneos_no_venden_mas_de_lo_que_hay(factory):
    """12 clientes piden 1 unidad cada uno de un producto con 4: exactamente 4 pedidos, 8 rechazos por stock y
    ningún deadlock ni error inesperado."""
    pid = _producto(factory, "Agua concurrente", 4)
    clientes = [_usuario(factory, f"c{i}@concurrencia.com", "CLIENT") for i in range(HILOS)]

    def pedir(cliente: CurrentUser):
        carrito = PedidoCreate(items=[LineaCreate(producto_id=pid, cantidad=1)], forma_pago_codigo="EFECTIVO")
        return pedidos.crear_pedido(PedidosUnitOfWork(factory), cliente, carrito, str(uuid.uuid4()), ahora=ABIERTO)

    resultados = _en_paralelo([lambda c=c: pedir(c) for c in clientes])
    creados = [r for r in resultados if isinstance(r, tuple)]
    sin_stock = [r for r in resultados if isinstance(r, ConflictError) and r.code == "INSUFFICIENT_STOCK"]
    otros = [r for r in resultados if r not in creados and r not in sin_stock]
    assert not otros, f"errores inesperados (¿deadlock?): {otros!r}"
    assert (len(creados), len(sin_stock)) == (4, 8)
    assert _stock(factory, pid) == (4, 0)  # el real no se toca; todo el disponible quedó reservado


def test_la_misma_idempotency_key_en_paralelo_crea_un_solo_pedido(factory):
    pid = _producto(factory, "Jugo concurrente", 20)
    cliente = _usuario(factory, "unico@concurrencia.com", "CLIENT")
    clave = str(uuid.uuid4())

    def pedir():
        carrito = PedidoCreate(items=[LineaCreate(producto_id=pid, cantidad=2)], forma_pago_codigo="EFECTIVO")
        return pedidos.crear_pedido(PedidosUnitOfWork(factory), cliente, carrito, clave, ahora=ABIERTO)

    resultados = _en_paralelo([pedir] * HILOS)
    errores = [r for r in resultados if isinstance(r, Exception)]
    assert not errores, f"errores inesperados: {errores!r}"
    assert sum(1 for _, creado in resultados if creado) == 1  # type: ignore[misc]
    assert len({p.id for p, _ in resultados}) == 1  # type: ignore[misc]
    assert _stock(factory, pid) == (20, 18)  # se reservó una sola vez


def test_dos_cajeros_cobrando_el_mismo_pedido_registran_un_solo_pago(factory):
    pid = _producto(factory, "Café concurrente", 5)
    cliente = _usuario(factory, "paga@concurrencia.com", "CLIENT")
    cajeros = [_usuario(factory, f"caja{i}@concurrencia.com", "PEDIDOS") for i in range(5)]
    carrito = PedidoCreate(items=[LineaCreate(producto_id=pid, cantidad=1)], forma_pago_codigo="EFECTIVO")
    pedido, _ = pedidos.crear_pedido(PedidosUnitOfWork(factory), cliente, carrito, str(uuid.uuid4()), ahora=ABIERTO)

    def cobrar(cajero: CurrentUser):
        return pagos.registrar_pago(
            PedidosUnitOfWork(factory), pedido.id, PagoCreate(monto=pedido.total), cajero, str(uuid.uuid4())
        )

    resultados = _en_paralelo([lambda c=c: cobrar(c) for c in cajeros])
    cobrados = [r for r in resultados if isinstance(r, tuple)]
    rechazados = [r for r in resultados if isinstance(r, ConflictError)]
    assert not [r for r in resultados if r not in cobrados and r not in rechazados], resultados
    assert (len(cobrados), len(rechazados)) == (1, 4)
    historial = pedidos.obtener_historial(PedidosUnitOfWork(factory), pedido.id, cajeros[0])
    assert [h.estado_hasta for h in historial] == ["PENDIENTE", "CONFIRMADO"]  # se confirmó una sola vez


def test_ordenes_de_produccion_simultaneas_no_reservan_mas_insumos_de_los_que_hay(factory):
    from app.modules.inventario.schemas import MovimientoCreate
    from app.modules.produccion import service as produccion
    from app.modules.produccion.schemas import OrdenCreate
    from app.modules.produccion.uow import ProduccionUnitOfWork
    from app.modules.productos.schemas import IngredienteCreate, RecetaProductoItem, RecetaProductoUpdate

    uow_p = ProductosUnitOfWork(factory)
    harina = productos.crear_ingrediente(uow_p, IngredienteCreate(nombre="Harina concurrente")).id
    pan = productos.crear_producto(
        uow_p, ProductoCreate(nombre="Pan concurrente", precio_base=Decimal("500"), categoria_ids=[])
    ).id
    productos.reemplazar_receta_producto(
        uow_p,
        pan,
        RecetaProductoUpdate(
            items=[RecetaProductoItem(ingrediente_id=harina, cantidad_requerida=Decimal("1"), unidad_medida="KG")]
        ),
    )
    inventario.registrar_movimiento_ingrediente(
        InventarioUnitOfWork(factory), harina, MovimientoCreate(tipo_movimiento="ENTRADA", cantidad=Decimal(6))
    )

    def planificar():
        return produccion.crear_orden(
            ProduccionUnitOfWork(factory), OrdenCreate(producto_id=pan, cantidad_a_producir=Decimal(2))
        )

    resultados = _en_paralelo([planificar] * 8)  # 8 órdenes de 2 KG sobre 6 KG: caben 3
    ok = [r for r in resultados if not isinstance(r, Exception)]
    sin_stock = [r for r in resultados if isinstance(r, ConflictError) and r.code == "INSUFFICIENT_STOCK"]
    assert not [r for r in resultados if isinstance(r, Exception) and r not in sin_stock], resultados
    assert (len(ok), len(sin_stock)) == (3, 5)
    s = inventario.obtener_stock_ingrediente(InventarioUnitOfWork(factory), harina)
    assert (s.stock_real, s.stock_disponible) == (6, 0)
    _ = UTC  # (la hora no interviene en producción)
