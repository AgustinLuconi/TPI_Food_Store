"""Lógica del catálogo (sin estado): productos, ingredientes y recetas.

Lanza excepciones de dominio, nunca HTTPException, y no hace commit (lo hace el Unit of Work).
"""

from app.core import media
from app.core.deps import CurrentUser
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.schemas import Estado, Paginated
from app.modules.productos import recetas
from app.modules.productos.models import Ingrediente, Producto, ProductoIngrediente, RecetaIngrediente
from app.modules.productos.schemas import (
    CategoriaDelProducto,
    FiltrosIngredientes,
    FiltrosProductos,
    IngredienteCreate,
    IngredienteDelProducto,
    IngredienteRead,
    IngredienteUpdate,
    ProductoCreate,
    ProductoItem,
    ProductoRead,
    ProductoUpdate,
    RecetaIngredienteRead,
    RecetaIngredienteUpdate,
    RecetaProductoUpdate,
)
from app.modules.productos.uow import ProductosUnitOfWork

# Roles que pueden ver registros dados de baja en los endpoints públicos del catálogo.
ROLES_GESTION_CATALOGO = frozenset({"ADMIN", "STOCK"})


def _es_gestion(usuario: CurrentUser | None) -> bool:
    return usuario is not None and bool(usuario.roles & ROLES_GESTION_CATALOGO)


def _estado_permitido(estado: Estado, usuario: CurrentUser | None) -> Estado:
    """El público solo ve activos: `incluir_inactivos` es solo para los roles de gestión (sección 6)."""
    return estado if _es_gestion(usuario) else "activos"


# ==============================================================================================
# Productos
# ==============================================================================================


def _obtener_producto(uow: ProductosUnitOfWork, producto_id: int, usuario: CurrentUser | None = None) -> Producto:
    """Un producto dado de baja es 404 para el público y visible para gestión (para reactivarlo)."""
    producto = uow.productos.get_by_id(producto_id, include_deleted=_es_gestion(usuario))
    if producto is None:
        raise NotFoundError("Producto no encontrado", code="PRODUCT_NOT_FOUND")
    return producto


def _categorias_read(filas: list[tuple[int, str, bool]]) -> list[CategoriaDelProducto]:
    return [CategoriaDelProducto(id=i, nombre=n, es_principal=p) for i, n, p in filas]


def _producto_item(producto: Producto, categorias: list[tuple[int, str, bool]]) -> ProductoItem:
    return ProductoItem.model_validate(producto).model_copy(update={"categorias": _categorias_read(categorias)})


def _producto_read(uow: ProductosUnitOfWork, producto: Producto) -> ProductoRead:
    receta = uow.recetas.de_producto(producto.id)  # type: ignore[arg-type]
    categorias = uow.productos.categorias_de([producto.id])[producto.id]  # type: ignore[list-item,index]
    ingredientes = [
        IngredienteDelProducto(
            ingrediente_id=ing.id,  # type: ignore[arg-type]
            nombre=ing.nombre,
            es_alergeno=ing.es_alergeno,
            cantidad_requerida=fila.cantidad_requerida,
            unidad_medida=fila.unidad_medida,
            es_removible=fila.es_removible,
        )
        for fila, ing in receta
    ]
    return ProductoRead.model_validate(producto).model_copy(
        update={
            "categorias": _categorias_read(categorias),
            "ingredientes": ingredientes,
            "alergenos": sorted({i.nombre for i in ingredientes if i.es_alergeno}),
        }
    )


def _validar_categorias(uow: ProductosUnitOfWork, categoria_ids: list[int]) -> None:
    for cid in categoria_ids:
        if uow.categorias.get_by_id(cid) is None:
            raise ValidationError(
                f"La categoría {cid} no existe o está dada de baja", code="INVALID_CATEGORY", field="categoria_ids"
            )


