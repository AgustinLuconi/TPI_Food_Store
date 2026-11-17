"""CE-09: el ERD (docs/food_store_erd.puml) y la base migrada son consistentes.

Se lee el .puml y se compara contra el catálogo de PostgreSQL: tablas, columnas, tipos, NOT NULL,
DEFAULT, PK, UNIQUE, FK (destino y ON DELETE) y ENUM. Los CHECK, los índices {IX} y el índice
parcial de RN-17 se prueban en test_esquema.py.

Notación del ERD para las FK: `*--` (composición) → CASCADE; `o--` (asociación) → RESTRICT,
salvo las columnas marcadas SET NULL.
"""

import re
from pathlib import Path

import pytest
from sqlalchemy import text

PUML = Path(__file__).resolve().parents[2] / "docs" / "food_store_erd.puml"

TIPOS = {
    "BIGSERIAL": "bigint",
    "BIGINT": "bigint",
    "TEXT": "text",
    "BOOLEAN": "boolean",
    "TIMESTAMPTZ": "timestamp with time zone",
    "INTEGER": "integer",
    "INT": "integer",
    "SMALLINT": "smallint",
    "DOUBLE PRECISION": "double precision",
    "TIME": "time without time zone",
    "JSONB": "jsonb",
}
# Composiciones entre dos entidades unidas por más de una FK: la etiqueta indica cuál es.
FK_DE_LA_COMPOSICION = {"posee": "usuario_id", "padre elaborado": "ingrediente_padre_id"}


