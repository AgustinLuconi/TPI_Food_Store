# Food Store

Sistema de gestión de pedidos de comida (TPI · Programación 3 y Arquitectura y Diseño de Interfaces).
**Stack:** React 19 + TypeScript + Tailwind 4 + TanStack Query + Zustand + Axios · FastAPI + SQLModel + Alembic · PostgreSQL 16.

> **Estado: Fase 1 (Cimientos) completa.** Modelo de datos, `core/`, seguridad, usuarios, direcciones,
> categorías y el frontend base con los ABM de categorías y usuarios. Las Fases 2 (negocio) y 3
> (cliente, panel, Docker, despliegue y MercadoPago) están pendientes. Ver `docs/` para el ERD.

## Requisitos

- Python 3.11 o superior (con el módulo `venv`)
- Node.js 22 y npm
- Docker (solo para la base de datos de desarrollo)

## Puesta en marcha

### 1. Base de datos

```bash
docker compose -f docker-compose.dev.yml up -d
```

PostgreSQL 16 queda en `localhost:5434` (usuario, clave y base: `foodstore`). Se usa el puerto 5434
para no chocar con un PostgreSQL local en el 5432; se cambia con `DB_HOST_PORT`.

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                 # completar SECRET_KEY (mínimo 32 caracteres, ver el archivo)
alembic upgrade head                 # crea el esquema
python -m app.db.seed                # carga los datos iniciales (idempotente)
uvicorn app.main:app --reload
```

- API: <http://localhost:8000/api/v1> · Documentación interactiva: <http://localhost:8000/docs> (y `/redoc`).
- Usuario inicial: **`admin@foodstore.com`** / **`FoodStore2026!`** (rol ADMIN; cambiarla en producción).

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

`VITE_API_URL` (ver `frontend/.env.example`) apunta por defecto a `http://localhost:8000/api/v1`.

## Tests y verificaciones

```bash
# Backend: crea sola la base de prueba `foodstore_test`, aplica las migraciones y siembra los datos.
cd backend
pytest                               # 68 tests
pytest --cov=app                     # cobertura (96 % en esta fase)
ruff check . && ruff format --check .
alembic check                        # modelos y migraciones no divergen

# Frontend
cd frontend
npm run lint && npm run build && npm test
```

Los tests del backend corren cada caso dentro de una transacción que se revierte, contra PostgreSQL
real, con el Unit of Work inyectado mediante `dependency_overrides`.

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

**Frontend** (`frontend/src/`): Feature-Sliced Design. Una feature no importa de otra (lo hace cumplir
ESLint); lo transversal vive en `shared/` y `store/`. Zustand guarda el estado del cliente (sesión,
carrito, checkout, UI) y TanStack Query el del servidor.

## Decisiones y adiciones respecto de la especificación

Cosas que la especificación no definía o que se resolvieron de forma propia. Conviene revisarlas.

| Tema | Decisión |
| --- | --- |
| Hash de contraseñas | `bcrypt` directo, sin Passlib (sin mantenimiento y con problemas con bcrypt ≥ 4.1). |
| `POST /usuarios` (agregado) | El patrón ABM y CE-12 piden "Agregar" para usuarios, pero la spec no define el endpoint. Solo ADMIN; aplica la política de contraseña y la auditoría de roles. |
| `PATCH …/reactivar` (agregado) | En usuarios y categorías. La sección 11.5 exige "reactivar limpia `deleted_at`" y no hay ruta para hacerlo. |
| `GET /categorias/lista` (agregado) | Listado plano, paginado y filtrable para el ABM. `GET /categorias` sigue devolviendo el árbol público. |
| Filtro `estado` | Las pantallas de maestros necesitan Activos / Inactivos / Todos; `incluir_inactivos=true` se mantiene y equivale a `todos`. |
| Protección del último admin | No se puede bloquear, dar de baja ni quitar el rol ADMIN al único administrador activo, ni a uno mismo. |
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
despliegue en la nube, MercadoPago, capturas y video de demostración.