def listar_productos(
    uow: ProductosUnitOfWork, filtros: FiltrosProductos, usuario: CurrentUser | None
) -> Paginated[ProductoItem]:
    """Listado público y paginado. Los dados de baja solo los ven ADMIN y STOCK."""
    with uow:
        categoria_ids = None
        if filtros.categoria_id is not None:
            # Una categoría incluye a sus subcategorías: "Comidas" muestra las pizzas.
            categoria_ids = {filtros.categoria_id, *uow.categorias.ids_descendientes(filtros.categoria_id)}
        items, total = uow.productos.search(
            search=filtros.search,
            categoria_ids=categoria_ids,
            disponible=filtros.disponible,
            estado=_estado_permitido(filtros.estado_efectivo, usuario),
            orden=filtros.orden,
            sentido=filtros.sentido,
            page=filtros.page,
            size=filtros.size,
        )
        categorias = uow.productos.categorias_de([p.id for p in items])  # type: ignore[misc]
        data = [_producto_item(p, categorias[p.id]) for p in items]  # type: ignore[index]
    return Paginated.build(data, total, filtros.page, filtros.size)


def obtener_producto(uow: ProductosUnitOfWork, producto_id: int, usuario: CurrentUser | None) -> ProductoRead:
    """Detalle con categorías, receta y alérgenos."""
    with uow:
        return _producto_read(uow, _obtener_producto(uow, producto_id, usuario))


def crear_producto(uow: ProductosUnitOfWork, datos: ProductoCreate) -> ProductoRead:
    """Alta. Las categorías deben estar activas; la principal es la indicada o la primera."""
    with uow:
        _validar_categorias(uow, datos.categoria_ids)
        producto = uow.productos.create(
            Producto(
                nombre=datos.nombre,
                descripcion=datos.descripcion,
                precio_base=datos.precio_base,
                disponible=datos.disponible,
                stock_minimo=datos.stock_minimo,
            )
        )
        principal = datos.categoria_principal_id or (datos.categoria_ids[0] if datos.categoria_ids else None)
        uow.productos.reemplazar_categorias(producto.id, datos.categoria_ids, principal)  # type: ignore[arg-type]
        return _producto_read(uow, producto)


def actualizar_producto(uow: ProductosUnitOfWork, producto_id: int, datos: ProductoUpdate) -> ProductoRead:
    """Edición parcial. `stock_cantidad` y la imagen no se editan por acá (ver /imagen y el ledger)."""
    cambios = datos.model_dump(exclude_unset=True, exclude={"categoria_ids", "categoria_principal_id"})
    for campo in ("nombre", "precio_base", "disponible", "stock_minimo"):
        if campo in cambios and cambios[campo] is None:
            raise ValidationError(f"{campo} no puede ser nulo", field=campo)
    with uow:
        producto = _obtener_producto(uow, producto_id)
        if datos.categoria_ids is not None:
            _validar_categorias(uow, datos.categoria_ids)
            principal = datos.categoria_principal_id or (datos.categoria_ids[0] if datos.categoria_ids else None)
            uow.productos.reemplazar_categorias(producto_id, datos.categoria_ids, principal)
        if cambios:
            uow.productos.update(producto, cambios)
        return _producto_read(uow, producto)


def eliminar_producto(uow: ProductosUnitOfWork, producto_id: int) -> None:
    """Baja lógica (RN-16): asigna deleted_at y pone disponible = false."""
    with uow:
        producto = _obtener_producto(uow, producto_id)
        uow.productos.update(producto, {"disponible": False})
        uow.productos.soft_delete(producto)


def reactivar_producto(uow: ProductosUnitOfWork, producto_id: int) -> ProductoRead:
    """Reactivar limpia deleted_at. Vuelve como no disponible: habilitarlo es una decisión comercial."""
    with uow:
        producto = uow.productos.get_by_id(producto_id, include_deleted=True)
        if producto is None:
            raise NotFoundError("Producto no encontrado", code="PRODUCT_NOT_FOUND")
        if producto.deleted_at is None:
            raise ConflictError("El producto ya está activo", code="ALREADY_ACTIVE")
        uow.productos.restore(producto)
        return _producto_read(uow, producto)


