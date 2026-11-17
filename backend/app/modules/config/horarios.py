"""Reglas puras de apertura del local (sección 10.1). Siempre trabajan con la hora LOCAL del negocio.

Una franja va de `apertura` (inclusive) a `cierre` (exclusivo) dentro del mismo día. El día 0 es el lunes.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass(frozen=True)
class Franja:
    dia_semana: int
    apertura: time
    cierre: time


@dataclass(frozen=True)
class Bloqueo:
    fecha: date
    todo_el_dia: bool
    desde: time | None = None
    hasta: time | None = None

    def cubre(self, momento: datetime) -> bool:
        if momento.date() != self.fecha:
            return False
        if self.todo_el_dia:
            return True
        return self.desde is not None and self.hasta is not None and self.desde <= momento.time() < self.hasta


def esta_abierto(ahora: datetime, franjas: Sequence[Franja], bloqueos: Sequence[Bloqueo]) -> bool:
    """Abierto = la hora cae en una franja del día y la fecha no está bloqueada (total o parcialmente)."""
    hora = ahora.time()
    en_franja = any(f.dia_semana == ahora.weekday() and f.apertura <= hora < f.cierre for f in franjas)
    return en_franja and not any(b.cubre(ahora) for b in bloqueos)


def proxima_apertura(
    ahora: datetime, franjas: Sequence[Franja], bloqueos: Sequence[Bloqueo], *, dias: int = 14
) -> datetime | None:
    """Primer momento posterior a `ahora` en que el local estará abierto, o None si no hay uno en `dias` días.

    Los candidatos son las aperturas de cada franja y el fin de cada cierre parcial; vale el primero en el
    que de verdad esté abierto (una franja puede caer en un día bloqueado).
    """
    candidatos: list[datetime] = []
    for i in range(dias + 1):
        dia = ahora.date() + timedelta(days=i)
        candidatos += [
            datetime.combine(dia, f.apertura, tzinfo=ahora.tzinfo) for f in franjas if f.dia_semana == dia.weekday()
        ]
    candidatos += [
        datetime.combine(b.fecha, b.hasta, tzinfo=ahora.tzinfo)
        for b in bloqueos
        if not b.todo_el_dia and b.hasta is not None
    ]
    posibles = [c for c in candidatos if c > ahora and esta_abierto(c, franjas, bloqueos)]
    return min(posibles, default=None)
