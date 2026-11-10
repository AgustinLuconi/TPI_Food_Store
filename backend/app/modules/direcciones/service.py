"""Lógica de direcciones de entrega. Cada usuario solo accede a las suyas."""

from app.core.errors import NotFoundError, ValidationError
from app.modules.direcciones.models import DireccionEntrega
from app.modules.direcciones.schemas import DireccionCreate, DireccionRead, DireccionUpdate
from app.modules.direcciones.uow import DireccionesUnitOfWork


def _propia(uow: DireccionesUnitOfWork, usuario_id: int, direccion_id: int) -> DireccionEntrega:
    # Una dirección ajena responde 404 (no revela que existe).
    direccion = uow.direcciones.get_owned(usuario_id, direccion_id)
    if direccion is None:
        raise NotFoundError("Dirección no encontrada", code="ADDRESS_NOT_FOUND")
    return direccion


def listar(uow: DireccionesUnitOfWork, usuario_id: int) -> list[DireccionRead]:
    with uow:
        return [DireccionRead.model_validate(d) for d in uow.direcciones.list_by_usuario(usuario_id)]


def crear(uow: DireccionesUnitOfWork, usuario_id: int, datos: DireccionCreate) -> DireccionRead:
    with uow:
        # La primera dirección del usuario queda como principal.
        es_principal = datos.es_principal or uow.direcciones.count_activas(usuario_id) == 0
        if es_principal:
            uow.direcciones.unset_principal(usuario_id)
        direccion = DireccionEntrega(
            **datos.model_dump(exclude={"es_principal"}), usuario_id=usuario_id, es_principal=es_principal
        )
        uow.direcciones.create(direccion)
        return DireccionRead.model_validate(direccion)


def actualizar(uow: DireccionesUnitOfWork, usuario_id: int, direccion_id: int, datos: DireccionUpdate) -> DireccionRead:
    cambios = datos.model_dump(exclude_unset=True)
    with uow:
        direccion = _propia(uow, usuario_id, direccion_id)
        lat = cambios.get("lat", direccion.lat)
        lng = cambios.get("lng", direccion.lng)
        if (lat is None) != (lng is None):
            raise ValidationError("lat y lng deben informarse juntas", code="INVALID_COORDINATES", field="lat")
        if cambios.get("linea1", direccion.linea1) is None:
            raise ValidationError("linea1 es obligatoria", field="linea1")
        if cambios.get("es_principal"):
            uow.direcciones.unset_principal(usuario_id, except_id=direccion_id)
        uow.direcciones.update(direccion, cambios)
        return DireccionRead.model_validate(direccion)


def marcar_principal(uow: DireccionesUnitOfWork, usuario_id: int, direccion_id: int) -> DireccionRead:
    """RN-17: a lo sumo una dirección principal activa por usuario."""
    with uow:
        direccion = _propia(uow, usuario_id, direccion_id)
        uow.direcciones.unset_principal(usuario_id, except_id=direccion_id)
        uow.direcciones.update(direccion, {"es_principal": True})
        return DireccionRead.model_validate(direccion)


def eliminar(uow: DireccionesUnitOfWork, usuario_id: int, direccion_id: int) -> None:
    """Baja lógica. Los pedidos existentes conservan su snapshot (direccion_id SET NULL solo ante un borrado físico)."""
    with uow:
        direccion = _propia(uow, usuario_id, direccion_id)
        # Una dirección dada de baja no puede seguir siendo la principal.
        uow.direcciones.update(direccion, {"es_principal": False})
        uow.direcciones.soft_delete(direccion)