def cambiar_disponibilidad(uow: ProductosUnitOfWork, producto_id: int, disponible: bool) -> ProductoRead:
    """Visibilidad comercial (ADMIN y STOCK), independiente del stock."""
    with uow:
        producto = _obtener_producto(uow, producto_id)
        uow.productos.update(producto, {"disponible": disponible})
        return _producto_read(uow, producto)


def subir_imagen(uow: ProductosUnitOfWork, producto_id: int, contenido: bytes) -> ProductoRead:
    """Valida tipo real y tamaño, guarda con nombre UUID y persiste solo la URL."""
    with uow:
        producto = _obtener_producto(uow, producto_id)
        nueva = media.guardar_imagen(contenido, "productos")  # valida antes de escribir
        anterior = producto.imagen_url
        try:
            uow.productos.update(producto, {"imagen_url": nueva})
        except Exception:
            media.borrar_imagen(nueva)
            raise
        media.borrar_imagen(anterior)
        return _producto_read(uow, producto)


# ----------------------------------------------------------------------------------------------
# Receta de venta
# ----------------------------------------------------------------------------------------------


def _validar_unidad(
    uow: ProductosUnitOfWork,
    ingrediente: Ingrediente,
    unidad: str,
    *,
    excluir_producto_id: int | None = None,
    excluir_padre_id: int | None = None,
) -> None:
    """RN-10: la primera receta que usa un ingrediente fija su unidad; las demás deben coincidir."""
    fijada = uow.recetas.unidad_de(
        ingrediente.id,  # type: ignore[arg-type]
        excluir_producto_id=excluir_producto_id,
        excluir_padre_id=excluir_padre_id,
    )
    if fijada is not None and fijada != unidad:
        raise ValidationError(
            f"«{ingrediente.nombre}» se mide en {fijada}: no puede usarse en {unidad}",
            code="UNIT_MISMATCH",
            field="unidad_medida",
        )


def _ingredientes_validos(uow: ProductosUnitOfWork, ids: list[int]) -> dict[int, Ingrediente]:
    if len(set(ids)) != len(ids):
        raise ValidationError(
            "Un ingrediente no puede repetirse en la receta", code="DUPLICATE_INGREDIENT", field="items"
        )
    encontrados = uow.ingredientes.get_activos(ids)
    faltan = sorted(set(ids) - set(encontrados))
    if faltan:
        raise ValidationError(
            f"Ingredientes inexistentes o dados de baja: {faltan}", code="UNKNOWN_INGREDIENT", field="items"
        )
    return encontrados


def obtener_receta_producto(
    uow: ProductosUnitOfWork, producto_id: int, usuario: CurrentUser | None
) -> list[IngredienteDelProducto]:
    """Receta de venta (pública, con alérgenos)."""
    with uow:
        producto = _obtener_producto(uow, producto_id, usuario)
        return _producto_read(uow, producto).ingredientes


def reemplazar_receta_producto(
    uow: ProductosUnitOfWork, producto_id: int, datos: RecetaProductoUpdate
) -> list[IngredienteDelProducto]:
    """Reemplaza la receta de venta completa. Aplica RN-10 (una unidad por ingrediente)."""
    with uow:
        producto = _obtener_producto(uow, producto_id)
        ingredientes = _ingredientes_validos(uow, [i.ingrediente_id for i in datos.items])
        for item in datos.items:
            _validar_unidad(uow, ingredientes[item.ingrediente_id], item.unidad_medida, excluir_producto_id=producto_id)
        uow.recetas.reemplazar_de_producto(
            producto_id,
            [
                ProductoIngrediente(
                    producto_id=producto_id,
                    ingrediente_id=i.ingrediente_id,
                    cantidad_requerida=i.cantidad_requerida,
                    unidad_medida=i.unidad_medida,
                    es_removible=i.es_removible,
                )
                for i in datos.items
            ],
        )
        return _producto_read(uow, producto).ingredientes


