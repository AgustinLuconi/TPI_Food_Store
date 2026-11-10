"""Datos iniciales obligatorios (sección 12.2). Sin ellos la aplicación no funciona.

    python -m app.db.seed

Es IDEMPOTENTE: busca cada registro por su código/clave natural antes de insertarlo, nunca por id.
"""

from datetime import time

from sqlmodel import Session, select

from app.core.security import hash_password
from app.core.uow import UnitOfWork
from app.db import base  # noqa: F401  (registra todos los modelos)
from app.modules.config.models import ConfiguracionLocal, HorarioOperativo, ZonaCobertura
from app.modules.pagos.models import FormaPago
from app.modules.pedidos.models import EstadoPedido
from app.modules.usuarios.models import Rol, Usuario, UsuarioRol

ROLES = [
    ("ADMIN", "Administrador", "Acceso total"),
    ("STOCK", "Gestor de stock", "Inventario y producción"),
    ("PEDIDOS", "Gestor de pedidos", "Estados CONFIRMADO → ENTREGADO"),
    ("CLIENT", "Cliente", "Solo sus propios datos"),
]

# (codigo, descripcion, orden, es_terminal) — sección 9.1
ESTADOS_PEDIDO = [
    ("PENDIENTE", "Pedido creado, pago pendiente", 1, False),
    ("CONFIRMADO", "Pago registrado", 2, False),
    ("EN_PREPARACION", "En cocina", 3, False),
    ("EN_CAMINO", "Despachado o listo para retirar", 4, False),
    ("ENTREGADO", "Entrega confirmada", 5, True),
    ("CANCELADO", "Pedido cancelado", 6, True),
]

# MERCADOPAGO queda deshabilitada hasta implementar el Anexo B.
FORMAS_PAGO = [
    ("EFECTIVO", "Efectivo", True),
    ("TRANSFERENCIA", "Transferencia", True),
    ("MERCADOPAGO", "MercadoPago", False),
]

ADMIN_EMAIL = "admin@foodstore.com"
ADMIN_PASSWORD = "FoodStore2026!"  # debe cambiarse en producción

LOCAL = {
    "nombre": "Food Store",
    "zona_horaria": "America/Argentina/Buenos_Aires",
    "direccion_origen": "Av. Corrientes 1000, Buenos Aires",
    "lat_origen": -34.6037,
    "lng_origen": -58.3816,
}

ZONA = {
    "nombre": "Zona Centro",
    # Polígono (lat, lng) ~ 6 km alrededor del local; ray casting en el Service de cobertura.
    "poligono": [[-34.58, -58.42], [-34.58, -58.35], [-34.63, -58.35], [-34.63, -58.42]],
    "tarifa_base": 500,
    "tarifa_por_km": 150,
    "pedido_minimo": 3000,
}


def _seed_catalogos(session: Session) -> None:
    for codigo, nombre, descripcion in ROLES:
        if session.get(Rol, codigo) is None:
            session.add(Rol(codigo=codigo, nombre=nombre, descripcion=descripcion))
    for codigo, descripcion, orden, terminal in ESTADOS_PEDIDO:
        if session.get(EstadoPedido, codigo) is None:
            session.add(EstadoPedido(codigo=codigo, descripcion=descripcion, orden=orden, es_terminal=terminal))
    for codigo, nombre, habilitado in FORMAS_PAGO:
        if session.get(FormaPago, codigo) is None:
            session.add(FormaPago(codigo=codigo, nombre=nombre, habilitado=habilitado))
    session.flush()


def _seed_admin(session: Session) -> None:
    admin = session.exec(select(Usuario).where(Usuario.email == ADMIN_EMAIL)).first()
    if admin is None:
        admin = Usuario(
            nombre="Admin",
            apellido="Food Store",
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
        )
        session.add(admin)
        session.flush()
    if session.get(UsuarioRol, (admin.id, "ADMIN")) is None:
        session.add(UsuarioRol(usuario_id=admin.id, rol_codigo="ADMIN"))
    session.flush()


def _seed_configuracion(session: Session) -> None:
    # ConfiguracionLocal es un registro único: solo se crea si no existe ninguno.
    if session.exec(select(ConfiguracionLocal)).first() is None:
        session.add(ConfiguracionLocal(**LOCAL))
    # Todos los días de 11:00 a 23:00 (franjas editables desde el panel).
    if session.exec(select(HorarioOperativo)).first() is None:
        for dia in range(7):
            session.add(HorarioOperativo(dia_semana=dia, hora_apertura=time(11, 0), hora_cierre=time(23, 0)))
    if session.exec(select(ZonaCobertura).where(ZonaCobertura.nombre == ZONA["nombre"])).first() is None:
        session.add(ZonaCobertura(**ZONA))
    session.flush()


def seed(uow: UnitOfWork | None = None) -> None:
    uow = uow or UnitOfWork()
    with uow:  # commit al salir; rollback ante cualquier error
        _seed_catalogos(uow.session)
        _seed_admin(uow.session)
        _seed_configuracion(uow.session)


if __name__ == "__main__":
    seed()
    print("Seed aplicado.")
