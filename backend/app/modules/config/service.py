"""Lógica de la configuración operativa: local, horarios, días bloqueados, zonas y cotización de envío.

Lanza excepciones de dominio y no hace commit (lo hace el Unit of Work). La hora siempre se evalúa en la
zona horaria del local, nunca en la del servidor (sección 10.1).
"""

from collections import defaultdict
from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from app.core.db_types import utcnow
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.modules.config import horarios as reglas
from app.modules.config.models import ConfiguracionLocal, DiaBloqueado, HorarioOperativo, ZonaCobertura
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
    ZonaCotizada,
    ZonaCreate,
    ZonaRead,
    ZonaUpdate,
)
from app.modules.config.uow import ConfigUnitOfWork

CENTAVO = Decimal("0.01")


# ==============================================================================================
# Local
# ==============================================================================================


def _local(uow: ConfigUnitOfWork) -> ConfiguracionLocal:
    local = uow.local.unico()
    if local is None:
        raise NotFoundError("El local todavía no está configurado", code="LOCAL_NOT_CONFIGURED")
    return local


def obtener_local(uow: ConfigUnitOfWork) -> LocalRead:
    with uow:
        return LocalRead.model_validate(_local(uow))


def actualizar_local(uow: ConfigUnitOfWork, datos: LocalUpdate) -> LocalRead:
    with uow:
        local = uow.local.update(_local(uow), datos.model_dump())
        return LocalRead.model_validate(local)


# ==============================================================================================
# Horarios y días bloqueados
# ==============================================================================================


def obtener_horarios(uow: ConfigUnitOfWork) -> list[HorarioRead]:
    with uow:
        return [HorarioRead.model_validate(h) for h in uow.horarios.todos()]


def reemplazar_horarios(uow: ConfigUnitOfWork, datos: HorariosUpdate) -> list[HorarioRead]:
    """Reemplaza todas las franjas. Las franjas activas de un mismo día no pueden solaparse."""
    por_dia: dict[int, list[tuple[time, time]]] = defaultdict(list)
    for item in datos.items:
        if item.activo:
            por_dia[item.dia_semana].append((item.hora_apertura, item.hora_cierre))
    for dia, franjas in por_dia.items():
        franjas.sort()
        for (_, cierre), (apertura, _) in zip(franjas, franjas[1:], strict=False):
            if apertura < cierre:
                raise ValidationError(
                    f"Hay franjas que se solapan el día {dia}", code="SCHEDULE_OVERLAP", field="items"
                )
    with uow:
        uow.horarios.reemplazar([HorarioOperativo(**item.model_dump()) for item in datos.items])
        return [HorarioRead.model_validate(h) for h in uow.horarios.todos()]


def listar_dias_bloqueados(uow: ConfigUnitOfWork, desde: date | None = None) -> list[DiaBloqueadoRead]:
    with uow:
        return [DiaBloqueadoRead.model_validate(d) for d in uow.bloqueos.todos(desde=desde)]


def crear_dia_bloqueado(uow: ConfigUnitOfWork, datos: DiaBloqueadoCreate) -> DiaBloqueadoRead:
    with uow:
        # El día calendario se guarda como medianoche UTC.
        fecha = datetime.combine(datos.fecha, time.min, tzinfo=UTC)
        if datos.todo_el_dia and any(d.todo_el_dia and d.fecha == fecha for d in uow.bloqueos.todos(desde=datos.fecha)):
            raise ConflictError("Ese día ya está bloqueado", code="DAY_ALREADY_BLOCKED", field="fecha")
        dia = uow.bloqueos.create(
            DiaBloqueado(
                fecha=fecha,
                motivo=datos.motivo,
                todo_el_dia=datos.todo_el_dia,
                hora_desde=datos.hora_desde,
                hora_hasta=datos.hora_hasta,
            )
        )
        return DiaBloqueadoRead.model_validate(dia)


def eliminar_dia_bloqueado(uow: ConfigUnitOfWork, dia_id: int) -> None:
    """Sin baja lógica: el cierre simplemente deja de existir."""
    with uow:
        dia = uow.bloqueos.get_by_id(dia_id)
        if dia is None:
            raise NotFoundError("Día bloqueado no encontrado", code="BLOCKED_DAY_NOT_FOUND")
        uow.bloqueos.hard_delete(dia)


def _reglas_de_apertura(uow: ConfigUnitOfWork) -> tuple[list[reglas.Franja], list[reglas.Bloqueo]]:
    franjas = [reglas.Franja(h.dia_semana, h.hora_apertura, h.hora_cierre) for h in uow.horarios.todos() if h.activo]
    bloqueos = [
        reglas.Bloqueo(d.fecha.astimezone(UTC).date(), d.todo_el_dia, d.hora_desde, d.hora_hasta)
        for d in uow.bloqueos.todos()
    ]
    return franjas, bloqueos


