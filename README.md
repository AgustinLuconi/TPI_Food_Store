# Food Store

Sistema de gestión de pedidos de comida (TPI · Programación 3 y Arquitectura y Diseño de Interfaces).
**Stack:** React 19 + TypeScript + Tailwind 4 + TanStack Query + Zustand + Axios · FastAPI + SQLModel + Alembic · PostgreSQL 16.

> **Estado: Fase 1 (Cimientos) completa.** Modelo de datos, `core/`, seguridad, usuarios, direcciones,
> categorías y el frontend base con los ABM de categorías y usuarios. Las Fases 2 (negocio) y 3
> (cliente, panel, Docker, despliegue y MercadoPago) están pendientes. Ver `docs/` para el ERD.

## Requisitos

- Python 3.11 o superior, con el módulo `venv` (en Ubuntu/Debian: `sudo apt install python3-venv`)
- Node.js 22 y npm
- Docker con Compose v2 (solo para la base de datos de desarrollo)

## Puesta en marcha

Son tres piezas que corren a la vez: **base de datos**, **backend** y **frontend**. Se usa una terminal
para cada una (la base queda en segundo plano, así que alcanza con dos terminales abiertas).
Todos los comandos parten de la raíz del repositorio.

| Pieza | Puerto | Dirección |
| --- | --- | --- |
| PostgreSQL (Docker) | 5434 | `localhost:5434` |
| Backend (FastAPI) | 8000 | <http://localhost:8000/docs> |
| Frontend (Vite) | 5173 | <http://localhost:5173> |

### Primera vez (instalación)

**1. Base de datos**

```bash
docker compose -f docker-compose.dev.yml up -d --wait
```

`--wait` vuelve recién cuando PostgreSQL está listo para recibir conexiones. La base usa el puerto 5434
para no chocar con un PostgreSQL local en el 5432 (se cambia con `DB_HOST_PORT`); usuario, clave y base
son `foodstore`.

**2. Backend** (en `backend/`)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                 # Windows: copy .env.example .env
alembic upgrade head                 # crea las tablas
python -m app.db.seed                # datos iniciales (se puede repetir sin problema)
```

El `.env.example` ya viene listo para desarrollo, con una `SECRET_KEY` de prueba (es pública, no usarla
en producción: ahí generar una propia con `python -c "import secrets; print(secrets.token_urlsafe(48))"`).

**3. Frontend** (en `frontend/`)

```bash
cd ../frontend
npm install
```

`VITE_API_URL` (ver `frontend/.env.example`) apunta por defecto a `http://localhost:8000/api/v1`; no hace
falta crear un `.env` en el frontend para desarrollo.

### Cada vez que trabajás

```bash
# Terminal 1: base de datos (si reiniciaste la PC, el contenedor está apagado; los datos se conservan)
docker compose -f docker-compose.dev.yml up -d --wait

# Terminal 2: backend (siempre desde backend/, porque ahí se lee el .env)
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload

# Terminal 3: frontend
cd frontend && npm run dev
```

Abrí <http://localhost:5173> e ingresá con el usuario inicial **`admin@foodstore.com`** /
**`FoodStore2026!`** (rol ADMIN; cambiar la clave en producción).
La documentación interactiva de la API está en <http://localhost:8000/docs> (y `/redoc`).

### Si algo falla

| Síntoma | Causa y solución |
| --- | --- |
| `SECRET_KEY: String should have at least 32 characters` | `backend/.env` no existe, o tiene `SECRET_KEY` vacía o corta. Copiarlo de nuevo desde `.env.example` y correr los comandos **desde `backend/`**. |
| `connection to server ... port 5434 failed: Connection refused` | La base está apagada. Ejecutar `docker compose -f docker-compose.dev.yml up -d --wait`. |
| `Address already in use` en el 8000 o el 5173 | Otro proceso usa el puerto. Cerrarlo, o cambiar el puerto (`uvicorn ... --port 8001`, `npm run dev -- --port 5174`; en ese caso agregar el origen a `CORS_ORIGINS` y a `VITE_API_URL`). |
| El frontend carga pero el login da error de red | El backend no está corriendo, o `VITE_API_URL` no apunta a él. |
| Querés empezar de cero con la base | `docker compose -f docker-compose.dev.yml down -v` borra el volumen; después repetir `alembic upgrade head` y el seed. |

## Tests y verificaciones

```bash
# Backend (requiere la base levantada): crea sola la base de prueba `foodstore_test`, aplica las migraciones y siembra los datos.
cd backend
pytest                               # 77 tests
pytest --cov=app                     # cobertura (96 % en esta fase)
ruff check . && ruff format --check .
alembic check                        # modelos y migraciones no divergen

# Frontend
cd frontend
npm run lint && npm run build && npm test
```

