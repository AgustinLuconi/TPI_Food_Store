from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Annotated, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Latitud = Annotated[float, Field(ge=-90, le=90)]
Longitud = Annotated[float, Field(ge=-180, le=180)]
Dinero = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


def _texto(v: str | None) -> str | None:
    return v.strip() or None if v else None


# ----------------------------------------------------------------------------------------------
# Local
# ----------------------------------------------------------------------------------------------


class _LocalBase(BaseModel):
    @field_validator("zona_horaria", check_fields=False)
    @classmethod
    def _zona_valida(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError, OSError) as e:
            raise ValueError("Zona horaria inválida (ejemplo: America/Argentina/Buenos_Aires)") from e
        return v

    @model_validator(mode="after")
    def _origen_completo(self) -> Self:
        lat, lng = getattr(self, "lat_origen", None), getattr(self, "lng_origen", None)
        if (lat is None) != (lng is None):
            raise ValueError("El punto de origen necesita latitud y longitud juntas")
        return self


class LocalUpdate(_LocalBase):
    nombre: str = Field(min_length=1, max_length=120)
    zona_horaria: str = Field(min_length=1, max_length=60)
    direccion_origen: str | None = Field(default=None, max_length=300)
    lat_origen: Latitud | None = None
    lng_origen: Longitud | None = None

    @field_validator("nombre")
    @classmethod
    def _nombre(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío")
        return v

    @field_validator("direccion_origen")
    @classmethod
    def _direccion(cls, v: str | None) -> str | None:
        return _texto(v)


class LocalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nombre: str
    zona_horaria: str
    direccion_origen: str | None
    lat_origen: float | None
    lng_origen: float | None


class EstadoLocal(BaseModel):
    abierto: bool
    proxima_apertura: datetime | None  # en la zona horaria del local; None si ya está abierto
    zona_horaria: str


# ----------------------------------------------------------------------------------------------
# Horarios
# ----------------------------------------------------------------------------------------------


class HorarioItem(BaseModel):
    dia_semana: int = Field(ge=0, le=6, description="0 = lunes ... 6 = domingo")
    hora_apertura: time
    hora_cierre: time
    activo: bool = True

    @model_validator(mode="after")
    def _orden(self) -> Self:
        if self.hora_cierre <= self.hora_apertura:
            raise ValueError("La hora de cierre debe ser posterior a la de apertura (la franja no cruza la medianoche)")
        return self


class HorariosUpdate(BaseModel):
    """Reemplaza todas las franjas. Se admiten varias por día, sin solaparse."""

    items: list[HorarioItem] = Field(max_length=70)


class HorarioRead(HorarioItem):
    model_config = ConfigDict(from_attributes=True)

    id: int


# ----------------------------------------------------------------------------------------------
# Días bloqueados
# ----------------------------------------------------------------------------------------------


class DiaBloqueadoCreate(BaseModel):
    fecha: date
    motivo: str | None = Field(default=None, max_length=120)
    todo_el_dia: bool = True
    hora_desde: time | None = None
    hora_hasta: time | None = None

    @field_validator("motivo")
    @classmethod
    def _motivo(cls, v: str | None) -> str | None:
        return _texto(v)

    @model_validator(mode="after")
    def _horas(self) -> Self:
        if self.todo_el_dia:
            if self.hora_desde or self.hora_hasta:
                raise ValueError("Un cierre de todo el día no lleva horas")
        elif self.hora_desde is None or self.hora_hasta is None:
            raise ValueError("Un cierre parcial exige hora_desde y hora_hasta")
        elif self.hora_hasta <= self.hora_desde:
            raise ValueError("hora_hasta debe ser posterior a hora_desde")
        return self


class DiaBloqueadoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: date
    motivo: str | None
    todo_el_dia: bool
    hora_desde: time | None
    hora_hasta: time | None

    @field_validator("fecha", mode="before")
    @classmethod
    def _solo_fecha(cls, v: object) -> object:
        # Se guarda como medianoche UTC: es el día calendario, sin importar la zona del local.
        return v.astimezone(UTC).date() if isinstance(v, datetime) else v


# ----------------------------------------------------------------------------------------------
# Zonas
# ----------------------------------------------------------------------------------------------

Vertice = tuple[Latitud, Longitud]


def _poligono_valido(v: list[Vertice] | None) -> list[Vertice] | None:
    if v is None:
        return v
    if len(set(v)) < 3:
        raise ValueError("El polígono necesita al menos 3 vértices distintos [lat, lng]")
    return v


class ZonaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    poligono: list[Vertice] = Field(max_length=200)
    tarifa_base: Dinero = Decimal(0)
    tarifa_por_km: Dinero = Decimal(0)
    pedido_minimo: Dinero = Decimal(0)

    _poligono = field_validator("poligono")(_poligono_valido)

    @field_validator("nombre")
    @classmethod
    def _nombre(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío")
        return v


class ZonaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    poligono: list[Vertice] | None = Field(default=None, max_length=200)
    tarifa_base: Dinero | None = None
    tarifa_por_km: Dinero | None = None
    pedido_minimo: Dinero | None = None
    activo: bool | None = None

    _poligono = field_validator("poligono")(_poligono_valido)

    @field_validator("nombre")
    @classmethod
    def _nombre(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío")
        return v


class ZonaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    poligono: list[list[float]]
    tarifa_base: Decimal
    tarifa_por_km: Decimal
    pedido_minimo: Decimal
    activo: bool


# ----------------------------------------------------------------------------------------------
# Cotización de envío
# ----------------------------------------------------------------------------------------------


class CotizacionRequest(BaseModel):
    lat: Latitud
    lng: Longitud
    subtotal: Dinero


class ZonaCotizada(BaseModel):
    id: int
    nombre: str
    pedido_minimo: Decimal


class CotizacionRead(BaseModel):
    dentro_de_cobertura: bool
    zona: ZonaCotizada | None = None
    distancia_km: float | None = None
    costo_envio: Decimal | None = None
    cumple_minimo: bool = False
