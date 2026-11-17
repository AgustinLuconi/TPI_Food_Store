"""Lógica del inventario: doble ledger, stock derivado, lotes y FEFO (sección 8, RN-06 a RN-09).

Lanza excepciones de dominio y no hace commit (lo hace el Unit of Work). Las funciones `consumir_*`
las reutilizan los pedidos y la producción para generar movimientos del sistema dentro de SU transacción.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.db_types import utcnow
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.schemas import Paginated
from app.modules.inventario.schemas import (
    FiltrosMovimientos,
    LotePorVencer,
    LoteRead,
    MovimientoCreate,
    MovimientoProductoCreate,
    MovimientoRead,
    StockRead,
)
from app.modules.inventario.stock import MOTIVOS_MERMA, TIPOS_MANUALES, TIPOS_QUE_RESTAN, LoteDisponible, repartir_fefo
from app.modules.inventario.uow import InventarioUnitOfWork
from app.modules.productos.models import (
    Lote,
    MovimientoIngrediente,
    MovimientoStock,
    TipoMovimiento,
)

T = TipoMovimiento
CERO = Decimal(0)


def _aware(valor: datetime) -> datetime:
    """Una fecha sin zona se interpreta como UTC."""
    return valor if valor.tzinfo else valor.replace(tzinfo=UTC)


def _stock_insuficiente(pedido: Decimal, disponible: Decimal) -> ConflictError:
    return ConflictError(
        f"Stock insuficiente: se piden {pedido} y hay {disponible} disponibles",
        code="INSUFFICIENT_STOCK",
        field="cantidad",
    )


def _validar_manual(datos: MovimientoCreate) -> None:
    """RN-07 (solo 4 tipos a mano) y RN-08 (la merma exige un motivo de la lista)."""
    if datos.tipo_movimiento not in TIPOS_MANUALES:
        raise ValidationError(
            "Solo ENTRADA, MERMA, AJUSTE_POSITIVO y AJUSTE_NEGATIVO se registran manualmente; "
            "SALIDA, RESERVA y LIBERACION_RESERVA las genera el sistema",
            code="MOVEMENT_NOT_MANUAL",
            field="tipo_movimiento",
        )
    if datos.tipo_movimiento == T.MERMA and datos.motivo not in MOTIVOS_MERMA:
        raise ValidationError(
            f"Una MERMA exige un motivo: {', '.join(MOTIVOS_MERMA)}", code="MERMA_REASON_REQUIRED", field="motivo"
        )


# ==============================================================================================
# Productos
# ==============================================================================================


def _producto(uow: InventarioUnitOfWork, producto_id: int, *, para_escribir: bool = False):
    """Para consultar vale también un producto dado de baja; para mover stock, no."""
    producto = uow.productos.get_by_id(producto_id, include_deleted=not para_escribir)
    if producto is None:
        raise NotFoundError("Producto no encontrado", code="PRODUCT_NOT_FOUND")
    return producto


def obtener_stock_producto(uow: InventarioUnitOfWork, producto_id: int) -> StockRead:
    with uow:
        _producto(uow, producto_id)
        return StockRead(
            id=producto_id,
            stock_real=uow.mov_productos.stock_real(producto_id),
            stock_disponible=uow.mov_productos.stock_disponible(producto_id),
        )


def listar_movimientos_producto(
    uow: InventarioUnitOfWork, producto_id: int, filtros: FiltrosMovimientos
) -> Paginated[MovimientoRead]:
    with uow:
        _producto(uow, producto_id)
        items, total = uow.mov_productos.listar(producto_id, tipo=filtros.tipo, page=filtros.page, size=filtros.size)
        data = [MovimientoRead.model_validate(m) for m in items]
    return Paginated.build(data, total, filtros.page, filtros.size)


def _lote_read(lote: Lote, real: Decimal, disponible: Decimal, ahora: datetime) -> LoteRead:
    return LoteRead(
        id=lote.id,  # type: ignore[arg-type]
        codigo_lote=lote.codigo_lote,
        fecha_vencimiento=lote.fecha_vencimiento,
        fecha_ingreso=lote.fecha_ingreso,
        cantidad_inicial=lote.cantidad_inicial,
        stock_real=real,
        stock_disponible=disponible,
        vencido=lote.fecha_vencimiento <= ahora,
    )


def lotes_de_producto(uow: InventarioUnitOfWork, producto_id: int) -> list[LoteRead]:
    """Lotes con su stock real/disponible y vencimiento, del que vence antes al que vence después."""
    with uow:
        _producto(uow, producto_id)
        stocks = uow.mov_productos.stock_por_lote(producto_id)
        ahora = utcnow()
        return [
            _lote_read(lote, *stocks.get(lote.id, (CERO, CERO)), ahora)  # type: ignore[arg-type]
            for lote in uow.lotes.de_producto(producto_id)
        ]


def lotes_por_vencer(uow: InventarioUnitOfWork, dias: int) -> list[LotePorVencer]:
    """Lotes con stock que vencen dentro de `dias` días o que ya vencieron (para darlos de baja con MERMA)."""
    with uow:
        ahora = utcnow()
        candidatos = uow.lotes.vencen_antes_de(ahora + timedelta(days=dias))
        stocks = uow.mov_productos.stock_de_lotes([lote.id for lote, _ in candidatos])  # type: ignore[misc]
        resultado = []
        for lote, nombre in candidatos:
            real, disponible = stocks.get(lote.id, (CERO, CERO))  # type: ignore[arg-type]
            if real <= 0:
                continue
            base = _lote_read(lote, real, disponible, ahora)
            resultado.append(
                LotePorVencer(
                    **base.model_dump(),
                    producto_id=lote.producto_id,
                    producto_nombre=nombre,
                    dias_restantes=(lote.fecha_vencimiento - ahora).days,
                )
            )
        return resultado


def consumir_producto(
    uow: InventarioUnitOfWork,
    producto_id: int,
    cantidad: Decimal,
    tipo: TipoMovimiento,
    *,
    motivo: str | None = None,
    pedido_id: int | None = None,
    orden_produccion_id: int | None = None,
    solo_vigentes: bool = True,
) -> list[MovimientoStock]:
    """RN-09: genera los movimientos que RESTAN (SALIDA, RESERVA, MERMA, AJUSTE_NEGATIVO) repartidos por FEFO.

    Primero se toman los lotes que vencen antes; lo que no tiene lote se toma al final. Nunca se toca lo
    que ya está reservado: si no alcanza el disponible → 409 INSUFFICIENT_STOCK. `solo_vigentes=False`
    permite incluir los lotes vencidos (para darlos de baja con MERMA). Quien llama debe haber bloqueado
    el producto (`mov_productos.bloquear`) para que dos pedidos simultáneos no vendan el mismo stock.
    """
    disponible = uow.mov_productos.stock_disponible(producto_id)
    if cantidad > disponible:
        raise _stock_insuficiente(cantidad, disponible)

    ahora = utcnow()
    por_lote = uow.mov_productos.stock_por_lote(producto_id)
    lotes = {lote.id: lote for lote in uow.lotes.de_producto(producto_id)}
    candidatos = [
        LoteDisponible(lote_id, lote.fecha_vencimiento, por_lote.get(lote_id, (CERO, CERO))[1])  # type: ignore[arg-type]
        for lote_id, lote in lotes.items()
        if not solo_vigentes or lote.fecha_vencimiento > ahora
    ]
    plan, faltante = repartir_fefo(candidatos, cantidad)
    if faltante > 0:
        # Lo que los lotes no cubren sale del stock que se cargó sin lote.
        sin_lote = disponible - sum((d for _, d in por_lote.values()), CERO)
        if faltante > sin_lote:
            raise _stock_insuficiente(cantidad, disponible - (faltante - max(sin_lote, CERO)))
        plan.append((None, faltante))  # type: ignore[arg-type]

    return [
        uow.mov_productos.create(
            MovimientoStock(
                producto_id=producto_id,
                lote_id=lote_id,
                pedido_id=pedido_id,
                orden_produccion_id=orden_produccion_id,
                tipo_movimiento=tipo,
                cantidad=parte,
                motivo=motivo,
            )
        )
        for lote_id, parte in plan
    ]


def registrar_movimiento_producto(
    uow: InventarioUnitOfWork, producto_id: int, datos: MovimientoProductoCreate
) -> list[MovimientoRead]:
    """Alta manual en el ledger del producto. Devuelve un movimiento por lote afectado (RN-09)."""
    _validar_manual(datos)
    tipo = datos.tipo_movimiento
    if (datos.codigo_lote or datos.fecha_vencimiento) and tipo != T.ENTRADA:
        raise ValidationError("Solo una ENTRADA puede crear un lote", code="LOTE_ONLY_IN_ENTRADA", field="codigo_lote")
    if bool(datos.codigo_lote) != bool(datos.fecha_vencimiento):
        raise ValidationError(
            "Un lote necesita código y fecha de vencimiento juntos", code="LOTE_INCOMPLETE", field="codigo_lote"
        )

    with uow:
        _producto(uow, producto_id, para_escribir=True)
        uow.mov_productos.bloquear(producto_id)

        if tipo in TIPOS_QUE_RESTAN:
            # La merma de lotes vencidos es justamente para lo que sirve el motivo VENCIMIENTO.
            movimientos = consumir_producto(
                uow, producto_id, datos.cantidad, tipo, motivo=datos.motivo, solo_vigentes=False
            )
        else:
            lote_id = None
            if datos.codigo_lote and datos.fecha_vencimiento:
                vencimiento = _aware(datos.fecha_vencimiento)
                if vencimiento <= utcnow():
                    raise ValidationError(
                        "No se puede ingresar un lote ya vencido", code="LOTE_EXPIRED", field="fecha_vencimiento"
                    )
                if uow.lotes.por_codigo(producto_id, datos.codigo_lote):
                    raise ConflictError(
                        f"El lote {datos.codigo_lote} ya existe para este producto",
                        code="LOTE_DUPLICATED",
                        field="codigo_lote",
                    )
                lote_id = uow.lotes.create(
                    Lote(
                        producto_id=producto_id,
                        codigo_lote=datos.codigo_lote,
                        fecha_vencimiento=vencimiento,
                        cantidad_inicial=datos.cantidad,
                    )
                ).id
            movimientos = [
                uow.mov_productos.create(
                    MovimientoStock(
                        producto_id=producto_id,
                        lote_id=lote_id,
                        tipo_movimiento=tipo,
                        cantidad=datos.cantidad,
                        motivo=datos.motivo,
                    )
                )
            ]
        return [MovimientoRead.model_validate(m) for m in movimientos]


# ==============================================================================================
# Ingredientes (insumos): sin lotes
# ==============================================================================================


def _ingrediente(uow: InventarioUnitOfWork, ingrediente_id: int, *, para_escribir: bool = False):
    ingrediente = uow.ingredientes.get_by_id(ingrediente_id, include_deleted=not para_escribir)
    if ingrediente is None:
        raise NotFoundError("Ingrediente no encontrado", code="INGREDIENT_NOT_FOUND")
    return ingrediente


def obtener_stock_ingrediente(uow: InventarioUnitOfWork, ingrediente_id: int) -> StockRead:
    with uow:
        _ingrediente(uow, ingrediente_id)
        return StockRead(
            id=ingrediente_id,
            stock_real=uow.mov_ingredientes.stock_real(ingrediente_id),
            stock_disponible=uow.mov_ingredientes.stock_disponible(ingrediente_id),
        )


def listar_movimientos_ingrediente(
    uow: InventarioUnitOfWork, ingrediente_id: int, filtros: FiltrosMovimientos
) -> Paginated[MovimientoRead]:
    with uow:
        _ingrediente(uow, ingrediente_id)
        items, total = uow.mov_ingredientes.listar(
            ingrediente_id, tipo=filtros.tipo, page=filtros.page, size=filtros.size
        )
        data = [MovimientoRead.model_validate(m) for m in items]
    return Paginated.build(data, total, filtros.page, filtros.size)


def consumir_ingrediente(
    uow: InventarioUnitOfWork,
    ingrediente_id: int,
    cantidad: Decimal,
    tipo: TipoMovimiento,
    *,
    motivo: str | None = None,
    orden_produccion_id: int | None = None,
) -> MovimientoIngrediente:
    """Movimiento que RESTA del insumo (sin lotes). Nunca toca lo reservado → 409 si no alcanza."""
    disponible = uow.mov_ingredientes.stock_disponible(ingrediente_id)
    if cantidad > disponible:
        raise _stock_insuficiente(cantidad, disponible)
    return uow.mov_ingredientes.create(
        MovimientoIngrediente(
            ingrediente_id=ingrediente_id,
            orden_produccion_id=orden_produccion_id,
            tipo_movimiento=tipo,
            cantidad=cantidad,
            motivo=motivo,
        )
    )


def registrar_movimiento_ingrediente(
    uow: InventarioUnitOfWork, ingrediente_id: int, datos: MovimientoCreate
) -> MovimientoRead:
    _validar_manual(datos)
    with uow:
        _ingrediente(uow, ingrediente_id, para_escribir=True)
        uow.mov_ingredientes.bloquear(ingrediente_id)
        if datos.tipo_movimiento in TIPOS_QUE_RESTAN:
            movimiento = consumir_ingrediente(
                uow, ingrediente_id, datos.cantidad, datos.tipo_movimiento, motivo=datos.motivo
            )
        else:
            movimiento = uow.mov_ingredientes.create(
                MovimientoIngrediente(
                    ingrediente_id=ingrediente_id,
                    tipo_movimiento=datos.tipo_movimiento,
                    cantidad=datos.cantidad,
                    motivo=datos.motivo,
                )
            )
        return MovimientoRead.model_validate(movimiento)
