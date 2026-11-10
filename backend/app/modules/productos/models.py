"""Dominio 2 · Catálogo e inventario.

Producto, Ingrediente, recetas (BOM), Lote y los dos ledgers append-only. El stock NO se almacena:
`stock_real` y `stock_disponible` se derivan por agregación sobre los ledgers (sección 8).
`Producto.stock_cantidad` es solo una caché de lectura (RN-06).
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Column, Numeric, Text, text
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlmodel import Field, SQLModel

from app.core.db_types import (
    created_at_field,
    deleted_at_field,
    timestamptz_field,
    updated_at_field,
)


class TipoMovimiento(enum.StrEnum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    RESERVA = "RESERVA"
    LIBERACION_RESERVA = "LIBERACION_RESERVA"
    MERMA = "MERMA"
    AJUSTE_POSITIVO = "AJUSTE_POSITIVO"
    AJUSTE_NEGATIVO = "AJUSTE_NEGATIVO"


TIPO_MOVIMIENTO_PG_NAME = "tipomovimientoenum"


def _tipo_movimiento_column(*, create_type: bool) -> Column:  # type: ignore[type-arg]
    """Ambos ledgers comparten el mismo tipo ENUM de PostgreSQL: el segundo modelo usa
    create_type=False para no intentar crearlo dos veces."""
    return Column(
        PGEnum(TipoMovimiento, name=TIPO_MOVIMIENTO_PG_NAME, create_type=create_type),
        nullable=False,
    )


class Producto(SQLModel, table=True):
    __tablename__ = "producto"
    __table_args__ = (
        CheckConstraint("precio_base >= 0", name="ck_producto_precio_base"),
        CheckConstraint("stock_minimo >= 0", name="ck_producto_stock_minimo"),
        CheckConstraint("stock_cantidad >= 0", name="ck_producto_stock_cantidad"),
    )

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    nombre: str = Field(max_length=200, nullable=False, index=True)
    descripcion: str | None = Field(default=None, sa_type=Text)
    imagen_url: str | None = Field(default=None, max_length=500)
    precio_base: Decimal = Field(sa_type=Numeric(10, 2), nullable=False)
    # Visibilidad comercial: independiente del stock.
    disponible: bool = Field(default=True, nullable=False, sa_column_kwargs={"server_default": text("true")})
    stock_minimo: int = Field(default=0, nullable=False, sa_column_kwargs={"server_default": text("0")})
    # Caché de solo lectura de stock_real; nunca fuente de verdad.
    stock_cantidad: int | None = Field(default=0, sa_column_kwargs={"server_default": text("0")})
    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()
    deleted_at: datetime | None = deleted_at_field()


class ProductoCategoria(SQLModel, table=True):
    __tablename__ = "producto_categoria"

    producto_id: int = Field(sa_type=BigInteger, primary_key=True, foreign_key="producto.id", ondelete="CASCADE")
    cat_id: int = Field(sa_type=BigInteger, primary_key=True, foreign_key="categoria.id", ondelete="CASCADE")
    es_principal: bool = Field(default=False, nullable=False, sa_column_kwargs={"server_default": text("false")})


class Ingrediente(SQLModel, table=True):
    __tablename__ = "ingrediente"
    __table_args__ = (CheckConstraint("stock_minimo >= 0", name="ck_ingrediente_stock_minimo"),)

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    # Sigue siendo único después de la baja lógica.
    nombre: str = Field(max_length=100, nullable=False, unique=True, index=True)
    es_alergeno: bool = Field(default=False, nullable=False, sa_column_kwargs={"server_default": text("false")})
    # Sub-ensamble con receta propia (RecetaIngrediente) y OrdenProduccion previa.
    es_elaborado: bool = Field(default=False, nullable=False, sa_column_kwargs={"server_default": text("false")})
    stock_minimo: int = Field(default=0, nullable=False, sa_column_kwargs={"server_default": text("0")})
    deleted_at: datetime | None = deleted_at_field()


class ProductoIngrediente(SQLModel, table=True):
    """Receta de venta (BOM a nivel producto)."""

    __tablename__ = "producto_ingrediente"
    __table_args__ = (CheckConstraint("cantidad_requerida > 0", name="ck_prod_ing_cantidad"),)

    producto_id: int = Field(sa_type=BigInteger, primary_key=True, foreign_key="producto.id", ondelete="CASCADE")
    ingrediente_id: int = Field(sa_type=BigInteger, primary_key=True, foreign_key="ingrediente.id", ondelete="RESTRICT")
    cantidad_requerida: Decimal = Field(
        default=Decimal("1"), sa_type=Numeric(10, 3), nullable=False, sa_column_kwargs={"server_default": text("1")}
    )
    unidad_medida: str = Field(default="UN", max_length=10, nullable=False, sa_column_kwargs={"server_default": "UN"})
    es_removible: bool = Field(default=True, nullable=False, sa_column_kwargs={"server_default": text("true")})


class RecetaIngrediente(SQLModel, table=True):
    """Receta de un ingrediente elaborado (BOM a nivel insumo). La ausencia de ciclos se valida en el Service."""

    __tablename__ = "receta_ingrediente"
    __table_args__ = (
        CheckConstraint("cantidad_requerida > 0", name="ck_receta_cantidad"),
        CheckConstraint("ingrediente_padre_id <> componente_id", name="ck_receta_padre_distinto_componente"),
    )

    ingrediente_padre_id: int = Field(
        sa_type=BigInteger, primary_key=True, foreign_key="ingrediente.id", ondelete="CASCADE"
    )
    componente_id: int = Field(sa_type=BigInteger, primary_key=True, foreign_key="ingrediente.id", ondelete="RESTRICT")
    cantidad_requerida: Decimal = Field(sa_type=Numeric(10, 3), nullable=False)
    unidad_medida: str = Field(default="UN", max_length=10, nullable=False, sa_column_kwargs={"server_default": "UN"})


class Lote(SQLModel, table=True):
    __tablename__ = "lote"

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    producto_id: int = Field(
        sa_type=BigInteger, foreign_key="producto.id", ondelete="RESTRICT", nullable=False, index=True
    )
    codigo_lote: str = Field(max_length=50, nullable=False)
    fecha_vencimiento: datetime = timestamptz_field()
    fecha_ingreso: datetime = timestamptz_field(default_now=True)
    cantidad_inicial: Decimal = Field(sa_type=Numeric(12, 3), nullable=False)


class MovimientoStock(SQLModel, table=True):
    """Ledger append-only del PRODUCTO terminado (nunca UPDATE ni DELETE).

    Exclusive arc: pedido_id y orden_produccion_id, a lo sumo uno. Ambos nulos = movimiento manual.
    """

    __tablename__ = "movimiento_stock"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_mov_stock_cantidad"),
        CheckConstraint("num_nonnulls(pedido_id, orden_produccion_id) <= 1", name="ck_mov_stock_origen_xor"),
    )

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    producto_id: int = Field(
        sa_type=BigInteger, foreign_key="producto.id", ondelete="RESTRICT", nullable=False, index=True
    )
    lote_id: int | None = Field(sa_type=BigInteger, default=None, foreign_key="lote.id", ondelete="RESTRICT")
    pedido_id: int | None = Field(sa_type=BigInteger, default=None, foreign_key="pedido.id", ondelete="RESTRICT")
    orden_produccion_id: int | None = Field(
        sa_type=BigInteger, default=None, foreign_key="orden_produccion.id", ondelete="RESTRICT"
    )
    tipo_movimiento: TipoMovimiento = Field(sa_column=_tipo_movimiento_column(create_type=True))
    cantidad: Decimal = Field(sa_type=Numeric(12, 3), nullable=False)
    motivo: str | None = Field(default=None, max_length=120)
    fecha_registro: datetime = created_at_field(index=True)


class MovimientoIngrediente(SQLModel, table=True):
    """Ledger append-only de INSUMOS. orden_produccion_id nulo = movimiento manual."""

    __tablename__ = "movimiento_ingrediente"
    __table_args__ = (CheckConstraint("cantidad > 0", name="ck_mov_ingrediente_cantidad"),)

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    ingrediente_id: int = Field(
        sa_type=BigInteger, foreign_key="ingrediente.id", ondelete="RESTRICT", nullable=False, index=True
    )
    orden_produccion_id: int | None = Field(
        sa_type=BigInteger, default=None, foreign_key="orden_produccion.id", ondelete="RESTRICT"
    )
    tipo_movimiento: TipoMovimiento = Field(sa_column=_tipo_movimiento_column(create_type=False))
    cantidad: Decimal = Field(sa_type=Numeric(12, 3), nullable=False)
    motivo: str | None = Field(default=None, max_length=120)
    fecha_registro: datetime = created_at_field(index=True)
