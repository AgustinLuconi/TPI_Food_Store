"""Acceso a datos del catálogo: productos, ingredientes y recetas. Sin lógica de negocio."""

from collections.abc import Sequence

from sqlalchemy import delete, func
from sqlalchemy import select as sa_select
from sqlmodel import select

from app.core.repository import BaseRepository, Sentido, ordenar
from app.core.schemas import Estado
from app.modules.categorias.models import Categoria
from app.modules.productos.models import (
    Ingrediente,
    Producto,
    ProductoCategoria,
    ProductoIngrediente,
    RecetaIngrediente,
)
from app.modules.productos.schemas import OrdenIngredientes, OrdenProductos

_ORDEN_PRODUCTOS = {"nombre": (Producto.nombre,), "precio": (Producto.precio_base, Producto.nombre)}
_ORDEN_INGREDIENTES = {"nombre": (Ingrediente.nombre,)}


def _filtro_estado(modelo, estado: Estado) -> list:
    if estado == "activos":
        return [modelo.deleted_at.is_(None)]
    if estado == "inactivos":
        return [modelo.deleted_at.is_not(None)]
    return []


class ProductoRepository(BaseRepository[Producto]):
    model = Producto

    def search(
        self,
        *,
        search: str | None,
        categoria_ids: set[int] | None,
        disponible: bool | None,
        estado: Estado,
        orden: OrdenProductos,
        sentido: Sentido,
        page: int,
        size: int,
    ) -> tuple[Sequence[Producto], int]:
        filtros = _filtro_estado(Producto, estado)
        if search:
            filtros.append(Producto.nombre.ilike(f"%{search.strip()}%"))  # type: ignore[attr-defined]
        if categoria_ids is not None:
            filtros.append(
                Producto.id.in_(  # type: ignore[attr-defined]
                    select(ProductoCategoria.producto_id).where(ProductoCategoria.cat_id.in_(categoria_ids))  # type: ignore[attr-defined]
                )
            )
        if disponible is not None:
            filtros.append(Producto.disponible.is_(disponible))  # type: ignore[attr-defined]
        return self.list(
            *filtros,
            page=page,
            size=size,
            order_by=ordenar(_ORDEN_PRODUCTOS[orden], sentido),
            include_deleted=True,
        )

    def categorias_de(self, producto_ids: Sequence[int]) -> dict[int, list[tuple[int, str, bool]]]:
        """(id, nombre, es_principal) de las categorías de varios productos en una sola consulta."""
        resultado: dict[int, list[tuple[int, str, bool]]] = {pid: [] for pid in producto_ids}
        if not producto_ids:
            return resultado
        stmt = (
            select(ProductoCategoria.producto_id, Categoria.id, Categoria.nombre, ProductoCategoria.es_principal)
            .join(Categoria, Categoria.id == ProductoCategoria.cat_id)  # type: ignore[arg-type]
            .where(ProductoCategoria.producto_id.in_(producto_ids))  # type: ignore[attr-defined]
            .order_by(ProductoCategoria.es_principal.desc(), Categoria.nombre)  # type: ignore[attr-defined]
        )
        for pid, cid, nombre, principal in self.session.exec(stmt).all():
            resultado[pid].append((cid, nombre, principal))
        return resultado

    def reemplazar_categorias(self, producto_id: int, categoria_ids: Sequence[int], principal_id: int | None) -> None:
        self.session.exec(delete(ProductoCategoria).where(ProductoCategoria.producto_id == producto_id))  # type: ignore[call-overload]
        for cid in dict.fromkeys(categoria_ids):
            self.session.add(ProductoCategoria(producto_id=producto_id, cat_id=cid, es_principal=(cid == principal_id)))
        self.session.flush()


