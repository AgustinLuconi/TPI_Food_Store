"""la unidad vive solo en el ingrediente (RN-10)

Las recetas dejan de guardar su propia copia de la unidad: la leen del ingrediente. No se pierde información,
porque desde la migración 0002 la unidad de cada fila de receta era igual a la del ingrediente.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-22 10:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("producto_ingrediente", "unidad_medida")
    op.drop_column("receta_ingrediente", "unidad_medida")


def downgrade() -> None:
    op.add_column(
        "receta_ingrediente",
        sa.Column("unidad_medida", sa.String(length=10), server_default="UN", nullable=False),
    )
    op.add_column(
        "producto_ingrediente",
        sa.Column("unidad_medida", sa.String(length=10), server_default="UN", nullable=False),
    )
    # Se repone la copia con la unidad que tiene cada ingrediente.
    op.execute(
        """
        UPDATE producto_ingrediente AS pi
        SET unidad_medida = i.unidad_medida
        FROM ingrediente AS i
        WHERE i.id = pi.ingrediente_id
        """
    )
    op.execute(
        """
        UPDATE receta_ingrediente AS ri
        SET unidad_medida = i.unidad_medida
        FROM ingrediente AS i
        WHERE i.id = ri.componente_id
        """
    )
