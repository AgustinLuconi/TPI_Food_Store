"""Registro de modelos: importar este módulo deja todas las tablas en SQLModel.metadata.

Lo usan Alembic (autogenerate), el seed y los tests.
"""

from sqlmodel import SQLModel

from app.modules.auth.models import RefreshToken  # noqa: F401
from app.modules.categorias.models import Categoria  # noqa: F401
from app.modules.config.models import ConfiguracionLocal, DiaBloqueado, HorarioOperativo, ZonaCobertura  # noqa: F401
from app.modules.direcciones.models import DireccionEntrega  # noqa: F401
from app.modules.pagos.models import FormaPago, Pago  # noqa: F401
from app.modules.pedidos.models import (  # noqa: F401
    DetallePedido,
    DetallePedidoExclusion,
    EstadoPedido,
    HistorialEstadoPedido,
    Pedido,
)
from app.modules.produccion.models import OrdenProduccion  # noqa: F401
from app.modules.productos.models import (  # noqa: F401
    Ingrediente,
    Lote,
    MovimientoIngrediente,
    MovimientoStock,
    Producto,
    ProductoCategoria,
    ProductoIngrediente,
    RecetaIngrediente,
)
from app.modules.usuarios.models import Rol, Usuario, UsuarioRol  # noqa: F401

metadata = SQLModel.metadata
