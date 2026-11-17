"""HTTP puro de la configuración y la cobertura (sección 6.7): valida, verifica el rol y delega en el Service."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.core.deps import CurrentUser, require_roles
from app.modules.config import service
from app.modules.config.deps import get_config_uow
from app.modules.config.schemas import (
    CotizacionRead,
    CotizacionRequest,
    DiaBloqueadoCreate,
    DiaBloqueadoRead,
    EstadoLocal,
    HorarioRead,
    HorariosUpdate,
    LocalRead,
    LocalUpdate,
    ZonaCreate,
    ZonaRead,
    ZonaUpdate,
)
from app.modules.config.uow import ConfigUnitOfWork

config_router = APIRouter(prefix="/config", tags=["config"])
envio_router = APIRouter(prefix="/envio", tags=["envio"])

Uow = Annotated[ConfigUnitOfWork, Depends(get_config_uow)]
Admin = Annotated[CurrentUser, Depends(require_roles("ADMIN"))]
Cliente = Annotated[CurrentUser, Depends(require_roles("CLIENT"))]


@config_router.get("/estado-local", response_model=EstadoLocal)
def estado_local(uow: Uow):
    """Público: { abierto, proxima_apertura } en la zona horaria del local."""
    return service.estado_local(uow)


@config_router.get("/local", response_model=LocalRead)
def obtener_local(_: Admin, uow: Uow):
    return service.obtener_local(uow)


@config_router.put("/local", response_model=LocalRead)
def actualizar_local(body: LocalUpdate, _: Admin, uow: Uow):
    return service.actualizar_local(uow, body)


@config_router.get("/horarios", response_model=list[HorarioRead])
def obtener_horarios(uow: Uow):
    """Público: las franjas operativas."""
    return service.obtener_horarios(uow)


@config_router.put("/horarios", response_model=list[HorarioRead])
def reemplazar_horarios(body: HorariosUpdate, _: Admin, uow: Uow):
    return service.reemplazar_horarios(uow, body)


@config_router.get("/dias-bloqueados", response_model=list[DiaBloqueadoRead])
def listar_dias_bloqueados(_: Admin, uow: Uow, desde: Annotated[date | None, Query()] = None):
    return service.listar_dias_bloqueados(uow, desde)


@config_router.post("/dias-bloqueados", status_code=201, response_model=DiaBloqueadoRead)
def crear_dia_bloqueado(body: DiaBloqueadoCreate, _: Admin, uow: Uow):
    return service.crear_dia_bloqueado(uow, body)


@config_router.delete("/dias-bloqueados/{dia_id}", status_code=204)
def eliminar_dia_bloqueado(dia_id: int, _: Admin, uow: Uow):
    service.eliminar_dia_bloqueado(uow, dia_id)
    return Response(status_code=204)


@config_router.get("/zonas", response_model=list[ZonaRead])
def listar_zonas(_: Admin, uow: Uow, activo: Annotated[bool | None, Query()] = None):
    return service.listar_zonas(uow, activo)


@config_router.post("/zonas", status_code=201, response_model=ZonaRead)
def crear_zona(body: ZonaCreate, _: Admin, uow: Uow):
    return service.crear_zona(uow, body)


@config_router.get("/zonas/{zona_id}", response_model=ZonaRead)
def obtener_zona(zona_id: int, _: Admin, uow: Uow):
    return service.obtener_zona(uow, zona_id)


@config_router.put("/zonas/{zona_id}", response_model=ZonaRead)
def actualizar_zona(zona_id: int, body: ZonaUpdate, _: Admin, uow: Uow):
    return service.actualizar_zona(uow, zona_id, body)


@config_router.delete("/zonas/{zona_id}", status_code=204)
def desactivar_zona(zona_id: int, _: Admin, uow: Uow):
    """Baja: `activo = false`. Se reactiva con PUT {activo: true}."""
    service.desactivar_zona(uow, zona_id)
    return Response(status_code=204)


@envio_router.post("/cotizar", response_model=CotizacionRead)
def cotizar_envio(body: CotizacionRequest, _: Cliente, uow: Uow):
    """{ lat, lng, subtotal } → zona, distancia, costo de envío y si cumple el pedido mínimo."""
    return service.cotizar(uow, body)
