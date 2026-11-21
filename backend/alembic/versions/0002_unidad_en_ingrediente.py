"""unidad de medida en el ingrediente (RN-10)

La unidad deja de deducirse de la primera receta: pasa a guardarse en el ingrediente. Las bases existentes
reciben la unidad que sus recetas ya usaban (o UN si el ingrediente no está en ninguna).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-21 17:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ingrediente",
        sa.Column("unidad_medida", sa.String(length=10), server_default="UN", nullable=False),
    )
    # Hasta ahora la primera receta fijaba la unidad: se conserva la que ya estaba en uso.
    op.execute(
        """
        UPDATE ingrediente AS i
        SET unidad_medida = COALESCE(
            (SELECT pi.unidad_medida FROM producto_ingrediente pi WHERE pi.ingrediente_id = i.id LIMIT 1),
            (SELECT ri.unidad_medida FROM receta_ingrediente ri WHERE ri.componente_id = i.id LIMIT 1),
            'UN'
        )
        """
    )


def downgrade() -> None:
    op.drop_column("ingrediente", "unidad_medida")
