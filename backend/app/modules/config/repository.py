"""Acceso a datos de la configuración operativa y puerto de cobertura. Sin lógica de negocio."""

from collections.abc import Sequence
from datetime import date
from typing import Protocol

from sqlalchemy import delete, func
from sqlmodel import select

from app.core.repository import BaseRepository
from app.modules.config.geo import Punto, distancia_haversine_km, punto_en_poligono
from app.modules.config.models import ConfiguracionLocal, DiaBloqueado, HorarioOperativo, ZonaCobertura


class LocalRepository(BaseRepository[ConfiguracionLocal]):
    model = ConfiguracionLocal

    def unico(self) -> ConfiguracionLocal | None:
        """ConfiguracionLocal es un registro único."""
        return self.session.exec(select(ConfiguracionLocal).order_by(ConfiguracionLocal.id)).first()  # type: ignore[arg-type]


class HorarioRepository(BaseRepository[HorarioOperativo]):
    model = HorarioOperativo

    def todos(self) -> Sequence[HorarioOperativo]:
        stmt = select(HorarioOperativo).order_by(
            HorarioOperativo.dia_semana,  # type: ignore[arg-type]
            HorarioOperativo.hora_apertura,  # type: ignore[arg-type]
            HorarioOperativo.id,  # type: ignore[arg-type]
        )
        return self.session.exec(stmt).all()

    def reemplazar(self, filas: Sequence[HorarioOperativo]) -> None:
        self.session.exec(delete(HorarioOperativo))  # type: ignore[call-overload]
        self.session.add_all(filas)
        self.session.flush()


class DiaBloqueadoRepository(BaseRepository[DiaBloqueado]):
    model = DiaBloqueado

    def todos(self, *, desde: date | None = None) -> Sequence[DiaBloqueado]:
        stmt = select(DiaBloqueado).order_by(DiaBloqueado.fecha, DiaBloqueado.id)  # type: ignore[arg-type]
        if desde is not None:
            stmt = stmt.where(func.date(DiaBloqueado.fecha) >= desde)
        return self.session.exec(stmt).all()


class ZonaRepository(BaseRepository[ZonaCobertura]):
    model = ZonaCobertura

    def search(self, *, activo: bool | None) -> Sequence[ZonaCobertura]:
        stmt = select(ZonaCobertura).order_by(ZonaCobertura.nombre, ZonaCobertura.id)  # type: ignore[arg-type]
        if activo is not None:
            stmt = stmt.where(ZonaCobertura.activo.is_(activo))  # type: ignore[attr-defined]
        return self.session.exec(stmt).all()

    def get_by_nombre(self, nombre: str) -> ZonaCobertura | None:
        stmt = select(ZonaCobertura).where(func.lower(ZonaCobertura.nombre) == nombre.lower(), ZonaCobertura.activo)
        return self.session.exec(stmt).first()


class Cobertura(Protocol):
    """Puerto de la lógica geoespacial (sección 10.2). El Service solo conoce estos dos métodos, de modo que
    una implementación con PostGIS pueda reemplazar a la de Python sin tocar el Service ni el Router."""

    def zona_que_contiene(self, punto: Punto) -> ZonaCobertura | None: ...

    def distancia_km(self, a: Punto, b: Punto) -> float: ...


class CoberturaRepository:
    """Implementación en Python puro: ray casting sobre los polígonos de las zonas activas + Haversine."""

    def __init__(self, zonas: ZonaRepository):
        self._zonas = zonas

    def zona_que_contiene(self, punto: Punto) -> ZonaCobertura | None:
        # Si el punto cae en más de una zona (superpuestas) gana la de menor id: el resultado es estable.
        for zona in sorted(self._zonas.search(activo=True), key=lambda z: z.id or 0):
            if punto_en_poligono(punto, zona.poligono):
                return zona
        return None

    def distancia_km(self, a: Punto, b: Punto) -> float:
        return distancia_haversine_km(a, b)
