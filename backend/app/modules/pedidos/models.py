"""Dominio 3 · Pedidos. Sin baja lógica: el ciclo de vida lo cierra la FSM con historial completo."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Numeric, Text, text
from sqlmodel import Field, SQLModel

from app.core.db_types import created_at_field, updated_at_field


class EstadoPedido(SQLModel, table=True):
    """Catálogo con clave semántica (seed). Las transiciones viven en core/fsm.py."""

    __tablename__ = "estado_pedido"

    codigo: str = Field(primary_key=True, max_length=20)
    descripcion: str = Field(max_length=120, nullable=False)
    orden: int = Field(nullable=False)
    es_terminal: bool = Field(default=False, nullable=False, sa_column_kwargs={"server_default": text("false")})


class Pedido(SQLModel, table=True):
    __tablename__ = "pedido"
    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="ck_pedido_subtotal"),
        CheckConstraint("total >= 0", name="ck_pedido_total"),
    )

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    usuario_id: int = Field(
        sa_type=BigInteger, foreign_key="usuario.id", ondelete="RESTRICT", nullable=False, index=True
    )
    estado_codigo: str = Field(
        max_length=20, foreign_key="estado_pedido.codigo", ondelete="RESTRICT", nullable=False, index=True
    )
    forma_pago_codigo: str = Field(max_length=20, foreign_key="forma_pago.codigo", ondelete="RESTRICT", nullable=False)
    # Nula = retiro en el local.
    direccion_id: int | None = Field(
        sa_type=BigInteger, default=None, foreign_key="direccion_entrega.id", ondelete="SET NULL"
    )
    # Snapshot monetario inmutable (RN-04): total = subtotal - descuento + costo_envio.
    subtotal: Decimal = Field(sa_type=Numeric(10, 2), nullable=False)
    descuento: Decimal = Field(
        default=Decimal("0.00"),
        sa_type=Numeric(10, 2),
        nullable=False,
        sa_column_kwargs={"server_default": text("0.00")},
    )
    costo_envio: Decimal = Field(sa_type=Numeric(10, 2), nullable=False)
    total: Decimal = Field(sa_type=Numeric(10, 2), nullable=False)
    # Idempotency-Key del cliente al crear el pedido.
    external_reference: str = Field(max_length=100, nullable=False, unique=True, index=True)
    notas: str | None = Field(default=None, sa_type=Text)
    created_at: datetime = created_at_field(index=True)
    updated_at: datetime = updated_at_field()


class DetallePedido(SQLModel, table=True):
    """PK propia: un mismo producto puede repetirse con distintas exclusiones."""

    __tablename__ = "detalle_pedido"
    __table_args__ = (CheckConstraint("cantidad >= 1", name="ck_detalle_cantidad"),)

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    pedido_id: int = Field(sa_type=BigInteger, foreign_key="pedido.id", ondelete="CASCADE", nullable=False, index=True)
    producto_id: int = Field(sa_type=BigInteger, foreign_key="producto.id", ondelete="RESTRICT", nullable=False)
    # Snapshot (RN-04).
    nombre_snapshot: str = Field(max_length=200, nullable=False)
    precio_snapshot: Decimal = Field(sa_type=Numeric(10, 2), nullable=False)
    cantidad: int = Field(nullable=False)


class DetallePedidoExclusion(SQLModel, table=True):
    """Ingredientes quitados de la línea ("sin cebolla")."""

    __tablename__ = "detalle_pedido_exclusion"

    detalle_pedido_id: int = Field(
        sa_type=BigInteger, primary_key=True, foreign_key="detalle_pedido.id", ondelete="CASCADE"
    )
    ingrediente_id: int = Field(sa_type=BigInteger, primary_key=True, foreign_key="ingrediente.id", ondelete="RESTRICT")


class HistorialEstadoPedido(SQLModel, table=True):
    """Ledger append-only (RN-02, RN-03). El motivo de cancelación se guarda aquí (RN-05)."""

    __tablename__ = "historial_estado_pedido"

    id: int | None = Field(sa_type=BigInteger, default=None, primary_key=True)
    pedido_id: int = Field(sa_type=BigInteger, foreign_key="pedido.id", ondelete="CASCADE", nullable=False, index=True)
    # Nulo en el primer registro del pedido.
    estado_desde: str | None = Field(
        default=None, max_length=20, foreign_key="estado_pedido.codigo", ondelete="RESTRICT"
    )
    estado_hasta: str = Field(max_length=20, foreign_key="estado_pedido.codigo", ondelete="RESTRICT", nullable=False)
    usuario_id: int | None = Field(sa_type=BigInteger, default=None, foreign_key="usuario.id", ondelete="SET NULL")
    motivo: str | None = Field(default=None, sa_type=Text)
    created_at: datetime = created_at_field(index=True)
