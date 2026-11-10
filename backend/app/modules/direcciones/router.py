from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.deps import CurrentUser, get_current_user
from app.modules.direcciones import service
from app.modules.direcciones.deps import get_direcciones_uow
from app.modules.direcciones.schemas import DireccionCreate, DireccionRead, DireccionUpdate
from app.modules.direcciones.uow import DireccionesUnitOfWork

router = APIRouter(prefix="/direcciones", tags=["direcciones"])

Owner = Annotated[CurrentUser, Depends(get_current_user)]
Uow = Annotated[DireccionesUnitOfWork, Depends(get_direcciones_uow)]


@router.get("", response_model=list[DireccionRead])
def listar_direcciones(user: Owner, uow: Uow):
    return service.listar(uow, user.id)


@router.post("", status_code=201, response_model=DireccionRead)
def crear_direccion(body: DireccionCreate, user: Owner, uow: Uow):
    return service.crear(uow, user.id, body)


@router.put("/{direccion_id}", response_model=DireccionRead)
def actualizar_direccion(direccion_id: int, body: DireccionUpdate, user: Owner, uow: Uow):
    return service.actualizar(uow, user.id, direccion_id, body)


@router.delete("/{direccion_id}", status_code=204)
def eliminar_direccion(direccion_id: int, user: Owner, uow: Uow):
    service.eliminar(uow, user.id, direccion_id)
    return Response(status_code=204)


@router.patch("/{direccion_id}/principal", response_model=DireccionRead)
def marcar_principal(direccion_id: int, user: Owner, uow: Uow):
    return service.marcar_principal(uow, user.id, direccion_id)