class IngredienteRepository(BaseRepository[Ingrediente]):
    model = Ingrediente

    def get_by_nombre(self, nombre: str) -> Ingrediente | None:
        """Incluye los dados de baja: el nombre sigue siendo único después de la baja lógica."""
        return self.session.exec(select(Ingrediente).where(func.lower(Ingrediente.nombre) == nombre.lower())).first()

    def get_activos(self, ids: Sequence[int]) -> dict[int, Ingrediente]:
        if not ids:
            return {}
        stmt = select(Ingrediente).where(Ingrediente.id.in_(ids), Ingrediente.deleted_at.is_(None))  # type: ignore[attr-defined]
        return {i.id: i for i in self.session.exec(stmt).all()}  # type: ignore[misc]

    def search(
        self,
        *,
        search: str | None,
        es_alergeno: bool | None,
        es_elaborado: bool | None,
        estado: Estado,
        orden: OrdenIngredientes,
        sentido: Sentido,
        page: int,
        size: int,
    ) -> tuple[Sequence[Ingrediente], int]:
        filtros = _filtro_estado(Ingrediente, estado)
        if search:
            filtros.append(Ingrediente.nombre.ilike(f"%{search.strip()}%"))  # type: ignore[attr-defined]
        if es_alergeno is not None:
            filtros.append(Ingrediente.es_alergeno.is_(es_alergeno))  # type: ignore[attr-defined]
        if es_elaborado is not None:
            filtros.append(Ingrediente.es_elaborado.is_(es_elaborado))  # type: ignore[attr-defined]
        return self.list(
            *filtros,
            page=page,
            size=size,
            order_by=ordenar(_ORDEN_INGREDIENTES[orden], sentido),
            include_deleted=True,
        )

    def count_productos_activos_que_lo_usan(self, ingrediente_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(ProductoIngrediente)
            .join(Producto, Producto.id == ProductoIngrediente.producto_id)  # type: ignore[arg-type]
            .where(ProductoIngrediente.ingrediente_id == ingrediente_id, Producto.deleted_at.is_(None))  # type: ignore[attr-defined]
        )
        return self.session.exec(stmt).one()

    def count_elaborados_activos_que_lo_usan(self, ingrediente_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(RecetaIngrediente)
            .join(Ingrediente, Ingrediente.id == RecetaIngrediente.ingrediente_padre_id)  # type: ignore[arg-type]
            .where(RecetaIngrediente.componente_id == ingrediente_id, Ingrediente.deleted_at.is_(None))  # type: ignore[attr-defined]
        )
        return self.session.exec(stmt).one()

    def tiene_receta(self, ingrediente_id: int) -> bool:
        stmt = (
            sa_select(func.count())
            .select_from(RecetaIngrediente)
            .where(RecetaIngrediente.ingrediente_padre_id == ingrediente_id)
        )
        return self.session.execute(stmt).scalar_one() > 0


class RecetaRepository:
    """Recetas de venta (ProductoIngrediente) y de ingredientes elaborados (RecetaIngrediente)."""

    def __init__(self, session):
        self.session = session

    # --- receta de venta -------------------------------------------------------------------
    def de_producto(self, producto_id: int) -> list[tuple[ProductoIngrediente, Ingrediente]]:
        stmt = (
            select(ProductoIngrediente, Ingrediente)
            .join(Ingrediente, Ingrediente.id == ProductoIngrediente.ingrediente_id)  # type: ignore[arg-type]
            .where(ProductoIngrediente.producto_id == producto_id)
            .order_by(Ingrediente.nombre)
        )
        return list(self.session.exec(stmt).all())

    def reemplazar_de_producto(self, producto_id: int, filas: Sequence[ProductoIngrediente]) -> None:
        self.session.exec(delete(ProductoIngrediente).where(ProductoIngrediente.producto_id == producto_id))  # type: ignore[call-overload]
        self.session.add_all(filas)
        self.session.flush()

    # --- receta de un ingrediente elaborado ----------------------------------------------------
    def de_ingrediente(self, padre_id: int) -> list[tuple[RecetaIngrediente, Ingrediente]]:
        stmt = (
            select(RecetaIngrediente, Ingrediente)
            .join(Ingrediente, Ingrediente.id == RecetaIngrediente.componente_id)  # type: ignore[arg-type]
            .where(RecetaIngrediente.ingrediente_padre_id == padre_id)
            .order_by(Ingrediente.nombre)
        )
        return list(self.session.exec(stmt).all())

    def reemplazar_de_ingrediente(self, padre_id: int, filas: Sequence[RecetaIngrediente]) -> None:
        self.session.exec(delete(RecetaIngrediente).where(RecetaIngrediente.ingrediente_padre_id == padre_id))  # type: ignore[call-overload]
        self.session.add_all(filas)
        self.session.flush()

    def aristas(self, excluyendo_padre_id: int) -> list[tuple[int, int]]:
        """Pares (padre, componente) de todas las recetas de ingredientes, salvo las del padre indicado
        (que se están reemplazando). Alimenta la detección de ciclos."""
        stmt = select(RecetaIngrediente.ingrediente_padre_id, RecetaIngrediente.componente_id).where(
            RecetaIngrediente.ingrediente_padre_id != excluyendo_padre_id
        )
        return [(p, c) for p, c in self.session.exec(stmt).all()]

    # --- RN-10: una sola unidad por ingrediente ----------------------------------------------------
    def unidad_de(
        self, ingrediente_id: int, *, excluir_producto_id: int | None = None, excluir_padre_id: int | None = None
    ) -> str | None:
        """Unidad con la que otras recetas ya usan el ingrediente (la primera receta la fija).
        Se excluye la receta que se está reemplazando."""
        en_productos = select(ProductoIngrediente.unidad_medida).where(
            ProductoIngrediente.ingrediente_id == ingrediente_id
        )
        if excluir_producto_id is not None:
            en_productos = en_productos.where(ProductoIngrediente.producto_id != excluir_producto_id)
        unidad = self.session.exec(en_productos).first()
        if unidad:
            return unidad
        en_recetas = select(RecetaIngrediente.unidad_medida).where(RecetaIngrediente.componente_id == ingrediente_id)
        if excluir_padre_id is not None:
            en_recetas = en_recetas.where(RecetaIngrediente.ingrediente_padre_id != excluir_padre_id)
        return self.session.exec(en_recetas).first()