Los tests del backend corren cada caso dentro de una transacción que se revierte, contra PostgreSQL
real, con el Unit of Work inyectado mediante `dependency_overrides`. `tests/test_erd.py` lee
`docs/food_store_erd.puml` y lo compara con la base migrada (columnas, tipos, NOT NULL, DEFAULT, PK,
UNIQUE, FK con su `ON DELETE` y ENUM), así el ERD y las migraciones no pueden divergir (CE-09).

## Arquitectura

**Backend** (`backend/app/`): módulos por dominio con la cadena `router → service → unit of work →
repository → model`; ninguna capa importa de una superior. Los services lanzan excepciones de dominio
(`core/errors.py`, traducidas a 404/409/422/403 con el formato `{detail, code, field}`) y **nunca hacen
`commit()`**: lo hace el Unit of Work al salir del bloque `with uow:`.

- **Seguridad:** OAuth2 Password Flow, JWT en cookie `HttpOnly` + refresh token rotativo (guardado como
  SHA-256), bcrypt con cost ≥ 12, rate limit del login (429 tras 5 fallos por IP en 15 minutos).
  El **rol se verifica contra la base en cada request**, no contra el token.
- **Modelo de datos:** 26 tablas en 4 dominios, fieles a `docs/food_store_erd.puml` (verificado campo por
  campo: tipos, nulabilidad, FK, UNIQUE e índices), con exclusive arcs, baja lógica e ENUM compartido.
  Las FK siguen la notación del ERD: `ON DELETE CASCADE` en las composiciones (`*--`), `SET NULL` en
  `Pedido.direccion_id` y `RESTRICT` en el resto.
- **Listados:** paginados y ordenados en la base; el orden siempre termina en la clave primaria para que
  la paginación no repita ni omita filas cuando hay valores empatados.

**Frontend** (`frontend/src/`): Feature-Sliced Design. Una feature no importa de otra (lo hace cumplir
ESLint); lo transversal vive en `shared/` y `store/`. Zustand guarda el estado del cliente (sesión,
carrito, checkout, UI) y TanStack Query el del servidor.

## Decisiones y adiciones respecto de la especificación

Cosas que la especificación no definía o que se resolvieron de forma propia. Conviene revisarlas.

| Tema | Decisión |
| --- | --- |
| Hash de contraseñas | `bcrypt` directo, sin Passlib (sin mantenimiento; verificado: falla con bcrypt 5.x y solo funciona fijando bcrypt 4.0.1). |
| `POST /usuarios` (agregado) | El patrón ABM y CE-12 piden "Agregar" para usuarios, pero la spec no define el endpoint. Solo ADMIN; aplica la política de contraseña y la auditoría de roles. |
| `PATCH …/reactivar` (agregado) | En usuarios y categorías. La sección 11.5 exige "reactivar limpia `deleted_at`" y no hay ruta para hacerlo. |
| `GET /categorias/lista` (agregado) | Listado plano, paginado y filtrable para el ABM. `GET /categorias` sigue devolviendo el árbol público. |
| Filtro `estado` | Las pantallas de maestros necesitan Activos / Inactivos / Todos; `incluir_inactivos=true` se mantiene y equivale a `todos`. |
| `orden` y `sentido` (agregados) | La sección 11.5 pide "orden en el servidor". `GET /usuarios` ordena por `nombre` o `email` y `GET /categorias/lista`, por `nombre` o `padre`; `sentido` = `asc` o `desc`. |
| `parent_id` y `raiz` (agregados) | Combo de agrupación de la sección 11.5 en categorías: `parent_id` lista las subcategorías directas y `raiz=true`, solo las raíces. |
| Protección del último admin | No se puede bloquear, dar de baja ni quitar el rol ADMIN al único administrador activo. Tampoco se puede bloquear ni dar de baja la propia cuenta. |
| Email tras la baja | Sigue siendo único: registrar o recrear un usuario dado de baja responde 409. |
| Consultas al profesor | Mientras no haya respuesta se aplican las propuestas del plan de trabajo (zonas con `activo`, unidad de medida fijada por la primera receta, lotes antes que stock sin lote, pagos por estado dentro de `/admin/metrics/resumen`). |

## Estructura

```
backend/    API FastAPI (app/core, app/modules/*, app/db, alembic, tests)
frontend/   SPA React (src/shared, src/features, src/store, src/routes, src/pages)
docs/       food_store_erd.puml y food_store_erd.svg
docker-compose.dev.yml   base de datos de desarrollo
```

## Pendiente (Fases 2 y 3)

Catálogo con recetas e imágenes, inventario con doble ledger y FEFO, órdenes de producción, horarios y
zonas de cobertura, pedidos, pagos, métricas con recharts, carrito y checkout, Docker + Nginx,
despliegue en la nube, MercadoPago.
