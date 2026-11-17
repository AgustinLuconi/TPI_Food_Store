"""Geometría plana de la cobertura: punto en polígono (ray casting) y distancia Haversine.

Funciones puras, sin acceso a datos. Un punto es (lat, lng) y un polígono es una lista de puntos.
"""

import math
from collections.abc import Sequence

Punto = tuple[float, float]

RADIO_TIERRA_KM = 6371.0088


def punto_en_poligono(punto: Punto, poligono: Sequence[Sequence[float]]) -> bool:
    """Ray casting: se traza un rayo hacia el este desde el punto y se cuentan los lados que cruza.
    Cantidad impar de cruces = adentro. Los puntos sobre el borde cuentan como adentro."""
    lat, lng = punto
    n = len(poligono)
    if n < 3:
        return False
    adentro = False
    for i in range(n):
        lat1, lng1 = poligono[i]
        lat2, lng2 = poligono[(i + 1) % n]
        if _sobre_el_lado(lat, lng, lat1, lng1, lat2, lng2):
            return True
        if (lat1 > lat) != (lat2 > lat):  # el lado atraviesa la latitud del punto
            lng_cruce = lng1 + (lat - lat1) / (lat2 - lat1) * (lng2 - lng1)
            if lng < lng_cruce:
                adentro = not adentro
    return adentro


def _sobre_el_lado(lat: float, lng: float, lat1: float, lng1: float, lat2: float, lng2: float) -> bool:
    cruz = (lat - lat1) * (lng2 - lng1) - (lng - lng1) * (lat2 - lat1)
    if abs(cruz) > 1e-12:
        return False
    return min(lat1, lat2) <= lat <= max(lat1, lat2) and min(lng1, lng2) <= lng <= max(lng1, lng2)


def distancia_haversine_km(a: Punto, b: Punto) -> float:
    """Distancia sobre la esfera entre dos puntos (lat, lng) en grados."""
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(h))
