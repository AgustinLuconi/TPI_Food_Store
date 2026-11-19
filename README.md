# Food Store

Sistema de gestión de pedidos de comida (TPI · Programación 3 y Arquitectura y Diseño de Interfaces).
**Stack:** React 19 + TypeScript + Tailwind 4 + TanStack Query + Zustand + Axios · FastAPI + SQLModel + Alembic · PostgreSQL 16.

> **Estado: Fase 2 (Negocio) completa.** Sobre los cimientos de la Fase 1, el backend suma catálogo con
> recetas e imágenes, inventario con doble ledger y FEFO, producción, configuración del local con zonas de
> cobertura, pedidos con máquina de estados y pagos idempotentes; el frontend suma las pantallas del
> personal (productos, ingredientes, inventario, producción y configuración). La Fase 3 (tienda del
> cliente, panel de métricas, Docker, despliegue y MercadoPago) está pendiente. Ver `docs/` para el ERD.

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

### Datos de demostración (opcional)

El seed deja solo lo imprescindible (roles, estados, formas de pago, administrador, un local con horario de
11 a 23 y una zona de cobertura). Para probar el sistema a mano hay un script aparte:

```bash
cd backend && python -m app.db.demo
```

Carga categorías, ingredientes (con un sub-ensamble), productos con receta, stock con lotes (uno por
vencer en 2 días), órdenes de producción, un usuario por rol y un pedido en cada estado. Pasa por los mismos
services que la API, así que respeta todas las reglas, y se puede repetir: si ya está cargada no hace nada.
Los usuarios `cliente@`, `stock@` y `pedidos@foodstore.com` usan la misma clave que el administrador.

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
pytest                               # 216 tests
pytest --cov=app                     # cobertura (98 %)
ruff check . && ruff format --check .
alembic check                        # modelos y migraciones no divergen

# Frontend
cd frontend
npm run lint && npm run build && npm test      # 31 tests
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
- **Inventario (doble ledger):** `MovimientoStock` (productos) y `MovimientoIngrediente` (insumos) son
  append-only y el stock **nunca se guarda**: `stock_real` y `stock_disponible` se calculan sumando los
  movimientos con el signo de cada tipo (RN-06). Las salidas, reservas y mermas de un producto con lotes
  consumen primero el lote que vence antes (FEFO, RN-09), con un movimiento por lote.
- **Pedidos y producción en una sola transacción:** crear un pedido valida horario, cobertura y líneas,
  congela el snapshot de precios y reserva el stock por lote; ante cualquier error se revierte todo. Las
  filas de los productos se bloquean en orden de id antes de calcular el disponible, así dos pedidos
  simultáneos no venden el mismo stock. `PedidosUnitOfWork` y `ProduccionUnitOfWork` reúnen los
  repositorios que cada operación necesita.
- **Idempotencia:** crear un pedido y registrar un pago exigen la cabecera `Idempotency-Key` (UUID).
  Repetirla devuelve el mismo resultado (200) sin duplicar nada; dos requests simultáneos con la misma clave
  se serializan con un bloqueo asesor de PostgreSQL.
- **Concurrencia:** `tests/test_concurrencia.py` lanza hilos reales con conexiones propias (los demás tests usan una
  sola conexión y no ven carreras): pedidos simultáneos que no sobrevenden, la misma `Idempotency-Key` en paralelo,
  varios cajeros cobrando el mismo pedido y órdenes de producción que compiten por insumos. Encontró un deadlock real
  al crear pedidos, ya corregido: los productos se bloquean antes de insertar las líneas que los referencian.
