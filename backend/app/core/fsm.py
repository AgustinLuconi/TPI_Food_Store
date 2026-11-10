"""Mapas de transiciones del pedido y de la orden de producción (único lugar de verdad).

El Service consulta `validar_transicion` antes de cada cambio de estado.
Un valor `None` significa "cualquier rol autorizado por el endpoint"; un conjunto restringe los roles.
"""

from collections.abc import Mapping

from app.core.errors import ConflictError, ForbiddenError

Transiciones = Mapping[str, Mapping[str, frozenset[str] | None]]

_STAFF = frozenset({"ADMIN", "PEDIDOS"})

PEDIDO_TRANSICIONES: Transiciones = {
    "PENDIENTE": {"CONFIRMADO": None, "CANCELADO": None},
    "CONFIRMADO": {"EN_PREPARACION": None, "CANCELADO": None},
    "EN_PREPARACION": {"EN_CAMINO": None, "CANCELADO": _STAFF},
    "EN_CAMINO": {"ENTREGADO": None, "CANCELADO": _STAFF},
    "ENTREGADO": {},
    "CANCELADO": {},
}

PEDIDO_ESTADOS_TERMINALES = frozenset({"ENTREGADO", "CANCELADO"})

ORDEN_TRANSICIONES: Transiciones = {
    "PLANIFICADA": {"EN_PROCESO": None, "CANCELADA": None},
    "EN_PROCESO": {"COMPLETADA": None, "CANCELADA": None},
    "COMPLETADA": {},
    "CANCELADA": {},
}


def validar_transicion(
    mapa: Transiciones,
    desde: str,
    hasta: str,
    roles: frozenset[str] | set[str] = frozenset(),
) -> None:
    """Lanza ConflictError (409) si la transición no existe (RN-01: los terminales no tienen salidas)
    o ForbiddenError (403) si el rol no está autorizado para esa transición."""
    if desde not in mapa:
        raise ConflictError(f"Estado desconocido: {desde}", code="INVALID_STATE")
    destinos = mapa[desde]
    if hasta not in destinos:
        if not destinos:
            raise ConflictError(f"El estado {desde} es terminal y no admite transiciones", code="TERMINAL_STATE")
        raise ConflictError(f"Transición inválida: {desde} → {hasta}", code="INVALID_TRANSITION")
    permitidos = destinos[hasta]
    if permitidos is not None and not (set(roles) & permitidos):
        raise ForbiddenError(f"Su rol no puede pasar de {desde} a {hasta}")