# ==============================================================================================
# Ingredientes
# ==============================================================================================


def _obtener_ingrediente(uow: ProductosUnitOfWork, ingrediente_id: int, *, incluir_baja: bool = False) -> Ingrediente:
    ingrediente = uow.ingredientes.get_by_id(ingrediente_id, include_deleted=incluir_baja)
    if ingrediente is None:
        raise NotFoundError("Ingrediente no encontrado", code="INGREDIENT_NOT_FOUND")
    return ingrediente


def _nombre_libre(uow: ProductosUnitOfWork, nombre: str, *, excluir_id: int | None = None) -> None:
    """El nombre sigue siendo único tras la baja lógica: se informa para ofrecer reactivar."""
    existente = uow.ingredientes.get_by_nombre(nombre)
    if existente is not None and existente.id != excluir_id:
        dado_de_baja = existente.deleted_at is not None
        raise ConflictError(
            "Ya existe un ingrediente con ese nombre" + (" (dado de baja: se puede reactivar)" if dado_de_baja else ""),
            code="INGREDIENT_INACTIVE_NAME" if dado_de_baja else "DUPLICATE_NAME",
            field="nombre",
        )


def listar_ingredientes(uow: ProductosUnitOfWork, filtros: FiltrosIngredientes) -> Paginated[IngredienteRead]:
    with uow:
        items, total = uow.ingredientes.search(
            search=filtros.search,
            es_alergeno=filtros.es_alergeno,
            es_elaborado=filtros.es_elaborado,
            estado=filtros.estado_efectivo,
            orden=filtros.orden,
            sentido=filtros.sentido,
            page=filtros.page,
            size=filtros.size,
        )
        data = [IngredienteRead.model_validate(i) for i in items]
    return Paginated.build(data, total, filtros.page, filtros.size)


def obtener_ingrediente(uow: ProductosUnitOfWork, ingrediente_id: int) -> IngredienteRead:
    with uow:
        return IngredienteRead.model_validate(_obtener_ingrediente(uow, ingrediente_id, incluir_baja=True))


def crear_ingrediente(uow: ProductosUnitOfWork, datos: IngredienteCreate) -> IngredienteRead:
    with uow:
        _nombre_libre(uow, datos.nombre)
        return IngredienteRead.model_validate(uow.ingredientes.create(Ingrediente(**datos.model_dump())))


def actualizar_ingrediente(uow: ProductosUnitOfWork, ingrediente_id: int, datos: IngredienteUpdate) -> IngredienteRead:
    """Edición parcial. Un ingrediente con receta no puede dejar de ser elaborado (RN-11)."""
    cambios = datos.model_dump(exclude_unset=True)
    for campo in ("nombre", "es_alergeno", "es_elaborado", "stock_minimo"):
        if campo in cambios and cambios[campo] is None:
            raise ValidationError(f"{campo} no puede ser nulo", field=campo)
    with uow:
        ingrediente = _obtener_ingrediente(uow, ingrediente_id)
        if "nombre" in cambios:
            _nombre_libre(uow, cambios["nombre"], excluir_id=ingrediente_id)
        if cambios.get("es_elaborado") is False and uow.ingredientes.tiene_receta(ingrediente_id):
            raise ConflictError(
                "Tiene receta: primero hay que vaciarla para dejar de ser elaborado",
                code="HAS_RECIPE",
                field="es_elaborado",
            )
        uow.ingredientes.update(ingrediente, cambios)
        return IngredienteRead.model_validate(ingrediente)


