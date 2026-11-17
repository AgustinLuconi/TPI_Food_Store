from sqlmodel import Session

from app.modules.config.uow import ConfigUnitOfWork
from app.modules.direcciones.repository import DireccionRepository
from app.modules.inventario.uow import InventarioUnitOfWork
from app.modules.pagos.repository import PagoRepository
from app.modules.pedidos.repository import (
    DetalleRepository,
    FormaPagoRepository,
    HistorialRepository,
    PedidoRepository,
)
from app.modules.productos.repository import RecetaRepository
from app.modules.usuarios.repository import UsuarioRepository


class PedidosUnitOfWork(InventarioUnitOfWork, ConfigUnitOfWork):
    """Crear un pedido toca todo en UNA transacción: horario y cobertura (config), stock y lotes (inventario),
    líneas, historial y pago. Por eso este UoW reúne los repositorios de esos módulos."""

    pedidos: PedidoRepository
    detalles: DetalleRepository
    historial: HistorialRepository
    formas_pago: FormaPagoRepository
    pagos: PagoRepository
    direcciones: DireccionRepository
    usuarios: UsuarioRepository
    recetas: RecetaRepository

    def _init_repositories(self, session: Session) -> None:
        super()._init_repositories(session)
        self.pedidos = PedidoRepository(session)
        self.detalles = DetalleRepository(session)
        self.historial = HistorialRepository(session)
        self.formas_pago = FormaPagoRepository(session)
        self.pagos = PagoRepository(session)
        self.direcciones = DireccionRepository(session)
        self.usuarios = UsuarioRepository(session)
        self.recetas = RecetaRepository(session)
