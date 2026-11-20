from sqlmodel import select

from app.core.repository import BaseRepository
from app.modules.pagos.models import Pago


class PagoRepository(BaseRepository[Pago]):
    model = Pago

    def get_by_pedido(self, pedido_id: int) -> Pago | None:
        """Un solo registro de Pago por pedido (los reintentos lo actualizan)."""
        return self.session.exec(select(Pago).where(Pago.pedido_id == pedido_id)).first()

    def get_by_idempotency_key(self, clave: str) -> Pago | None:
        return self.session.exec(select(Pago).where(Pago.idempotency_key == clave)).first()

    def get_by_external_reference(self, referencia: str) -> Pago | None:
        return self.session.exec(select(Pago).where(Pago.external_reference == referencia)).first()
