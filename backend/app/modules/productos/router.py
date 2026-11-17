"""HTTP puro del catálogo: valida con schemas, verifica el rol y delega en el Service."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile

from app.core import media
from app.core.deps import CurrentUser, get_optional_user, require_roles
from app.core.errors import ValidationError
from app.core.schemas import Paginated
from app.modules.productos import service
from app.modules.productos.deps import get_productos_uow
from app.modules.productos.schemas import (
    DisponibilidadUpdate,
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

productos_router = APIRouter(prefix="/productos", tags=["productos"])
ingredientes_router = APIRouter(prefix="/ingredientes", tags=["ingredientes"])

Uow = Annotated[ProductosUnitOfWork, Depends(get_productos_uow)]
Opcional = Annotated[CurrentUser | None, Depends(get_optional_user)]
Admin = Annotated[CurrentUser, Depends(require_roles("ADMIN"))]
AdminOStock = Annotated[CurrentUser, Depends(require_roles("ADMIN", "STOCK"))]


# ----------------------------------------------------------------------------------------------
# Productos
# ----------------------------------------------------------------------------------------------


@productos_router.get("", response_model=Paginated[ProductoItem])
def listar_productos(uow: Uow, usuario: Opcional, filtros: Annotated[FiltrosProductos, Query()]):
    """Público. Filtros search, categoria_id (con subcategorías), disponible y estado; los dados de baja
    (`estado`, `incluir_inactivos`) solo los ven ADMIN y STOCK. Orden por `nombre` o `precio`."""
    return service.listar_productos(uow, filtros, usuario)


@productos_router.post("", status_code=201, response_model=ProductoRead)
def crear_producto(body: ProductoCreate, _: Admin, uow: Uow):
    return service.crear_producto(uow, body)


@productos_router.get("/{producto_id}", response_model=ProductoRead)
def obtener_producto(producto_id: int, uow: Uow, usuario: Opcional):
    """Público: detalle con categorías, receta y alérgenos."""
    return service.obtener_producto(uow, producto_id, usuario)


@productos_router.put("/{producto_id}", response_model=ProductoRead)
def actualizar_producto(producto_id: int, body: ProductoUpdate, _: Admin, uow: Uow):
    return service.actualizar_producto(uow, producto_id, body)


@productos_router.delete("/{producto_id}", status_code=204)
def eliminar_producto(producto_id: int, _: Admin, uow: Uow):
    """Baja lógica: asigna deleted_at y disponible = false."""
    service.eliminar_producto(uow, producto_id)
    return Response(status_code=204)


@productos_router.patch("/{producto_id}/reactivar", response_model=ProductoRead)
def reactivar_producto(producto_id: int, _: Admin, uow: Uow):
    return service.reactivar_producto(uow, producto_id)


@productos_router.patch("/{producto_id}/disponibilidad", response_model=ProductoRead)
def cambiar_disponibilidad(producto_id: int, body: DisponibilidadUpdate, _: AdminOStock, uow: Uow):
    """Cambia la visibilidad comercial (independiente del stock)."""
    return service.cambiar_disponibilidad(uow, producto_id, body.disponible)


@productos_router.post("/{producto_id}/imagen", response_model=ProductoRead)
async def subir_imagen(producto_id: int, _: Admin, uow: Uow, archivo: Annotated[UploadFile, File()]):
    """Valida el tipo real (JPEG, PNG o WEBP) y el tamaño (≤ 2 MB), renombra con UUID y guarda solo la URL."""
    contenido = await archivo.read(media.MAX_BYTES + 1)  # un byte de más basta para detectar el exceso
    if len(contenido) > media.MAX_BYTES:
        raise ValidationError("La imagen supera el máximo de 2 MB", code="FILE_TOO_LARGE", field="archivo")
    return service.subir_imagen(uow, producto_id, contenido)


@productos_router.get("/{producto_id}/ingredientes", response_model=list[IngredienteDelProducto])
def obtener_receta_producto(producto_id: int, uow: Uow, usuario: Opcional):
    """Receta de venta (pública)."""
    return service.obtener_receta_producto(uow, producto_id, usuario)


@productos_router.put("/{producto_id}/ingredientes", response_model=list[IngredienteDelProducto])
def reemplazar_receta_producto(producto_id: int, body: RecetaProductoUpdate, _: Admin, uow: Uow):
    """Reemplaza la receta de venta completa (RN-10: una unidad por ingrediente)."""
    return service.reemplazar_receta_producto(uow, producto_id, body)


# ----------------------------------------------------------------------------------------------
# Ingredientes
# ----------------------------------------------------------------------------------------------


@ingredientes_router.get("", response_model=Paginated[IngredienteRead])
def listar_ingredientes(_: AdminOStock, uow: Uow, filtros: Annotated[FiltrosIngredientes, Query()]):
    return service.listar_ingredientes(uow, filtros)


@ingredientes_router.post("", status_code=201, response_model=IngredienteRead)
def crear_ingrediente(body: IngredienteCreate, _: Admin, uow: Uow):
    return service.crear_ingrediente(uow, body)


@ingredientes_router.get("/{ingrediente_id}", response_model=IngredienteRead)
def obtener_ingrediente(ingrediente_id: int, _: AdminOStock, uow: Uow):
    return service.obtener_ingrediente(uow, ingrediente_id)


@ingredientes_router.put("/{ingrediente_id}", response_model=IngredienteRead)
def actualizar_ingrediente(ingrediente_id: int, body: IngredienteUpdate, _: Admin, uow: Uow):
    return service.actualizar_ingrediente(uow, ingrediente_id, body)


@ingredientes_router.delete("/{ingrediente_id}", status_code=204)
def eliminar_ingrediente(ingrediente_id: int, _: Admin, uow: Uow):
    service.eliminar_ingrediente(uow, ingrediente_id)
    return Response(status_code=204)


@ingredientes_router.patch("/{ingrediente_id}/reactivar", response_model=IngredienteRead)
def reactivar_ingrediente(ingrediente_id: int, _: Admin, uow: Uow):
    return service.reactivar_ingrediente(uow, ingrediente_id)


@ingredientes_router.get("/{ingrediente_id}/receta", response_model=list[RecetaIngredienteRead])
def obtener_receta_ingrediente(ingrediente_id: int, _: Admin, uow: Uow):
    return service.obtener_receta_ingrediente(uow, ingrediente_id)


@ingredientes_router.put("/{ingrediente_id}/receta", response_model=list[RecetaIngredienteRead])
def reemplazar_receta_ingrediente(ingrediente_id: int, body: RecetaIngredienteUpdate, _: Admin, uow: Uow):
    """Reemplaza la receta de un ingrediente elaborado (RN-11: sin ciclos; RN-10: una unidad por ingrediente)."""
    return service.reemplazar_receta_ingrediente(uow, ingrediente_id, body)
