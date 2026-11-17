from collections.abc import Sequence

from sqlalchemy import func
from sqlalchemy.orm import aliased
from sqlmodel import select

from app.core.repository import BaseRepository, Sentido, ordenar
from app.core.schemas import Estado
from app.modules.categorias.models import Categoria
from app.modules.categorias.schemas import OrdenCategorias
from app.modules.productos.models import Producto, ProductoCategoria

# Columnas por las que la grilla puede ordenar (sección 11.5: orden en el servidor).
_Padre = aliased(Categoria)
# Nombre del padre como subconsulta correlacionada: ordena sin agregar un JOIN al listado.
_NOMBRE_DEL_PADRE = select(_Padre.nombre).where(_Padre.id == Categoria.parent_id).scalar_subquery()
_COLUMNAS_DE_ORDEN = {"nombre": (Categoria.nombre,), "padre": (_NOMBRE_DEL_PADRE, Categoria.nombre)}


class CategoriaRepository(BaseRepository[Categoria]):
    model = Categoria

    def arbol_activo(self) -> Sequence[Categoria]:
        """Categorías activas alcanzables desde la raíz por una cadena de padres activos (CTE recursiva).
        Una subcategoría activa bajo un padre dado de baja no aparece."""
        raiz = (
            select(Categoria.id)
            .where(Categoria.parent_id.is_(None), Categoria.deleted_at.is_(None))  # type: ignore[attr-defined]
            .cte("arbol", recursive=True)
        )
        hijas = (
            select(Categoria.id)
            .join(raiz, Categoria.parent_id == raiz.c.id)  # type: ignore[arg-type]
            .where(Categoria.deleted_at.is_(None))  # type: ignore[attr-defined]
        )
        arbol = raiz.union_all(hijas)
        stmt = select(Categoria).where(Categoria.id.in_(select(arbol.c.id))).order_by(Categoria.nombre)  # type: ignore[attr-defined]
        return self.session.exec(stmt).all()

    def ids_descendientes(self, categoria_id: int) -> set[int]:
        """Todos los descendientes (activos o no): sirve para evitar ciclos al cambiar el padre."""
        hijas = select(Categoria.id).where(Categoria.parent_id == categoria_id).cte("desc", recursive=True)
        siguientes = select(Categoria.id).join(hijas, Categoria.parent_id == hijas.c.id)  # type: ignore[arg-type]
        cte = hijas.union_all(siguientes)
        return set(self.session.exec(select(cte.c.id)).all())

    def nombres_por_id(self, ids: set[int]) -> dict[int, str]:
        """Nombres de varias categorías (incluso dadas de baja) en una sola consulta."""
        if not ids:
            return {}
        stmt = select(Categoria.id, Categoria.nombre).where(Categoria.id.in_(ids))  # type: ignore[attr-defined]
        return {cid: nombre for cid, nombre in self.session.exec(stmt).all()}

    def count_subcategorias_activas(self, categoria_id: int) -> int:
        return self.count(Categoria.parent_id == categoria_id)

    def count_productos_activos(self, categoria_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(ProductoCategoria)
            .join(Producto, Producto.id == ProductoCategoria.producto_id)  # type: ignore[arg-type]
            .where(ProductoCategoria.cat_id == categoria_id, Producto.deleted_at.is_(None))  # type: ignore[attr-defined]
        )
        return self.session.exec(stmt).one()

    def existe_hermana(self, parent_id: int | None, nombre: str, *, excluir_id: int | None = None) -> bool:
        """¿Hay otra categoría ACTIVA con ese nombre bajo el mismo padre?"""
        filtros = [
            func.lower(Categoria.nombre) == nombre.lower(),
            Categoria.parent_id.is_(None) if parent_id is None else Categoria.parent_id == parent_id,
        ]
        if excluir_id is not None:
            filtros.append(Categoria.id != excluir_id)
        return self.count(*filtros) > 0

    def search(
        self,
        *,
        search: str | None,
        estado: Estado,
        parent_id: int | None,
        solo_raices: bool,
        orden: OrdenCategorias,
        sentido: Sentido,
        page: int,
        size: int,
    ) -> tuple[Sequence[Categoria], int]:
        filtros = []
        if search:
            filtros.append(Categoria.nombre.ilike(f"%{search.strip()}%"))  # type: ignore[attr-defined]
        if solo_raices:
            filtros.append(Categoria.parent_id.is_(None))  # type: ignore[union-attr]
        elif parent_id is not None:
            filtros.append(Categoria.parent_id == parent_id)
        if estado == "activos":
            filtros.append(Categoria.deleted_at.is_(None))  # type: ignore[attr-defined]
        elif estado == "inactivos":
            filtros.append(Categoria.deleted_at.is_not(None))  # type: ignore[attr-defined]
        return self.list(
            *filtros,
            page=page,
            size=size,
            order_by=ordenar(_COLUMNAS_DE_ORDEN[orden], sentido),
            include_deleted=True,
        )