def estado_local(uow: ConfigUnitOfWork, ahora: datetime | None = None) -> EstadoLocal:
    """¿Está abierto ahora y cuándo abre? `ahora` solo se inyecta en las pruebas."""
    with uow:
        local = _local(uow)
        zona = ZoneInfo(local.zona_horaria)
        momento = (ahora or utcnow()).astimezone(zona)
        franjas, bloqueos = _reglas_de_apertura(uow)
        abierto = reglas.esta_abierto(momento, franjas, bloqueos)
        proxima = None if abierto else reglas.proxima_apertura(momento, franjas, bloqueos)
        return EstadoLocal(abierto=abierto, proxima_apertura=proxima, zona_horaria=local.zona_horaria)


def exigir_local_abierto(uow: ConfigUnitOfWork, ahora: datetime | None = None) -> None:
    """RN-13: solo se crean pedidos con el local abierto. 409 con la próxima apertura."""
    estado = estado_local(uow, ahora)
    if not estado.abierto:
        cuando = estado.proxima_apertura.strftime("%d/%m/%Y %H:%M") if estado.proxima_apertura else "sin fecha definida"
        raise ConflictError(f"El local está cerrado. Próxima apertura: {cuando}", code="LOCAL_CLOSED")


# ==============================================================================================
# Zonas de cobertura
# ==============================================================================================


def _zona(uow: ConfigUnitOfWork, zona_id: int) -> ZonaCobertura:
    zona = uow.zonas.get_by_id(zona_id)
    if zona is None:
        raise NotFoundError("Zona de cobertura no encontrada", code="ZONE_NOT_FOUND")
    return zona


def _nombre_libre(uow: ConfigUnitOfWork, nombre: str, *, excluir_id: int | None = None) -> None:
    existente = uow.zonas.get_by_nombre(nombre)
    if existente is not None and existente.id != excluir_id:
        raise ConflictError(f"Ya existe una zona activa llamada «{nombre}»", code="ZONE_NAME_TAKEN", field="nombre")


def listar_zonas(uow: ConfigUnitOfWork, activo: bool | None) -> list[ZonaRead]:
    with uow:
        return [ZonaRead.model_validate(z) for z in uow.zonas.search(activo=activo)]


def obtener_zona(uow: ConfigUnitOfWork, zona_id: int) -> ZonaRead:
    with uow:
        return ZonaRead.model_validate(_zona(uow, zona_id))


def crear_zona(uow: ConfigUnitOfWork, datos: ZonaCreate) -> ZonaRead:
    with uow:
        _nombre_libre(uow, datos.nombre)
        zona = uow.zonas.create(ZonaCobertura(**datos.model_dump()))
        return ZonaRead.model_validate(zona)


def actualizar_zona(uow: ConfigUnitOfWork, zona_id: int, datos: ZonaUpdate) -> ZonaRead:
    """Cambia solo lo enviado. `activo: true` reactiva una zona dada de baja."""
    with uow:
        zona = _zona(uow, zona_id)
        cambios = datos.model_dump(exclude_unset=True)
        if "nombre" in cambios and cambios["nombre"] is None:
            raise ValidationError("El nombre no puede ser nulo", field="nombre")
        quedara_activa = cambios.get("activo", zona.activo)
        nombre = cambios.get("nombre", zona.nombre)
        if quedara_activa:
            _nombre_libre(uow, nombre, excluir_id=zona.id)
        for campo in ("poligono", "tarifa_base", "tarifa_por_km", "pedido_minimo", "activo"):
            if campo in cambios and cambios[campo] is None:
                raise ValidationError(f"{campo} no puede ser nulo", field=campo)
        return ZonaRead.model_validate(uow.zonas.update(zona, cambios))


def desactivar_zona(uow: ConfigUnitOfWork, zona_id: int) -> None:
    """DELETE: la zona se anula con `activo = false` (el ERD no tiene deleted_at en esta tabla)."""
    with uow:
        uow.zonas.update(_zona(uow, zona_id), {"activo": False})


# ==============================================================================================
# Cotización de envío (RN-14)
# ==============================================================================================


def cotizar(uow: ConfigUnitOfWork, datos: CotizacionRequest) -> CotizacionRead:
    """Zona que contiene el punto, distancia desde el local y costo = tarifa_base + km × tarifa_por_km."""
    with uow:
        local = _local(uow)
        if local.lat_origen is None or local.lng_origen is None:
            raise ConflictError("El local no tiene punto de origen configurado", code="ORIGIN_NOT_SET")
        punto = (datos.lat, datos.lng)
        zona = uow.cobertura.zona_que_contiene(punto)
        if zona is None:
            return CotizacionRead(dentro_de_cobertura=False)
        distancia = round(uow.cobertura.distancia_km((local.lat_origen, local.lng_origen), punto), 2)
        costo = (zona.tarifa_base + Decimal(str(distancia)) * zona.tarifa_por_km).quantize(CENTAVO, ROUND_HALF_UP)
        return CotizacionRead(
            dentro_de_cobertura=True,
            zona=ZonaCotizada(id=zona.id, nombre=zona.nombre, pedido_minimo=zona.pedido_minimo),  # type: ignore[arg-type]
            distancia_km=distancia,
            costo_envio=costo,
            cumple_minimo=datos.subtotal >= zona.pedido_minimo,
        )