def eliminar_ingrediente(uow: ProductosUnitOfWork, ingrediente_id: int) -> None:
    """Baja lógica (RN-16). No se anula un ingrediente que forma parte de una receta activa."""
    with uow:
        ingrediente = _obtener_ingrediente(uow, ingrediente_id)
        if uow.ingredientes.count_productos_activos_que_lo_usan(ingrediente_id):
            raise ConflictError("No se puede dar de baja: lo usan productos activos", code="INGREDIENT_IN_USE")
        if uow.ingredientes.count_elaborados_activos_que_lo_usan(ingrediente_id):
            raise ConflictError(
                "No se puede dar de baja: lo usan ingredientes elaborados activos", code="INGREDIENT_IN_USE"
            )
        uow.ingredientes.soft_delete(ingrediente)


def reactivar_ingrediente(uow: ProductosUnitOfWork, ingrediente_id: int) -> IngredienteRead:
    """Reactivar limpia deleted_at."""
    with uow:
        ingrediente = _obtener_ingrediente(uow, ingrediente_id, incluir_baja=True)
        if ingrediente.deleted_at is None:
            raise ConflictError("El ingrediente ya está activo", code="ALREADY_ACTIVE")
        uow.ingredientes.restore(ingrediente)
        return IngredienteRead.model_validate(ingrediente)


# ----------------------------------------------------------------------------------------------
# Receta de un ingrediente elaborado
# ----------------------------------------------------------------------------------------------


def _receta_ingrediente_read(uow: ProductosUnitOfWork, padre_id: int) -> list[RecetaIngredienteRead]:
    return [
        RecetaIngredienteRead(
            componente_id=ing.id,  # type: ignore[arg-type]
            nombre=ing.nombre,
            cantidad_requerida=fila.cantidad_requerida,
            unidad_medida=fila.unidad_medida,
        )
        for fila, ing in uow.recetas.de_ingrediente(padre_id)
    ]


def obtener_receta_ingrediente(uow: ProductosUnitOfWork, ingrediente_id: int) -> list[RecetaIngredienteRead]:
    with uow:
        _obtener_ingrediente(uow, ingrediente_id)
        return _receta_ingrediente_read(uow, ingrediente_id)


def reemplazar_receta_ingrediente(
    uow: ProductosUnitOfWork, ingrediente_id: int, datos: RecetaIngredienteUpdate
) -> list[RecetaIngredienteRead]:
    """Reemplaza la receta de un ingrediente elaborado.

    RN-11: solo es válida si el padre es elaborado y no puede tener ciclos. RN-10: una unidad por ingrediente.
    """
    with uow:
        padre = _obtener_ingrediente(uow, ingrediente_id)
        if not padre.es_elaborado:
            raise ValidationError(
                "Solo un ingrediente elaborado puede tener receta", code="NOT_ELABORATED", field="items"
            )
        ids = [i.componente_id for i in datos.items]
        if ingrediente_id in ids:
            raise ValidationError(
                "Un ingrediente no puede ser componente de sí mismo", code="SELF_REFERENCE", field="items"
            )
        componentes = _ingredientes_validos(uow, ids)
        if recetas.hay_ciclo(uow.recetas.aristas(ingrediente_id), ingrediente_id, ids):
            raise ValidationError(
                "La receta tendría un ciclo: algún componente ya usa a este ingrediente",
                code="RECIPE_CYCLE",
                field="items",
            )
        for item in datos.items:
            _validar_unidad(uow, componentes[item.componente_id], item.unidad_medida, excluir_padre_id=ingrediente_id)
        uow.recetas.reemplazar_de_ingrediente(
            ingrediente_id,
            [
                RecetaIngrediente(
                    ingrediente_padre_id=ingrediente_id,
                    componente_id=i.componente_id,
                    cantidad_requerida=i.cantidad_requerida,
                    unidad_medida=i.unidad_medida,
                )
                for i in datos.items
            ],
        )
        return _receta_ingrediente_read(uow, ingrediente_id)
