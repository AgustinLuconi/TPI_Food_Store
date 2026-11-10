"""Lógica de categorías: árbol jerárquico con baja lógica validada."""

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.schemas import Paginated
from app.modules.categorias.models import Categoria
from app.modules.categorias.repository import Estado
from app.modules.categorias.schemas import CategoriaCreate, CategoriaNode, CategoriaRead, CategoriaUpdate
from app.modules.categorias.uow import CategoriasUnitOfWork


def _obtener(uow: CategoriasUnitOfWork, categoria_id: int, *, incluir_baja: bool = False) -> Categoria:
    categoria = uow.categorias.get_by_id(categoria_id, include_deleted=incluir_baja)
    if categoria is None:
        raise NotFoundError("Categoría no encontrada", code="CATEGORY_NOT_FOUND")
    return categoria


def _validar_padre(uow: CategoriasUnitOfWork, parent_id: int | None) -> None:
    if parent_id is not None and uow.categorias.get_by_id(parent_id) is None:
        raise ValidationError(
            "La categoría padre no existe o está dada de baja", code="INVALID_PARENT", field="parent_id"
        )


def arbol(uow: CategoriasUnitOfWork) -> list[CategoriaNode]:
    """Árbol de categorías activas (público)."""
    with uow:
        categorias = uow.categorias.arbol_activo()
        nodos = {
            c.id: CategoriaNode(id=c.id, parent_id=c.parent_id, nombre=c.nombre, descripcion=c.descripcion)  # type: ignore[arg-type]
            for c in categorias
        }
    raices: list[CategoriaNode] = []
    for c in categorias:  # ya vienen ordenadas por nombre
        nodo = nodos[c.id]  # type: ignore[index]
        (nodos[c.parent_id].children if c.parent_id in nodos else raices).append(nodo)
    return raices


def listar(
    uow: CategoriasUnitOfWork, *, search: str | None, estado: Estado, page: int, size: int
) -> Paginated[CategoriaRead]:
    with uow:
        items, total = uow.categorias.search(search=search, estado=estado, page=page, size=size)
        nombres = uow.categorias.nombres_por_id({c.parent_id for c in items if c.parent_id is not None})
        data = [
            CategoriaRead.model_validate(c).model_copy(update={"parent_nombre": nombres.get(c.parent_id)})  # type: ignore[arg-type]
            for c in items
        ]
    return Paginated.build(data, total, page, size)


def obtener(uow: CategoriasUnitOfWork, categoria_id: int) -> CategoriaRead:
    with uow:
        return CategoriaRead.model_validate(_obtener(uow, categoria_id, incluir_baja=True))


def crear(uow: CategoriasUnitOfWork, datos: CategoriaCreate) -> CategoriaRead:
    with uow:
        _validar_padre(uow, datos.parent_id)
        if uow.categorias.existe_hermana(datos.parent_id, datos.nombre):
            raise ConflictError(
                "Ya existe una categoría con ese nombre en el mismo nivel", code="DUPLICATE_NAME", field="nombre"
            )
        categoria = uow.categorias.create(Categoria(**datos.model_dump()))
        return CategoriaRead.model_validate(categoria)


def actualizar(uow: CategoriasUnitOfWork, categoria_id: int, datos: CategoriaUpdate) -> CategoriaRead:
    cambios = datos.model_dump(exclude_unset=True)
    if "nombre" in cambios and cambios["nombre"] is None:
        raise ValidationError("El nombre no puede ser nulo", field="nombre")
    with uow:
        categoria = _obtener(uow, categoria_id)
        if "parent_id" in cambios:
            nuevo_padre = cambios["parent_id"]
            if nuevo_padre == categoria_id or (
                nuevo_padre is not None and nuevo_padre in uow.categorias.ids_descendientes(categoria_id)
            ):
                raise ValidationError(
                    "Una categoría no puede ser su propia ascendiente", code="CATEGORY_CYCLE", field="parent_id"
                )
            _validar_padre(uow, nuevo_padre)
        padre = cambios.get("parent_id", categoria.parent_id)
        nombre = cambios.get("nombre", categoria.nombre)
        if ("nombre" in cambios or "parent_id" in cambios) and uow.categorias.existe_hermana(
            padre, nombre, excluir_id=categoria_id
        ):
            raise ConflictError(
                "Ya existe una categoría con ese nombre en el mismo nivel", code="DUPLICATE_NAME", field="nombre"
            )
        uow.categorias.update(categoria, cambios)
        return CategoriaRead.model_validate(categoria)


def eliminar(uow: CategoriasUnitOfWork, categoria_id: int) -> None:
    """Baja lógica (RN-16). Falla con 409 si tiene productos o subcategorías activos."""
    with uow:
        categoria = _obtener(uow, categoria_id)
        if uow.categorias.count_subcategorias_activas(categoria_id):
            raise ConflictError("No se puede dar de baja: tiene subcategorías activas", code="CATEGORY_HAS_CHILDREN")
        if uow.categorias.count_productos_activos(categoria_id):
            raise ConflictError("No se puede dar de baja: tiene productos activos", code="CATEGORY_HAS_PRODUCTS")
        uow.categorias.soft_delete(categoria)


def reactivar(uow: CategoriasUnitOfWork, categoria_id: int) -> CategoriaRead:
    """Reactivar limpia deleted_at (sección 11.5). No se reactiva bajo un padre dado de baja."""
    with uow:
        categoria = _obtener(uow, categoria_id, incluir_baja=True)
        if categoria.deleted_at is None:
            raise ConflictError("La categoría ya está activa", code="ALREADY_ACTIVE")
        if categoria.parent_id is not None and uow.categorias.get_by_id(categoria.parent_id) is None:
            raise ConflictError("Primero hay que reactivar la categoría padre", code="PARENT_INACTIVE")
        if uow.categorias.existe_hermana(categoria.parent_id, categoria.nombre, excluir_id=categoria_id):
            raise ConflictError(
                "Ya existe una categoría activa con ese nombre en el mismo nivel", code="DUPLICATE_NAME", field="nombre"
            )
        uow.categorias.restore(categoria)
        return CategoriaRead.model_validate(categoria)
