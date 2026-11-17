"""Reglas puras del inventario (sin acceso a datos), fáciles de probar. Sección 8 de la spec."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.modules.productos.models import TipoMovimiento

T = TipoMovimiento

# Cada tipo aporta su cantidad (siempre positiva) con este signo. La base de datos hace la suma.
SIGNO_REAL: dict[str, int] = {
    T.ENTRADA: 1,
    T.AJUSTE_POSITIVO: 1,
    T.SALIDA: -1,
    T.MERMA: -1,
    T.AJUSTE_NEGATIVO: -1,
}
SIGNO_DISPONIBLE: dict[str, int] = {**SIGNO_REAL, T.RESERVA: -1, T.LIBERACION_RESERVA: 1}

# RN-07: solo estos cuatro se cargan a mano; SALIDA, RESERVA y LIBERACION_RESERVA las genera el sistema.
TIPOS_MANUALES = frozenset({T.ENTRADA, T.MERMA, T.AJUSTE_POSITIVO, T.AJUSTE_NEGATIVO})
# Los manuales que restan stock: no pueden tocar lo que ya está reservado.
TIPOS_QUE_RESTAN = frozenset({T.MERMA, T.AJUSTE_NEGATIVO})
# RN-08: la MERMA exige uno de estos motivos.
MOTIVOS_MERMA = ("VENCIMIENTO", "ROTURA", "CONSUMO_INTERNO", "ERROR_PRODUCCION")


@dataclass(frozen=True)
class LoteDisponible:
    id: int
    fecha_vencimiento: datetime
    disponible: Decimal


def repartir_fefo(lotes: Iterable[LoteDisponible], cantidad: Decimal) -> tuple[list[tuple[int, Decimal]], Decimal]:
    """RN-09: reparte `cantidad` entre los lotes, primero los que vencen antes (FEFO).

    Devuelve (plan, faltante): el plan es una lista de (lote_id, cantidad) —un movimiento por lote— y el
    faltante es lo que los lotes no alcanzaron a cubrir (0 si alcanzaron). Quien llama decide qué hacer
    con el faltante: tomarlo de stock sin lote o rechazar con 409.
    """
    plan: list[tuple[int, Decimal]] = []
    restante = cantidad
    for lote in sorted(lotes, key=lambda x: (x.fecha_vencimiento, x.id)):
        if restante <= 0:
            break
        toma = min(lote.disponible, restante)
        if toma > 0:
            plan.append((lote.id, toma))
            restante -= toma
    return plan, restante