def _snake(nombre: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", nombre).lower()


def _flags(texto: str) -> list[str]:
    return re.split(r"[ ,]+", texto)


def _leer_erd() -> tuple[dict, dict, dict]:
    contenido = PUML.read_text(encoding="utf-8")
    clases: dict[str, dict] = {}
    enums: dict[str, list[str]] = {}
    for kind, nombre, cuerpo in re.findall(r"^\s*(class|enum) (\w+) <<\w+>> \{(.*?)^\s*\}", contenido, re.S | re.M):
        if kind == "enum":
            enums[nombre.lower()] = [ln.strip() for ln in cuerpo.splitlines() if ln.strip()]
            continue
        columnas = {}
        for col, tipo, flags in re.findall(r"^\s*\+ (\w+)\s*:\s*(.+?)\s*(?:\{(.*)\})?\s*$", cuerpo, re.M):
            columnas[col] = {"tipo": tipo.strip(), "flags": flags}
        clases[nombre] = {"tabla": _snake(nombre), "cols": columnas}

    fks = {}
    for clase in clases.values():
        for col, d in clase["cols"].items():
            if destino := re.search(r"FK -> (\w+)\.(\w+)", d["flags"]):
                regla = "SET NULL" if "SET NULL" in d["flags"] else "RESTRICT"
                fks[(clase["tabla"], col)] = [clases[destino[1]]["tabla"], destino[2], regla]
    for todo, parte, etiqueta in re.findall(r'^(\w+) "[^"]*" \*-- "[^"]*" (\w+) : (.+?) >?$', contenido, re.M):
        t_todo, t_parte = clases[todo]["tabla"], clases[parte]["tabla"]
        candidatas = [c for (t, c), v in fks.items() if t == t_parte and v[0] == t_todo]
        if len(candidatas) > 1:
            candidatas = [FK_DE_LA_COMPOSICION[etiqueta.strip()]]
        fks[(t_parte, candidatas[0])][2] = "CASCADE"
    return clases, enums, fks


def _tipo_esperado(tipo: str, enums: dict) -> str:
    if tipo in TIPOS:
        return TIPOS[tipo]
    if tipo.lower() in enums:
        return f"enum:{tipo.lower()}"
    for patron, plantilla in (
        (r"VARCHAR\((\d+)\)", "character varying({})"),
        (r"CHAR\((\d+)\)", "character({})"),
        (r"DECIMAL\((\d+,\d+)\)", "numeric({})"),
    ):
        if m := re.fullmatch(patron, tipo):
            return plantilla.format(m[1])
    raise ValueError(f"Tipo del ERD sin mapear: {tipo}")


@pytest.fixture(scope="module")
def erd():
    if not PUML.exists():
        pytest.skip("docs/food_store_erd.puml no está disponible")
    return _leer_erd()


@pytest.fixture(scope="module")
def catalogo(engine):
    with engine.connect() as cx:
        columnas = {}
        for t, c, dt, udt, nulo, default, largo, prec, escala in cx.execute(
            text(
                """select table_name, column_name, data_type, udt_name, is_nullable, column_default,
                          character_maximum_length, numeric_precision, numeric_scale
                   from information_schema.columns where table_schema = 'public'"""
            )
        ):
            if dt in ("character varying", "character"):
                dt = f"{dt}({largo})"
            elif dt == "numeric":
                dt = f"numeric({prec},{escala})"
            elif dt == "USER-DEFINED":
                dt = f"enum:{udt}"
            columnas[(t, c)] = {"tipo": dt, "nulo": nulo == "YES", "default": default}

        indices = [
            (tabla, list(cols), unico, parcial, nombre)
            for nombre, tabla, unico, parcial, cols in cx.execute(
                text(
                    """select i.relname, t.relname, ix.indisunique, ix.indpred is not null,
                              array(select a.attname from unnest(ix.indkey) with ordinality k(n, o)
                                    join pg_attribute a on a.attrelid = t.oid and a.attnum = k.n order by k.o)
                       from pg_index ix join pg_class i on i.oid = ix.indexrelid
                       join pg_class t on t.oid = ix.indrelid
                       where t.relnamespace = 'public'::regnamespace"""
                )
            )
        ]

        fks = {
            (tabla, col): [destino, col_destino, regla]
            for tabla, col, destino, col_destino, regla in cx.execute(
                text(
                    """select c.conrelid::regclass::text, a.attname, c.confrelid::regclass::text, af.attname,
                              case c.confdeltype when 'c' then 'CASCADE' when 'n' then 'SET NULL'
                                   when 'r' then 'RESTRICT' else 'NO ACTION' end
                       from pg_constraint c
                       join pg_attribute a on a.attrelid = c.conrelid and a.attnum = c.conkey[1]
                       join pg_attribute af on af.attrelid = c.confrelid and af.attnum = c.confkey[1]
                       where c.contype = 'f' and c.connamespace = 'public'::regnamespace"""
                )
            )
        }

        enums: dict[str, list[str]] = {}
        for tipo, valor in cx.execute(
            text(
                """select t.typname, e.enumlabel from pg_type t join pg_enum e on e.enumtypid = t.oid
                   where t.typnamespace = 'public'::regnamespace order by t.typname, e.enumsortorder"""
            )
        ):
            enums.setdefault(tipo, []).append(valor)

        tablas = {r[0] for r in cx.execute(text("select tablename from pg_tables where schemaname = 'public'"))}
    tablas.discard("alembic_version")
    return {"columnas": columnas, "indices": indices, "fks": fks, "enums": enums, "tablas": tablas}


def test_las_tablas_y_columnas_son_las_del_erd(erd, catalogo):
    clases, _, _ = erd
    assert catalogo["tablas"] == {c["tabla"] for c in clases.values()}
    for clase in clases.values():
        # {derived} se calcula por agregación sobre el ledger: no es una columna.
        esperadas = {c for c, d in clase["cols"].items() if "derived" not in d["flags"]}
        reales = {c for (t, c) in catalogo["columnas"] if t == clase["tabla"]}
        assert reales == esperadas, clase["tabla"]


def test_tipos_not_null_y_defaults(erd, catalogo):
    clases, enums, _ = erd
    diferencias = []
    for clase in clases.values():
        for col, d in clase["cols"].items():
            if "derived" in d["flags"]:
                continue
            real = catalogo["columnas"][(clase["tabla"], col)]
            nombre = f"{clase['tabla']}.{col}"
            if real["tipo"] != _tipo_esperado(d["tipo"], enums):
                diferencias.append(f"{nombre}: tipo {real['tipo']}")
            not_null = "NN" in _flags(d["flags"]) or "PK" in d["flags"]
            if real["nulo"] == not_null:
                diferencias.append(f"{nombre}: nullable={real['nulo']}")
            if d["tipo"] == "BIGSERIAL" and "nextval" not in (real["default"] or ""):
                diferencias.append(f"{nombre}: no es BIGSERIAL")
            if default := re.search(r"DEFAULT ([^,}]+)", d["flags"]):
                valor = default[1].strip().strip("'").lower()
                if valor not in (real["default"] or "").lower():
                    diferencias.append(f"{nombre}: DEFAULT {real['default']!r}, el ERD dice {valor}")
    assert diferencias == []


def test_claves_primarias_y_unique(erd, catalogo):
    clases, _, _ = erd
    for clase in clases.values():
        t = clase["tabla"]
        pk = sorted(c for c, d in clase["cols"].items() if "PK" in d["flags"])
        pk_real = next(
            cols for tabla, cols, _, _, nombre in catalogo["indices"] if tabla == t and nombre.endswith("pkey")
        )
        assert sorted(pk_real) == pk, t
        for col, d in clase["cols"].items():
            if "UQ" in _flags(d["flags"]):
                assert any(
                    tabla == t and cols == [col] and unico and not parcial
                    for tabla, cols, unico, parcial, _ in catalogo["indices"]
                ), f"{t}.{col} no es UNIQUE"


def test_fk_con_destino_y_on_delete_del_erd(erd, catalogo):
    """CASCADE en las composiciones, SET NULL donde el ERD lo marca y RESTRICT en el resto."""
    _, _, fks_erd = erd
    assert catalogo["fks"] == fks_erd


def test_enums_compartidos(erd, catalogo):
    _, enums, _ = erd
    assert catalogo["enums"] == enums
