"""Qué formas de pago se ofrecen en este despliegue (sin dependencias de otros módulos)."""

from app.core.config import get_settings

MERCADOPAGO = "MERCADOPAGO"


def forma_ofrecida(codigo: str) -> bool:
    """MercadoPago solo se ofrece si el servidor tiene sus credenciales; efectivo y transferencia, siempre."""
    return codigo != MERCADOPAGO or get_settings().MP_CONFIGURADO
