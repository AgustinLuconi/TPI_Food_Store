"""Fechas de las métricas: siempre en la zona horaria del LOCAL, nunca en la del servidor (sección 10.1).

Funciones puras, fáciles de probar.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

MAX_DIAS_RANGO = 366


def limites_del_dia(dia: date, zona: ZoneInfo) -> tuple[datetime, datetime]:
    """[inicio, fin) del día calendario de `dia` en la zona del local, como instantes con zona."""
    inicio = datetime.combine(dia, time.min, tzinfo=zona)
    return inicio, datetime.combine(dia + timedelta(days=1), time.min, tzinfo=zona)


def hoy_local(ahora: datetime, zona: ZoneInfo) -> date:
    return ahora.astimezone(zona).date()


def limites_del_rango(desde: date, hasta: date, zona: ZoneInfo) -> tuple[datetime, datetime]:
    """[inicio de `desde`, fin de `hasta`) en la zona del local (`hasta` es inclusivo como día)."""
    return limites_del_dia(desde, zona)[0], limites_del_dia(hasta, zona)[1]


def dias_entre(desde: date, hasta: date) -> list[date]:
    """Todos los días del rango, inclusive: la serie de ventas no debe saltear los días sin ventas."""
    return [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]
