"""Producción (sección 8.3): planificar, iniciar, completar y cancelar órdenes.

Cada acción registra todos sus movimientos en UNA transacción y los marca con `orden_produccion_id`.
La explosión de materiales es de un solo nivel: una orden consume sus componentes directos como cualquier
insumo; los sub-ensambles (ingredientes elaborados) se producen antes con su propia orden.
"""

from decimal import ROUND_CEILING, Decimal

from app.core.deps import CurrentUser
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.fsm import ORDEN_TRANSICIONES, validar_transicion
from app.core.schemas import Paginated
from app.modules.inventario import service as inventario
from app.modules.produccion.models import EstadoOrden, OrdenProduccion
from app.modules.produccion.schemas import (
    ComponenteOrden,
    FiltrosOrdenes,
    OrdenCancelar,
    OrdenCompletar,
    OrdenCreate,
    OrdenRead,
)
from app.modules.produccion.uow import ProduccionUnitOfWork
from app.modules.productos.models import MovimientoIngrediente, TipoMovimiento

T = TipoMovimiento
CERO = Decimal(0)
MILESIMA = Decimal("0.001")
PLANIFICADO = {T.RESERVA: 1}
RESERVADO = {T.RESERVA: 1, T.LIBERACION_RESERVA: -1}


def _orden(uow: ProduccionUnitOfWork, orden_id: int, *, bloquear: bool = False) -> OrdenProduccion:
    orden = uow.ordenes.get_for_update(orden_id) if bloquear else uow.ordenes.get_by_id(orden_id)
    if orden is None:
        raise NotFoundError("Orden de producción no encontrada", code="ORDER_NOT_FOUND")
    return orden


def _nombre_resultado(uow: ProduccionUnitOfWork, orden: OrdenProduccion) -> str:
    if orden.producto_id is not None:
        producto = uow.productos.get_by_id(orden.producto_id, include_deleted=True)
        return producto.nombre if producto else ""
    ingrediente = uow.ingredientes.get_by_id(orden.ingrediente_id, include_deleted=True)  # type: ignore[arg-type]
    return ingrediente.nombre if ingrediente else ""


def _orden_read(uow: ProduccionUnitOfWork, orden: OrdenProduccion, *, con_componentes: bool = True) -> OrdenRead:
    lectura = OrdenRead.model_validate(orden)
    lectura.nombre = _nombre_resultado(uow, orden)
    if con_componentes:
        for ing_id, cantidad in sorted(uow.mov_ingredientes.por_orden(orden.id, PLANIFICADO).items()):  # type: ignore[arg-type]
            ingrediente = uow.ingredientes.get_by_id(ing_id, include_deleted=True)
            lectura.componentes.append(
                ComponenteOrden(
                    ingrediente_id=ing_id,
                    nombre=ingrediente.nombre if ingrediente else "",
                    cantidad=cantidad,
                    unidad_medida=ingrediente.unidad_medida if ingrediente else None,
                )
            )
    return lectura


def listar_ordenes(uow: ProduccionUnitOfWork, filtros: FiltrosOrdenes) -> Paginated[OrdenRead]:
    with uow:
        items, total = uow.ordenes.search(estado=filtros.estado, page=filtros.page, size=filtros.size)
        data = [_orden_read(uow, o, con_componentes=False) for o in items]
    return Paginated.build(data, total, filtros.page, filtros.size)


def obtener_orden(uow: ProduccionUnitOfWork, orden_id: int) -> OrdenRead:
    with uow:
        return _orden_read(uow, _orden(uow, orden_id))


def _explosion(uow: ProduccionUnitOfWork, datos: OrdenCreate) -> dict[int, Decimal]:
    """Receta × cantidad a producir, por insumo. Se redondea hacia arriba a la milésima para no reservar de menos."""
    if datos.producto_id is not None:
        if uow.productos.get_by_id(datos.producto_id) is None:
            raise NotFoundError("Producto no encontrado", code="PRODUCT_NOT_FOUND")
        receta = [
            (fila.ingrediente_id, fila.cantidad_requerida) for fila, _ in uow.recetas.de_producto(datos.producto_id)
        ]
    else:
        ingrediente = uow.ingredientes.get_by_id(datos.ingrediente_id)  # type: ignore[arg-type]
        if ingrediente is None:
            raise NotFoundError("Ingrediente no encontrado", code="INGREDIENT_NOT_FOUND")
        if not ingrediente.es_elaborado:
            raise ValidationError(
                "Solo un ingrediente elaborado se produce", code="INGREDIENT_NOT_ELABORATED", field="ingrediente_id"
            )
        receta = [
            (fila.componente_id, fila.cantidad_requerida) for fila, _ in uow.recetas.de_ingrediente(ingrediente.id)
        ]  # type: ignore[arg-type]
    if not receta:
        raise ValidationError("No tiene receta: no hay nada que consumir", code="NO_RECIPE")
    return {
        ing_id: (cantidad * datos.cantidad_a_producir).quantize(MILESIMA, rounding=ROUND_CEILING)
        for ing_id, cantidad in sorted(receta)
    }


