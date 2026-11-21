"""Datos de demostración para probar el sistema a mano: catálogo, stock con lotes, producción, usuarios de cada
rol y pedidos en todos los estados. Es OPCIONAL y va separado del seed (que solo deja lo imprescindible).

    python -m app.db.demo

Pasa por los mismos services que la API, así que respeta todas las reglas. Se puede repetir: si el catálogo de
demo ya está cargado no vuelve a crearlo.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.core.deps import CurrentUser
from app.core.security import hash_password
from app.core.uow import UnitOfWork
from app.db.seed import ADMIN_PASSWORD, seed
from app.modules.categorias import service as categorias
from app.modules.categorias.schemas import CategoriaCreate
from app.modules.categorias.uow import CategoriasUnitOfWork
from app.modules.direcciones import service as direcciones
from app.modules.direcciones.schemas import DireccionCreate
from app.modules.direcciones.uow import DireccionesUnitOfWork
from app.modules.inventario import service as inventario
from app.modules.inventario.schemas import MovimientoCreate, MovimientoProductoCreate
from app.modules.inventario.uow import InventarioUnitOfWork
from app.modules.pagos import service as pagos
from app.modules.pagos.schemas import PagoCreate
from app.modules.pedidos import service as pedidos
from app.modules.pedidos.schemas import CancelarPedido, EstadoUpdate, LineaCreate, PedidoCreate
from app.modules.pedidos.uow import PedidosUnitOfWork
from app.modules.produccion import service as produccion
from app.modules.produccion.schemas import OrdenCompletar, OrdenCreate
from app.modules.produccion.uow import ProduccionUnitOfWork
from app.modules.productos import service as productos
from app.modules.productos.models import Producto
from app.modules.productos.schemas import (
    IngredienteCreate,
    ProductoCreate,
    RecetaIngredienteUpdate,
    RecetaProductoUpdate,
)
from app.modules.productos.uow import ProductosUnitOfWork
from app.modules.usuarios.models import Usuario, UsuarioRol

PASSWORD = ADMIN_PASSWORD  # la misma clave que el administrador del seed
USUARIOS = [
    ("cliente@foodstore.com", "Camila", "Cliente", "CLIENT"),
    ("stock@foodstore.com", "Sergio", "Stock", "STOCK"),
    ("pedidos@foodstore.com", "Paula", "Pedidos", "PEDIDOS"),
]
# Dentro de la «Zona Centro» del seed (a menos de 2 km del local).
UBICACION = (-34.6045, -58.3770)


def _usuarios() -> dict[str, CurrentUser]:
    """Crea los usuarios de demo (si faltan) y devuelve su identidad por rol."""
    uow = UnitOfWork()
    resultado: dict[str, CurrentUser] = {}
    with uow:
        from sqlmodel import select

        for email, nombre, apellido, rol in USUARIOS:
            usuario = uow.session.exec(select(Usuario).where(Usuario.email == email)).first()
            if usuario is None:
                usuario = Usuario(nombre=nombre, apellido=apellido, email=email, password_hash=hash_password(PASSWORD))
                uow.session.add(usuario)
                uow.session.flush()
                uow.session.add(UsuarioRol(usuario_id=usuario.id, rol_codigo=rol))
            resultado[rol] = CurrentUser(usuario.id, email, nombre, apellido, frozenset({rol}))  # type: ignore[arg-type]
        admin = uow.session.exec(select(Usuario).where(Usuario.email == "admin@foodstore.com")).one()
        resultado["ADMIN"] = CurrentUser(admin.id, admin.email, admin.nombre, admin.apellido, frozenset({"ADMIN"}))  # type: ignore[arg-type]
    return resultado


def _catalogo() -> dict[str, int]:
    """Categorías, insumos, sub-ensamble y productos con receta. Devuelve los ids por nombre."""
    ids: dict[str, int] = {}
    cat = CategoriasUnitOfWork()
    comidas = categorias.crear(cat, CategoriaCreate(nombre="Comidas")).id
    ids["Pizzas"] = categorias.crear(cat, CategoriaCreate(nombre="Pizzas", parent_id=comidas)).id
    ids["Empanadas"] = categorias.crear(cat, CategoriaCreate(nombre="Empanadas", parent_id=comidas)).id
    ids["Bebidas"] = categorias.crear(cat, CategoriaCreate(nombre="Bebidas")).id

    prod = ProductosUnitOfWork()
    for nombre, kwargs in [
        ("Harina", {"unidad_medida": "KG", "es_alergeno": True}),
        ("Muzzarella", {"unidad_medida": "KG", "es_alergeno": True}),
        ("Tomate", {"unidad_medida": "KG"}),
        ("Cebolla", {"unidad_medida": "KG"}),
        ("Carne picada", {"unidad_medida": "KG"}),
        ("Caja de pizza", {"unidad_medida": "UN"}),
        ("Salsa de tomate", {"unidad_medida": "KG", "es_elaborado": True}),
    ]:
        ids[nombre] = productos.crear_ingrediente(prod, IngredienteCreate(nombre=nombre, stock_minimo=2, **kwargs)).id
    productos.reemplazar_receta_ingrediente(
        prod,
        ids["Salsa de tomate"],
        RecetaIngredienteUpdate(
            items=[{"componente_id": ids["Tomate"], "cantidad_requerida": "2", "unidad_medida": "KG"}]
        ),  # type: ignore[list-item]
    )

    def receta(*filas: tuple[str, str, str, bool]) -> RecetaProductoUpdate:
        return RecetaProductoUpdate(
            items=[
                {"ingrediente_id": ids[n], "cantidad_requerida": c, "unidad_medida": u, "es_removible": r}  # type: ignore[list-item]
                for n, c, u, r in filas
            ]
        )

    for nombre, descripcion, precio, categoria, filas in [
        (
            "Pizza muzzarella",
            "Clásica, con salsa y muzzarella.",
            "9500.00",
            "Pizzas",
            [
                ("Harina", "0.300", "KG", False),
                ("Muzzarella", "0.250", "KG", True),
                ("Salsa de tomate", "0.100", "KG", False),
                ("Caja de pizza", "1", "UN", False),
            ],
        ),
        (
            "Pizza fugazzeta",
            "Con cebolla y abundante muzzarella.",
            "10800.00",
            "Pizzas",
            [
                ("Harina", "0.300", "KG", False),
                ("Muzzarella", "0.300", "KG", True),
                ("Cebolla", "0.200", "KG", True),
                ("Caja de pizza", "1", "UN", False),
            ],
        ),
        (
            "Empanada de carne",
            "Al horno, rellena de carne cortada a cuchillo.",
            "1400.00",
            "Empanadas",
            [("Harina", "0.060", "KG", False), ("Carne picada", "0.080", "KG", True)],
        ),
        ("Gaseosa 500 ml", "Bebida fría.", "1800.00", "Bebidas", []),
    ]:
        p = productos.crear_producto(
            prod,
            ProductoCreate(
                nombre=nombre,
                descripcion=descripcion,
                precio_base=Decimal(precio),
                categoria_ids=[ids[categoria]],
                disponible=True,
                stock_minimo=3,
            ),
        )
        ids[nombre] = p.id
        if filas:
            productos.reemplazar_receta_producto(prod, p.id, receta(*filas))
    return ids


def _stock(ids: dict[str, int]) -> None:
    """Insumos con stock; productos terminados con lotes (uno por vencer pronto, para ver las alertas)."""
    inv = InventarioUnitOfWork()
    for nombre, cantidad in [
        ("Harina", "50"),
        ("Muzzarella", "30"),
        ("Tomate", "40"),
        ("Cebolla", "10"),
        ("Carne picada", "15"),
        ("Caja de pizza", "100"),
    ]:
        inventario.registrar_movimiento_ingrediente(
            inv,
            ids[nombre],
            MovimientoCreate(tipo_movimiento="ENTRADA", cantidad=Decimal(cantidad), motivo="Stock inicial"),
        )
    ahora = datetime.now(ZoneInfo("UTC"))
    for nombre, lotes in [
        ("Gaseosa 500 ml", [("GAS-01", 2, "24"), ("GAS-02", 60, "48")]),
        ("Empanada de carne", [("EMP-01", 3, "30")]),
    ]:
        for codigo, dias, cantidad in lotes:
            inventario.registrar_movimiento_producto(
                inv,
                ids[nombre],
                MovimientoProductoCreate(
                    tipo_movimiento="ENTRADA",
                    cantidad=Decimal(cantidad),
                    codigo_lote=codigo,
                    fecha_vencimiento=ahora + timedelta(days=dias),
                ),
            )


def _produccion(ids: dict[str, int], personal: CurrentUser) -> None:
    """Una orden completada (la salsa, sub-ensamble), otra de pizzas ya terminada y una planificada."""
    uow = ProduccionUnitOfWork()
    salsa = produccion.crear_orden(
        uow, OrdenCreate(ingrediente_id=ids["Salsa de tomate"], cantidad_a_producir=Decimal(8))
    )
    produccion.iniciar_orden(uow, salsa.id, personal)
    produccion.completar_orden(uow, salsa.id, OrdenCompletar(), personal)

    pizzas = produccion.crear_orden(
        uow, OrdenCreate(producto_id=ids["Pizza muzzarella"], cantidad_a_producir=Decimal(12))
    )
    produccion.iniciar_orden(uow, pizzas.id, personal)
    produccion.completar_orden(
        uow,
        pizzas.id,
        OrdenCompletar(codigo_lote="PZ-01", fecha_vencimiento=datetime.now(ZoneInfo("UTC")) + timedelta(days=2)),
        personal,
    )
    produccion.crear_orden(uow, OrdenCreate(producto_id=ids["Pizza fugazzeta"], cantidad_a_producir=Decimal(4)))
    # Fugazzeta terminada, para poder pedirla.
    otra = produccion.crear_orden(uow, OrdenCreate(producto_id=ids["Pizza fugazzeta"], cantidad_a_producir=Decimal(6)))
    produccion.iniciar_orden(uow, otra.id, personal)
    produccion.completar_orden(uow, otra.id, OrdenCompletar(), personal)


def _pedidos(ids: dict[str, int], u: dict[str, CurrentUser]) -> None:
    """Un pedido en cada estado del ciclo de vida."""
    cliente, pers = u["CLIENT"], u["PEDIDOS"]
    direccion = direcciones.crear(
        DireccionesUnitOfWork(),
        cliente.id,
        DireccionCreate(
            alias="Casa",
            linea1="Av. Corrientes 1500",
            ciudad="Buenos Aires",
            lat=UBICACION[0],
            lng=UBICACION[1],
            es_principal=True,
        ),
    )
    zona = ZoneInfo("America/Argentina/Buenos_Aires")
    hoy_abierto = datetime.now(zona).replace(hour=15, minute=0, second=0, microsecond=0)  # dentro del horario

    uow = PedidosUnitOfWork()

    def nuevo(items: list[tuple[str, int]], **extra) -> int:
        carrito = PedidoCreate(
            items=[LineaCreate(producto_id=ids[n], cantidad=c) for n, c in items],
            forma_pago_codigo=extra.pop("forma_pago_codigo", "EFECTIVO"),
            **extra,
        )
        pedido, _ = pedidos.crear_pedido(uow, cliente, carrito, str(uuid.uuid4()), ahora=hoy_abierto)
        return pedido.id

    def cobrar(pedido_id: int) -> None:
        total = pedidos.obtener_pedido(uow, pedido_id, pers).total
        pagos.registrar_pago(uow, pedido_id, PagoCreate(monto=total), pers, str(uuid.uuid4()))

    def avanzar(pedido_id: int, *estados: str) -> None:
        for e in estados:
            pedidos.cambiar_estado(uow, pedido_id, EstadoUpdate(estado=e), pers)  # type: ignore[arg-type]

    nuevo([("Pizza muzzarella", 1), ("Gaseosa 500 ml", 2)])  # PENDIENTE (retiro)
    cobrar(nuevo([("Empanada de carne", 6)], direccion_id=direccion.id))  # CONFIRMADO (con envío)
    preparacion = nuevo([("Pizza fugazzeta", 2)], forma_pago_codigo="TRANSFERENCIA")
    cobrar(preparacion)
    avanzar(preparacion, "EN_PREPARACION")
    entregado = nuevo([("Pizza muzzarella", 2), ("Gaseosa 500 ml", 1)], direccion_id=direccion.id)
    cobrar(entregado)
    avanzar(entregado, "EN_PREPARACION", "EN_CAMINO", "ENTREGADO")
    cancelado = nuevo([("Gaseosa 500 ml", 4)])
    pedidos.cancelar_pedido(uow, cancelado, CancelarPedido(motivo="El cliente se arrepintió"), cliente)


def cargar() -> bool:
    """Carga la demo. Devuelve False si ya estaba cargada."""
    seed()
    existente = UnitOfWork()
    with existente:
        from sqlmodel import select

        if existente.session.exec(select(Producto).where(Producto.nombre == "Pizza muzzarella")).first():
            return False
    usuarios = _usuarios()
    ids = _catalogo()
    _stock(ids)
    _produccion(ids, usuarios["STOCK"])
    _pedidos(ids, usuarios)
    return True


if __name__ == "__main__":
    if cargar():
        print("Demo cargada. Usuarios (clave", PASSWORD + "):")
        for email, *_ in USUARIOS:
            print("  ", email)
        print("   admin@foodstore.com")
    else:
        print("La demo ya estaba cargada; no se tocó nada.")
