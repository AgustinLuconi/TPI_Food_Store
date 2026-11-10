from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.core.deps import CurrentUser, require_roles
from app.core.schemas import Paginated
from app.modules.categorias import service
from app.modules.categorias.deps import get_categorias_uow
from app.modules.categorias.repository import Estado
from app.modules.categorias.schemas import CategoriaCreate, CategoriaNode, CategoriaRead, CategoriaUpdate
from app.modules.categorias.uow import CategoriasUnitOfWork

router = APIRouter(prefix="/categorias", tags=["categorias"])

AdminUser = Annotated[CurrentUser, Depends(require_roles("ADMIN"))]
Uow = Annotated[CategoriasUnitOfWork, Depends(get_categorias_uow)]


@router.get("", response_model=list[CategoriaNode])
def arbol_de_categorias(uow: Uow):
    """Árbol de categorías activas. Público."""
    return service.arbol(uow)


# Declarada antes de /{categoria_id} para que "lista" no se interprete como un id.
@router.get("/lista", response_model=Paginated[CategoriaRead])
def listar_categorias(
    _: AdminUser,
    uow: Uow,
    search: str | None = None,
    estado: Estado = "activos",
    incluir_inactivos: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """Listado plano y paginado para el ABM. `estado` = activos | inactivos | todos."""
    if incluir_inactivos:
        estado = "todos"
    return service.listar(uow, search=search, estado=estado, page=page, size=size)


@router.get("/{categoria_id}", response_model=CategoriaRead)
def obtener_categoria(categoria_id: int, _: AdminUser, uow: Uow):
    return service.obtener(uow, categoria_id)


@router.post("", status_code=201, response_model=CategoriaRead)
def crear_categoria(body: CategoriaCreate, _: AdminUser, uow: Uow):
    return service.crear(uow, body)


@router.put("/{categoria_id}", response_model=CategoriaRead)
def actualizar_categoria(categoria_id: int, body: CategoriaUpdate, _: AdminUser, uow: Uow):
    return service.actualizar(uow, categoria_id, body)


@router.delete("/{categoria_id}", status_code=204)
def eliminar_categoria(categoria_id: int, _: AdminUser, uow: Uow):
    service.eliminar(uow, categoria_id)
    return Response(status_code=204)


@router.patch("/{categoria_id}/reactivar", response_model=CategoriaRead)
def reactivar_categoria(categoria_id: int, _: AdminUser, uow: Uow):
    return service.reactivar(uow, categoria_id)