def crear_orden(uow: ProduccionUnitOfWork, datos: OrdenCreate) -> OrdenRead:
    """Planificar: crea la orden y RESERVA cada componente. Si falta algún insumo → 409 y no queda nada."""
    with uow:
        necesidades = _explosion(uow, datos)
        for ing_id in necesidades:  # en orden de id: dos órdenes simultáneas no se bloquean entre sí en círculo
            uow.mov_ingredientes.bloquear(ing_id)
        faltantes = []
        for ing_id, necesaria in necesidades.items():
            disponible = uow.mov_ingredientes.stock_disponible(ing_id)
            if necesaria > disponible:
                ingrediente = uow.ingredientes.get_by_id(ing_id, include_deleted=True)
                faltantes.append(
                    f"{ingrediente.nombre if ingrediente else ing_id} (necesita {necesaria}, hay {disponible})"
                )
        if faltantes:
            raise ConflictError(
                "Stock insuficiente para planificar: " + "; ".join(faltantes), code="INSUFFICIENT_STOCK"
            )

        orden = uow.ordenes.create(
            OrdenProduccion(
                producto_id=datos.producto_id,
                ingrediente_id=datos.ingrediente_id,
                cantidad_a_producir=datos.cantidad_a_producir,
            )
        )
        for ing_id, cantidad in necesidades.items():
            inventario.consumir_ingrediente(uow, ing_id, cantidad, T.RESERVA, orden_produccion_id=orden.id)
        return _orden_read(uow, orden)


def iniciar_orden(uow: ProduccionUnitOfWork, orden_id: int, usuario: CurrentUser) -> OrdenRead:
    """PLANIFICADA → EN_PROCESO. No mueve stock."""
    with uow:
        orden = _orden(uow, orden_id, bloquear=True)
        validar_transicion(ORDEN_TRANSICIONES, orden.estado, EstadoOrden.EN_PROCESO, usuario.roles)
        uow.ordenes.update(orden, {"estado": EstadoOrden.EN_PROCESO})
        return _orden_read(uow, orden)


def _movimiento_insumo(
    uow: ProduccionUnitOfWork,
    orden_id: int,
    ing_id: int,
    tipo: TipoMovimiento,
    cantidad: Decimal,
    motivo: str | None = None,
) -> None:
    uow.mov_ingredientes.create(
        MovimientoIngrediente(
            ingrediente_id=ing_id, orden_produccion_id=orden_id, tipo_movimiento=tipo, cantidad=cantidad, motivo=motivo
        )
    )


def completar_orden(uow: ProduccionUnitOfWork, orden_id: int, datos: OrdenCompletar, usuario: CurrentUser) -> OrdenRead:
    """EN_PROCESO → COMPLETADA. Por componente: LIBERACION_RESERVA y SALIDA; del resultado: ENTRADA.

    La liberación va antes que la salida para no descontar dos veces el disponible: anula la reserva y la
    salida registra el consumo físico. Los componentes salen de lo que la orden RESERVÓ, no de la receta de
    hoy: si la receta cambió mientras tanto, igual se consume lo que se planificó.
    """
    if bool(datos.codigo_lote) != bool(datos.fecha_vencimiento):
        raise ValidationError(
            "Un lote necesita código y fecha de vencimiento juntos", code="LOTE_INCOMPLETE", field="codigo_lote"
        )
    with uow:
        orden = _orden(uow, orden_id, bloquear=True)
        validar_transicion(ORDEN_TRANSICIONES, orden.estado, EstadoOrden.COMPLETADA, usuario.roles)
        if orden.ingrediente_id is not None and datos.codigo_lote:
            raise ValidationError(
                "Solo el producto terminado puede tener lote", code="LOTE_ONLY_FOR_PRODUCT", field="codigo_lote"
            )

        for ing_id, cantidad in sorted(uow.mov_ingredientes.por_orden(orden.id, RESERVADO).items()):  # type: ignore[arg-type]
            _movimiento_insumo(uow, orden.id, ing_id, T.LIBERACION_RESERVA, cantidad)  # type: ignore[arg-type]
            _movimiento_insumo(uow, orden.id, ing_id, T.SALIDA, cantidad)  # type: ignore[arg-type]

        if orden.producto_id is not None:
            inventario.ingresar_producto(
                uow,
                orden.producto_id,
                orden.cantidad_a_producir,
                T.ENTRADA,
                codigo_lote=datos.codigo_lote,
                fecha_vencimiento=datos.fecha_vencimiento,
                orden_produccion_id=orden.id,
            )
        else:
            _movimiento_insumo(uow, orden.id, orden.ingrediente_id, T.ENTRADA, orden.cantidad_a_producir)  # type: ignore[arg-type]

        uow.ordenes.update(orden, {"estado": EstadoOrden.COMPLETADA})
        return _orden_read(uow, orden)


def cancelar_orden(uow: ProduccionUnitOfWork, orden_id: int, datos: OrdenCancelar, usuario: CurrentUser) -> OrdenRead:
    """PLANIFICADA o EN_PROCESO → CANCELADA con motivo. LIBERACION_RESERVA por componente: el real nunca se tocó."""
    with uow:
        orden = _orden(uow, orden_id, bloquear=True)
        validar_transicion(ORDEN_TRANSICIONES, orden.estado, EstadoOrden.CANCELADA, usuario.roles)
        for ing_id, cantidad in sorted(uow.mov_ingredientes.por_orden(orden.id, RESERVADO).items()):  # type: ignore[arg-type]
            _movimiento_insumo(uow, orden.id, ing_id, T.LIBERACION_RESERVA, cantidad, datos.motivo)  # type: ignore[arg-type]
        uow.ordenes.update(orden, {"estado": EstadoOrden.CANCELADA, "motivo_cancelacion": datos.motivo})
        return _orden_read(uow, orden)
