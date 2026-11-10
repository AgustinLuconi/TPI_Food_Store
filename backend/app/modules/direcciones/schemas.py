from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Coordenadas(BaseModel):
    """lat y lng van juntas: sin coordenadas no se puede cotizar el envío (sección 10.2)."""

    @model_validator(mode="after")
    def lat_y_lng_juntas(self) -> Self:
        lat, lng = getattr(self, "lat", None), getattr(self, "lng", None)
        if (lat is None) != (lng is None):
            raise ValueError("lat y lng deben informarse juntas")
        return self


class DireccionCreate(_Coordenadas):
    alias: str | None = Field(default=None, max_length=50)
    linea1: str = Field(min_length=1)
    linea2: str | None = None
    ciudad: str | None = Field(default=None, max_length=100)
    provincia: str | None = Field(default=None, max_length=100)
    codigo_postal: str | None = Field(default=None, max_length=20)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    es_principal: bool = False


class DireccionUpdate(BaseModel):
    """Edición parcial: solo se modifican los campos enviados."""

    alias: str | None = Field(default=None, max_length=50)
    linea1: str | None = Field(default=None, min_length=1)
    linea2: str | None = None
    ciudad: str | None = Field(default=None, max_length=100)
    provincia: str | None = Field(default=None, max_length=100)
    codigo_postal: str | None = Field(default=None, max_length=20)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    es_principal: bool | None = None


class DireccionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    alias: str | None
    linea1: str
    linea2: str | None
    ciudad: str | None
    provincia: str | None
    codigo_postal: str | None
    lat: float | None
    lng: float | None
    es_principal: bool
    created_at: datetime
