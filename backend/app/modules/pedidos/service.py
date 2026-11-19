"""Pedidos (sección 9): creación idempotente en una transacción, máquina de estados, stock e historial.

Lanza excepciones de dominio y no hace commit (lo hace el Unit of Work). Ante cualquier error se revierte
todo: no quedan pedidos a medias ni reservas sueltas.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.core.deps import CurrentUser
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.fsm import PEDIDO_TRANSICIONES, validar_transicion
from app.core.schemas import Paginated
from app.modules.config import service as config
from app.modules.config.schemas import CotizacionRequest
from app.modules.direcciones.schemas import DireccionRead
from app.modules.inventario import service as inventario
from app.modules.pagos.schemas import PagoRead
from app.modules.pedidos.models import DetallePedido, HistorialEstadoPedido, Pedido
from app.modules.pedidos.schemas import (
    CancelarPedido,
    EstadoUpdate,
    ExclusionRead,
    FiltrosPedidos,
    HistorialRead,
    LineaCreate,
    LineaRead,
    PedidoCreate,
    PedidoItem,
    PedidoRead,
)
from app.modules.pedidos.uow import PedidosUnitOfWork
from app.modules.productos.models import Producto, TipoMovimiento

ROLES_STAFF = frozenset({"ADMIN", "PEDIDOS"})
CENTAVO = Decimal("0.01")


def es_staff(usuario: CurrentUser) -> bool:
    return bool(usuario.roles & ROLES_STAFF)


# ==============================================================================================
# Lecturas
# ==============================================================================================


def _nombre_cliente(uow: PedidosUnitOfWork, usuario_id: int) -> str:
    usuario = uow.usuarios.get_by_id(usuario_id, include_deleted=True)
    return f"{usuario.nombre} {usuario.apellido}" if usuario else ""


def obtener_pedido_visible(
    uow: PedidosUnitOfWork, pedido_id: int, usuario: CurrentUser, *, bloquear: bool = False
) -> Pedido:
    """El propietario y el personal lo ven; para cualquier otro es 404 (no se revela que existe)."""
    pedido = uow.pedidos.get_for_update(pedido_id) if bloquear else uow.pedidos.get_by_id(pedido_id)
    if pedido is None or not (es_staff(usuario) or pedido.usuario_id == usuario.id):
        raise NotFoundError("Pedido no encontrado", code="ORDER_NOT_FOUND")
    return pedido


def _lineas(uow: PedidosUnitOfWork, pedido_id: int) -> list[LineaRead]:
    detalles = uow.detalles.de_pedido(pedido_id)
    exclusiones = uow.detalles.exclusiones_de([d.id for d in detalles])  # type: ignore[misc]
    return [
        LineaRead(
            id=d.id,  # type: ignore[arg-type]
            producto_id=d.producto_id,
            nombre_snapshot=d.nombre_snapshot,
            precio_snapshot=d.precio_snapshot,
            cantidad=d.cantidad,
            subtotal=d.precio_snapshot * d.cantidad,
            exclusiones=[ExclusionRead(ingrediente_id=i, nombre=n) for i, n in exclusiones[d.id]],  # type: ignore[index]
        )
        for d in detalles
    ]


def _pedido_read(uow: PedidosUnitOfWork, pedido: Pedido) -> PedidoRead:
    direccion = uow.direcciones.get_by_id(pedido.direccion_id, include_deleted=True) if pedido.direccion_id else None
    pago = uow.pagos.get_by_pedido(pedido.id)  # type: ignore[arg-type]
    return PedidoRead(
        id=pedido.id,  # type: ignore[arg-type]
        usuario_id=pedido.usuario_id,
        cliente_nombre=_nombre_cliente(uow, pedido.usuario_id),
        estado_codigo=pedido.estado_codigo,
        forma_pago_codigo=pedido.forma_pago_codigo,
        direccion_id=pedido.direccion_id,
        direccion=DireccionRead.model_validate(direccion) if direccion else None,
        subtotal=pedido.subtotal,
        descuento=pedido.descuento,
        costo_envio=pedido.costo_envio,
        total=pedido.total,
        notas=pedido.notas,
        external_reference=pedido.external_reference,
        created_at=pedido.created_at,
        updated_at=pedido.updated_at,
        lineas=_lineas(uow, pedido.id),  # type: ignore[arg-type]
        pago=PagoRead.model_validate(pago) if pago else None,
        historial=[HistorialRead.model_validate(h) for h in uow.historial.de_pedido(pedido.id)],  # type: ignore[arg-type]
    )


def _limites_de_fecha(uow: PedidosUnitOfWork, filtros: FiltrosPedidos) -> tuple[datetime | None, datetime | None]:
    """`desde` y `hasta` son días del calendario del LOCAL: se pasan a instantes con su zona horaria."""
    if not (filtros.desde or filtros.hasta):
        return None, None
    zona = ZoneInfo(config.obtener_local_en_transaccion(uow).zona_horaria)
    desde = datetime.combine(filtros.desde, time.min, tzinfo=zona) if filtros.desde else None
    hasta = datetime.combine(filtros.hasta + timedelta(days=1), time.min, tzinfo=zona) if filtros.hasta else None
    return desde, hasta


def listar_pedidos(uow: PedidosUnitOfWork, usuario: CurrentUser, filtros: FiltrosPedidos) -> Paginated[PedidoItem]:
    """El cliente ve solo los suyos; ADMIN y PEDIDOS ven todos."""
    with uow:
        desde, hasta = _limites_de_fecha(uow, filtros)
        items, total = uow.pedidos.search(
            usuario_id=None if es_staff(usuario) else usuario.id,
            estado=filtros.estado,
            desde=desde,
            hasta_exclusivo=hasta,
            page=filtros.page,
            size=filtros.size,
        )
        data = [
            PedidoItem(
                id=p.id,  # type: ignore[arg-type]
                usuario_id=p.usuario_id,
                cliente_nombre=_nombre_cliente(uow, p.usuario_id),
                estado_codigo=p.estado_codigo,
                forma_pago_codigo=p.forma_pago_codigo,
                total=p.total,
                con_envio=p.direccion_id is not None,
                created_at=p.created_at,
            )
            for p in items
        ]
    return Paginated.build(data, total, filtros.page, filtros.size)


def obtener_pedido(uow: PedidosUnitOfWork, pedido_id: int, usuario: CurrentUser) -> PedidoRead:
    with uow:
        return _pedido_read(uow, obtener_pedido_visible(uow, pedido_id, usuario))


def obtener_historial(uow: PedidosUnitOfWork, pedido_id: int, usuario: CurrentUser) -> list[HistorialRead]:
    with uow:
        pedido = obtener_pedido_visible(uow, pedido_id, usuario)
        return [HistorialRead.model_validate(h) for h in uow.historial.de_pedido(pedido.id)]  # type: ignore[arg-type]


# ==============================================================================================
# Cambios de estado
# ==============================================================================================


def registrar_transicion(
    uow: PedidosUnitOfWork, pedido: Pedido, hasta: str, usuario_id: int | None, motivo: str | None = None
) -> None:
    """Cambia el estado e inserta SIEMPRE un registro en el historial (sección 9.1)."""
    desde = pedido.estado_codigo
    uow.pedidos.update(pedido, {"estado_codigo": hasta})
    uow.historial.create(
        HistorialEstadoPedido(
            pedido_id=pedido.id, estado_desde=desde, estado_hasta=hasta, usuario_id=usuario_id, motivo=motivo
        )
    )


def cambiar_estado(uow: PedidosUnitOfWork, pedido_id: int, datos: EstadoUpdate, usuario: CurrentUser) -> PedidoRead:
    """Avanza de CONFIRMADO a ENTREGADO según la máquina de estados (solo ADMIN y PEDIDOS).

    Pasar a EN_PREPARACION consume el stock: LIBERACION_RESERVA y SALIDA sobre los mismos lotes reservados."""
    hasta = datos.estado
    if hasta == "CANCELADO":
        raise ValidationError(
            "Para cancelar use POST /pedidos/{id}/cancelar (exige motivo)", code="USE_CANCEL_ENDPOINT"
        )
    with uow:
        pedido = obtener_pedido_visible(uow, pedido_id, usuario, bloquear=True)
        if pedido.estado_codigo == "PENDIENTE" and hasta == "CONFIRMADO":
            raise ConflictError(
                "Un pedido PENDIENTE se confirma al registrar su pago (POST /pagos/{pedido_id})",
                code="PAYMENT_REQUIRED",
            )
        validar_transicion(PEDIDO_TRANSICIONES, pedido.estado_codigo, hasta, usuario.roles)
        if hasta == "EN_PREPARACION":
            inventario.consumir_reservas_de_pedido(uow, pedido.id)  # type: ignore[arg-type]
        registrar_transicion(uow, pedido, hasta, usuario.id)
        return _pedido_read(uow, pedido)


def cancelar_pedido(uow: PedidosUnitOfWork, pedido_id: int, datos: CancelarPedido, usuario: CurrentUser) -> PedidoRead:
    """RN-05: cancelar exige motivo (queda en el historial). El propietario cancela en PENDIENTE o CONFIRMADO;
    ADMIN y PEDIDOS en cualquier estado no terminal.

    Desde PENDIENTE o CONFIRMADO se libera la reserva (el stock real nunca cambió). Desde EN_PREPARACION o
    EN_CAMINO no hay movimiento automático: el producto ya se consumió y, si se descarta, STOCK registra una MERMA."""
    with uow:
        pedido = obtener_pedido_visible(uow, pedido_id, usuario, bloquear=True)
        desde = pedido.estado_codigo
        validar_transicion(PEDIDO_TRANSICIONES, desde, "CANCELADO", usuario.roles)
        if desde in ("PENDIENTE", "CONFIRMADO"):
            inventario.liberar_reservas_de_pedido(uow, pedido.id)  # type: ignore[arg-type]
        registrar_transicion(uow, pedido, "CANCELADO", usuario.id, datos.motivo)
        return _pedido_read(uow, pedido)


# ==============================================================================================
# Crear un pedido (sección 9.3)
# ==============================================================================================


def _validar_lineas(uow: PedidosUnitOfWork, items: list[LineaCreate]) -> dict[int, Producto]:
    """Producto activo y disponible, y exclusiones permitidas (RN-12). Todo error de línea es 409."""
    productos: dict[int, Producto] = {}
    recetas: dict[int, dict[int, bool]] = {}
    for item in items:
        producto = productos.get(item.producto_id) or uow.productos.get_by_id(item.producto_id)
        if producto is None or not producto.disponible:
            raise ConflictError(
                f"El producto {item.producto_id} no está disponible", code="PRODUCT_UNAVAILABLE", field="items"
            )
        productos[item.producto_id] = producto
        if item.producto_id not in recetas:
            recetas[item.producto_id] = {
                ing.id: fila.es_removible  # type: ignore[misc]
                for fila, ing in uow.recetas.de_producto(item.producto_id)
            }
        for ingrediente_id in item.exclusiones:
            if not recetas[item.producto_id].get(ingrediente_id, False):
                raise ConflictError(
                    f"«{producto.nombre}» no permite quitar el ingrediente {ingrediente_id}: "
                    "no está en la receta o no es removible",
                    code="INVALID_EXCLUSION",
                    field="items",
                )
    return productos


def _costo_de_envio(
    uow: PedidosUnitOfWork, usuario: CurrentUser, direccion_id: int | None, subtotal: Decimal
) -> Decimal:
    """RN-14. Con dirección: debe tener coordenadas, caer en una zona activa y alcanzar el pedido mínimo (422).
    Sin dirección (retiro en el local) el envío es 0."""
    if direccion_id is None:
        return Decimal("0.00")
    direccion = uow.direcciones.get_owned(usuario.id, direccion_id)
    if direccion is None:
        raise NotFoundError("Dirección no encontrada", code="ADDRESS_NOT_FOUND")
    if direccion.lat is None or direccion.lng is None:
        raise ValidationError(
            "La dirección no tiene coordenadas: no se puede cotizar el envío",
            code="ADDRESS_WITHOUT_COORDS",
            field="direccion_id",
        )
    # Fuera de toda zona lanza 422 OUTSIDE_COVERAGE (atribuido a la dirección).
    cotizacion = config.calcular_cotizacion(
        uow, CotizacionRequest(lat=direccion.lat, lng=direccion.lng, subtotal=subtotal), campo="direccion_id"
    )
    if not cotizacion.cumple_minimo:
        raise ValidationError(
            f"El subtotal no alcanza el pedido mínimo de la zona ({cotizacion.zona.pedido_minimo})",
            code="BELOW_MINIMUM",
            field="items",
        )
    return cotizacion.costo_envio


def _reservar(uow: PedidosUnitOfWork, pedido_id: int, linea: LineaCreate, producto: Producto) -> None:
    try:
        inventario.consumir_producto(
            uow, linea.producto_id, Decimal(linea.cantidad), TipoMovimiento.RESERVA, pedido_id=pedido_id
        )
    except ConflictError as e:
        if e.code != "INSUFFICIENT_STOCK":
            raise
        raise ConflictError(f"«{producto.nombre}»: {e.detail}", code=e.code, field="items") from e


def crear_pedido(
    uow: PedidosUnitOfWork,
    usuario: CurrentUser,
    datos: PedidoCreate,
    clave: str,
    ahora: datetime | None = None,
) -> tuple[PedidoRead, bool]:
    """Crea el pedido desde el carrito. Devuelve (pedido, creado): con una Idempotency-Key ya usada devuelve el
    pedido existente y `creado = False`, sin tocar nada. `ahora` solo se inyecta en las pruebas."""
    with uow:
        uow.pedidos.bloquear_clave(clave)
        existente = uow.pedidos.get_by_referencia(clave)
        if existente is not None:
            if existente.usuario_id != usuario.id:
                raise ConflictError("Esa Idempotency-Key ya se usó en otro pedido", code="IDEMPOTENCY_KEY_REUSED")
            return _pedido_read(uow, existente), False

        config.exigir_local_abierto(uow, ahora)  # RN-13

        forma = uow.formas_pago.get_by_id(datos.forma_pago_codigo)
        if forma is None or not forma.habilitado:
            raise ValidationError(
                f"La forma de pago {datos.forma_pago_codigo} no está habilitada",
                code="PAYMENT_METHOD_UNAVAILABLE",
                field="forma_pago_codigo",
            )

        productos = _validar_lineas(uow, datos.items)
        # Se bloquean los productos EN ORDEN de id y ANTES de insertar nada que los referencie: una fila con clave
        # foránea hacia el producto ya toma un bloqueo compartido sobre él, y pedir después el exclusivo haría que
        # dos pedidos simultáneos se esperen mutuamente (deadlock). Así se serializan sin bloquearse en círculo ni
        # vender el mismo stock.
        for producto_id in sorted(productos):
            uow.mov_productos.bloquear(producto_id)
        subtotal = sum((productos[i.producto_id].precio_base * i.cantidad for i in datos.items), Decimal(0))
        subtotal = subtotal.quantize(CENTAVO)
        costo_envio = _costo_de_envio(uow, usuario, datos.direccion_id, subtotal)

        # Snapshot monetario inmutable (RN-04): total = subtotal − descuento + costo_envio.
        descuento = Decimal("0.00")
        pedido = uow.pedidos.create(
            Pedido(
                usuario_id=usuario.id,
                estado_codigo="PENDIENTE",
                forma_pago_codigo=forma.codigo,
                direccion_id=datos.direccion_id,
                subtotal=subtotal,
                descuento=descuento,
                costo_envio=costo_envio,
                total=subtotal - descuento + costo_envio,
                external_reference=clave,
                notas=datos.notas,
            )
        )
        for linea in datos.items:
            producto = productos[linea.producto_id]
            detalle = uow.detalles.create(
                DetallePedido(
                    pedido_id=pedido.id,
                    producto_id=producto.id,
                    nombre_snapshot=producto.nombre,
                    precio_snapshot=producto.precio_base,
                    cantidad=linea.cantidad,
                )
            )
            for ingrediente_id in linea.exclusiones:
                uow.detalles.agregar_exclusion(detalle.id, ingrediente_id)  # type: ignore[arg-type]

        for linea in datos.items:
            _reservar(uow, pedido.id, linea, productos[linea.producto_id])  # type: ignore[arg-type]

        uow.historial.create(
            HistorialEstadoPedido(
                pedido_id=pedido.id, estado_desde=None, estado_hasta="PENDIENTE", usuario_id=usuario.id
            )
        )
        return _pedido_read(uow, pedido), True