- **Geografía:** el ray casting y la distancia Haversine están aislados detrás del puerto
  `CoberturaRepository`, de modo que se puedan reemplazar por PostGIS sin tocar el service ni el router.

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
| Categoría con subcategorías | Filtrar productos por "Comidas" también muestra los de sus subcategorías (las pizzas). |
| Baja de un ingrediente en uso | Responde 409 si lo usa un producto activo o un elaborado activo (igual que las categorías con productos). |
| Producto reactivado | Vuelve como **no disponible**: habilitarlo para la venta es una decisión comercial. La baja también lo deja no disponible. |
| `PATCH …/reactivar` en catálogo (agregado) | En productos e ingredientes, por la misma razón que en usuarios y categorías. |
| `orden` en productos | `GET /productos` ordena por `nombre` o `precio`. |
| RN-10 (unidad) | La primera receta que usa un ingrediente fija su unidad; usarlo en otra distinta responde 422 `UNIT_MISMATCH`. |
| Imágenes | Se valida el tipo por la firma del archivo (JPEG, PNG, WEBP), máximo 2 MB, nombre UUID; en la base solo queda la URL `/media/productos/<uuid>.ext`. En desarrollo el frontend le antepone el origen del backend. |
| `stock_cantidad` | No se materializa: el stock sale siempre de los ledgers. |
| Stock visible | `stock_real` y `stock_disponible` aparecen en el catálogo solo para ADMIN y STOCK; el público ve únicamente `disponible`. |
| Movimiento manual que resta | Una MERMA o un ajuste negativo no puede tocar lo ya reservado: se compara contra el stock disponible (409 `INSUFFICIENT_STOCK`). |
| Lotes | Una entrada con lote exige código y vencimiento juntos, no admite vencimientos pasados ni códigos repetidos del mismo producto. Los lotes vencidos no se venden y se dan de baja con una merma por vencimiento. |
| `GET /produccion/{id}` (agregado) | Detalle de una orden con los insumos que consume, para la pantalla. |
| Explosión de la receta | De un solo nivel y redondeada hacia arriba a la milésima. Los componentes se consumen según lo reservado al planificar, no según la receta de hoy. |
| Horarios | Las franjas no cruzan la medianoche, el cierre es exclusivo y las activas de un día no pueden solaparse. `estado-local` informa la próxima apertura solo cuando está cerrado. |
| Días bloqueados | Se guardan como fecha de calendario (medianoche UTC). |
| Zonas superpuestas | Si un punto cae en varias zonas activas gana la de menor id. |
| `POST /envio/cotizar` | Fuera de toda zona responde **422** `OUTSIDE_COVERAGE` (sección 10.2: sin zona no hay distancia ni costo que cotizar), igual que al crear el pedido. El pedido mínimo, en cambio, solo se informa con `cumple_minimo` (la cotización existe). La respuesta 200 conserva `dentro_de_cobertura` por el contrato de la sección 6.7, pero siempre vale `true`; el frontend lee el motivo del código de error. |
| Errores de línea del pedido | Producto no disponible, exclusión inválida y stock insuficiente responden 409; dirección, cobertura y pedido mínimo, 422. |
| Ajeno es 404 | Un pedido, un pago o una dirección de otra persona responde 404 y no revela que existe. |
| Cancelar un pedido pagado | Libera el stock pero no hay reembolso automático (fuera del alcance de la Fase 2). |
| Pagos | El monto debe coincidir con el total; se registra con la forma de pago del pedido y MercadoPago queda deshabilitada hasta el Anexo B. Un segundo pago distinto es 409. |
| Consultas al profesor | Mientras no haya respuesta se aplican las propuestas del plan de trabajo (zonas con `activo`, unidad de medida fijada por la primera receta, lotes antes que stock sin lote, pagos por estado dentro de `/admin/metrics/resumen`). |

## Estructura

```
backend/    API FastAPI (app/core, app/modules/*, app/db con seed y demo, alembic, tests)
frontend/   SPA React (src/shared, src/features, src/store, src/routes, src/pages)
docs/       food_store_erd.puml y food_store_erd.svg
docker-compose.dev.yml   base de datos de desarrollo
```

## Pendiente (Fase 3)

Tienda del cliente (catálogo público, carrito y checkout con `Idempotency-Key`, seguimiento de pedidos),
gestión de pedidos y pagos para el personal, panel de métricas con recharts, Docker + Nginx, despliegue en
la nube y MercadoPago (Anexo B).
