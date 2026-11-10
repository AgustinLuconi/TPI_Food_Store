"""Criterios de cierre de la Fase 1: la base impone las restricciones del ERD."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError
from app.core.fsm import ORDEN_TRANSICIONES, PEDIDO_TRANSICIONES, validar_transicion
from app.core.repository import AppendOnlyRepository, BaseRepository
from app.modules.direcciones.models import DireccionEntrega
from app.modules.usuarios.models import Usuario


def _insertar_producto(s) -> int:
    return s.exec(text("insert into producto (nombre, precio_base) values ('P', 10) returning id")).one()[0]  # type: ignore[call-overload]


def _violacion(session_factory, sql: str, restriccion: str, **params) -> None:
    with session_factory() as s:
        with pytest.raises(IntegrityError) as exc:
            s.exec(text(sql), params=params)  # type: ignore[call-overload]
        assert restriccion in str(exc.value), str(exc.value)
        s.rollback()


# --- Exclusive arcs -------------------------------------------------------------------------


def test_movimiento_stock_rechaza_pedido_y_orden_a_la_vez(session_factory):
    with session_factory() as s:
        pid = _insertar_producto(s)
        s.commit()
    _violacion(
        session_factory,
        "insert into movimiento_stock (producto_id, pedido_id, orden_produccion_id, tipo_movimiento, cantidad) "
        "values (:p, 1, 1, 'ENTRADA', 1)",
        "ck_mov_stock_origen_xor",
        p=pid,
    )


def test_movimiento_stock_acepta_origen_manual(session_factory):
    """Ambos nulos = movimiento manual (compra, ajuste, merma): num_nonnulls(...) <= 1."""
    with session_factory() as s:
        pid = _insertar_producto(s)
        s.exec(
            text(  # type: ignore[call-overload]
                "insert into movimiento_stock (producto_id, tipo_movimiento, cantidad, motivo) "
                "values (:p, 'ENTRADA', 5, 'compra')"
            ),
            params={"p": pid},
        )
        assert (
            s.exec(text("select count(*) from movimiento_stock where producto_id = :p"), params={"p": pid}).one()[0]
            == 1
        )  # type: ignore[call-overload]
        s.rollback()


def test_orden_produccion_exige_exactamente_una_salida(session_factory):
    with session_factory() as s:
        pid = _insertar_producto(s)
        s.commit()
    _violacion(session_factory, "insert into orden_produccion (cantidad_a_producir) values (1)", "ck_orden_salida_xor")
    _violacion(
        session_factory,
        "insert into orden_produccion (producto_id, ingrediente_id, cantidad_a_producir) values (:p, 1, 1)",
        "ck_orden_salida_xor",
        p=pid,
    )


# --- CHECK, UQ e índices --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sql", "restriccion"),
    [
        ("insert into producto (nombre, precio_base) values ('X', -1)", "ck_producto_precio_base"),
        ("insert into producto (nombre, precio_base, stock_minimo) values ('X', 1, -1)", "ck_producto_stock_minimo"),
        (
            "insert into horario_operativo (dia_semana, hora_apertura, hora_cierre) values (7, '10:00', '20:00')",
            "ck_horario_dia_semana",
        ),
        ("insert into receta_ingrediente values (1, 1, 1, 'UN')", "ck_receta_padre_distinto_componente"),
        (
            "insert into movimiento_ingrediente (ingrediente_id, tipo_movimiento, cantidad) values (1, 'ENTRADA', 0)",
            "ck_mov_ingrediente_cantidad",
        ),
    ],
)
def test_check_constraints_del_erd(session_factory, sql, restriccion):
    _violacion(session_factory, sql, restriccion)


def test_el_enum_de_movimientos_rechaza_tipos_desconocidos(session_factory):
    with session_factory() as s:
        pid = _insertar_producto(s)
        s.commit()
    with session_factory() as s:
        with pytest.raises(Exception) as exc:  # noqa: PT011
            s.exec(
                text("insert into movimiento_stock (producto_id, tipo_movimiento, cantidad) values (:p, 'ROBO', 1)"),
                params={"p": pid},
            )  # type: ignore[call-overload]
        assert "tipomovimientoenum" in str(exc.value)
        s.rollback()


def test_indice_unico_parcial_rn17_una_principal_activa_por_usuario(session_factory):
    with session_factory() as s:
        admin_id = s.exec(text("select id from usuario where email = 'admin@foodstore.com'")).one()[0]  # type: ignore[call-overload]
        s.add(DireccionEntrega(usuario_id=admin_id, linea1="A", es_principal=True))
        s.flush()
        s.add(DireccionEntrega(usuario_id=admin_id, linea1="B", es_principal=True))
        with pytest.raises(IntegrityError) as exc:
            s.flush()
        assert "uq_direccion_principal_activa" in str(exc.value)
        s.rollback()


def test_el_indice_parcial_ignora_las_direcciones_dadas_de_baja(session_factory):
    with session_factory() as s:
        admin_id = s.exec(text("select id from usuario where email = 'admin@foodstore.com'")).one()[0]  # type: ignore[call-overload]
        s.add(DireccionEntrega(usuario_id=admin_id, linea1="A", es_principal=True, deleted_at=text("now()")))  # type: ignore[arg-type]
        s.add(DireccionEntrega(usuario_id=admin_id, linea1="B", es_principal=True))
        s.flush()  # no viola: la primera está dada de baja
        s.rollback()


def test_email_unico(session_factory):
    _violacion(
        session_factory,
        "insert into usuario (nombre, apellido, email, password_hash) values ('a', 'b', 'admin@foodstore.com', 'x')",
        "ix_usuario_email",
    )


def test_los_28_indices_ix_del_erd_existen_en_la_base(session_factory):
    with session_factory() as s:
        n = s.exec(
            text("select count(*) from pg_indexes where schemaname = 'public' and indexname like 'ix\\_%'")
        ).one()[0]  # type: ignore[call-overload]
        assert n == 28
        assert (
            s.exec(text("select count(*) from pg_indexes where indexname = 'uq_direccion_principal_activa'")).one()[0]
            == 1
        )  # type: ignore[call-overload]


# --- Seed -----------------------------------------------------------------------------------


def test_el_seed_cargo_los_datos_obligatorios(session_factory):
    with session_factory() as s:

        def uno(sql):
            return s.exec(text(sql)).all()  # type: ignore[call-overload]

        assert {r[0] for r in uno("select codigo from rol")} == {"ADMIN", "STOCK", "PEDIDOS", "CLIENT"}
        estados = {r[0]: (r[1], r[2]) for r in uno("select codigo, orden, es_terminal from estado_pedido")}
        assert (
            estados["PENDIENTE"] == (1, False)
            and estados["ENTREGADO"] == (5, True)
            and estados["CANCELADO"] == (6, True)
        )
        formas = {r[0]: r[1] for r in uno("select codigo, habilitado from forma_pago")}
        assert formas == {"EFECTIVO": True, "TRANSFERENCIA": True, "MERCADOPAGO": False}
        assert uno("select zona_horaria from configuracion_local") == [("America/Argentina/Buenos_Aires",)]


def test_el_seed_es_idempotente(session_factory):
    from app.core.uow import UnitOfWork
    from app.db.seed import seed

    seed(UnitOfWork(session_factory))
    seed(UnitOfWork(session_factory))
    with session_factory() as s:
        assert s.exec(text("select count(*) from usuario where email = 'admin@foodstore.com'")).one()[0] == 1  # type: ignore[call-overload]
        assert s.exec(text("select count(*) from rol")).one()[0] == 4  # type: ignore[call-overload]
        assert s.exec(text("select count(*) from configuracion_local")).one()[0] == 1  # type: ignore[call-overload]
        assert s.exec(text("select count(*) from horario_operativo")).one()[0] == 7  # type: ignore[call-overload]


# --- Máquina de estados y repositorios ------------------------------------------------------


def test_los_estados_terminales_no_tienen_salidas():
    for terminal in ("ENTREGADO", "CANCELADO"):
        with pytest.raises(ConflictError) as exc:
            validar_transicion(PEDIDO_TRANSICIONES, terminal, "PENDIENTE", {"ADMIN"})
        assert exc.value.code == "TERMINAL_STATE"  # RN-01 → 409


def test_transiciones_del_pedido_y_roles():
    validar_transicion(PEDIDO_TRANSICIONES, "PENDIENTE", "CONFIRMADO")
    validar_transicion(PEDIDO_TRANSICIONES, "EN_CAMINO", "ENTREGADO")
    validar_transicion(PEDIDO_TRANSICIONES, "EN_PREPARACION", "CANCELADO", {"PEDIDOS"})
    with pytest.raises(ConflictError):
        validar_transicion(PEDIDO_TRANSICIONES, "PENDIENTE", "ENTREGADO")  # no se saltea estados
    with pytest.raises(Exception) as exc:  # noqa: PT011
        validar_transicion(PEDIDO_TRANSICIONES, "EN_PREPARACION", "CANCELADO", {"CLIENT"})
    assert exc.value.status_code == 403  # type: ignore[attr-defined]


def test_transiciones_de_la_orden_de_produccion():
    validar_transicion(ORDEN_TRANSICIONES, "PLANIFICADA", "EN_PROCESO")
    validar_transicion(ORDEN_TRANSICIONES, "EN_PROCESO", "CANCELADA")
    with pytest.raises(ConflictError):
        validar_transicion(ORDEN_TRANSICIONES, "PLANIFICADA", "COMPLETADA")


def test_el_repositorio_append_only_no_permite_modificar_ni_borrar():
    for metodo in ("update", "soft_delete", "hard_delete", "restore"):
        assert not hasattr(AppendOnlyRepository, metodo), metodo
    assert hasattr(AppendOnlyRepository, "create")


def test_baja_logica_y_borrado_fisico_segun_la_entidad(session_factory):
    with session_factory() as s:
        repo = BaseRepository[Usuario](s)
        repo.model = Usuario
        admin = repo.list(page=1, size=1)[0][0]
        with pytest.raises(TypeError):
            repo.hard_delete(admin)  # RN-16: las maestras solo admiten baja lógica
        s.rollback()
