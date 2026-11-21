# Food Store

Sistema de gestión de pedidos de comida (TPI · Programación 3 y Arquitectura y Diseño de Interfaces).
**Stack:** React 19 + TypeScript + Tailwind 4 + TanStack Query + Zustand + Axios · FastAPI + SQLModel + Alembic · PostgreSQL 16.

> **Estado: Fase 3 (Tienda, panel y despliegue) completa; quedan solo los bonus.** Además del backend de
> la Fase 2, ahora hay métricas (`/admin/metrics`), la tienda del cliente (catálogo con filtros, carrito
> persistente, direcciones con mapa, checkout con `Idempotency-Key` y seguimiento), la gestión de pedidos y
> pagos del personal, el panel de métricas con gráficos y el despliegue con Docker Compose + Nginx.
> MercadoPago (Anexo B) está implementado y verificado contra MercadoPago con credenciales de prueba (cobro, rechazo,
> reintento, pago pendiente y webhook real). El despliegue en la nube no se realiza. Ver `docs/` para el ERD.

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

## Despliegue con Docker Compose

Levanta todo el sistema (4 servicios) con un solo comando. **Solo Nginx publica un puerto**; la base y la API
quedan en la red interna.

```bash
cp .env.example .env          # y completar/ajustar: POSTGRES_PASSWORD, SECRET_KEY (mín. 32 caracteres), etc.
docker compose up -d --build
# Aplicación: http://localhost · Documentación de la API: http://localhost/docs
```

| Servicio | Imagen | Función |
| --- | --- | --- |
| `db` | `postgres:16-alpine` | Base de datos (volumen `pgdata`). |
| `backend` | `python:3.11-slim` | Al arrancar aplica las migraciones y el seed (idempotente) y sirve la API con `--proxy-headers`. |
| `frontend` | `node:22-alpine` (multistage) | Compila la SPA con `VITE_API_URL=/api/v1`, la copia a un volumen y termina. |
| `nginx` | `nginx:1.28-alpine` | Sirve la SPA, las imágenes (`/media/`) y enruta `/api/v1/`, `/docs` y `/openapi.json` al backend. |

Detalles de Nginx que importan: `client_max_body_size 5m` (las imágenes llegan a 2 MB), `/openapi.json`
enrutado (si no, `/docs` queda en blanco) y `X-Forwarded-For` **sobrescrito** con la IP real, para que el
límite de intentos de login no se pueda esquivar falseando la cabecera.

Para cargar los datos de demostración en el despliegue:
`docker compose exec backend python -m app.db.demo`. Con `ENVIRONMENT=production` las cookies de sesión
pasan a `Secure` (solo HTTPS); en `localhost` dejar `development`. Apagar con `docker compose stop`
(conserva los datos) o `docker compose down -v` (los borra).

## MercadoPago (Anexo B, opcional)

Cobro con tarjeta (Checkout API) y confirmación automática por webhook. **Sin credenciales la forma de pago no se
ofrece** y el sistema funciona igual con efectivo y transferencia.

1. Crear una aplicación en <https://www.mercadopago.com.ar/developers> y copiar sus **credenciales de prueba**.
2. Completar en `backend/.env` (o en el `.env` raíz si se usa Docker): `MP_ACCESS_TOKEN` (privada),
   `MP_PUBLIC_KEY`, `MP_NOTIFICATION_URL` (`https://<dominio>/api/v1/pagos/webhook`) y `MP_WEBHOOK_SECRET`.
3. En el panel de MercadoPago, registrar esa URL como webhook del evento *Pagos* y copiar la clave secreta.
   MercadoPago no puede llamar a `localhost`: para probar el webhook en tu máquina hay que abrir un túnel (por ejemplo
   `cloudflared tunnel --url http://localhost:8000`) y usar su dirección `https://…` en `MP_NOTIFICATION_URL`. Esa
   dirección cambia cada vez que se reinicia el túnel gratuito. Sin webhook, el cobro con tarjeta igual funciona.

| Endpoint | Qué hace |
| --- | --- |
| `GET /pagos/mercadopago/config` | Devuelve solo la clave pública, que el SDK del navegador necesita para tokenizar. |
| `POST /pagos/mercadopago` | Cliente dueño del pedido PENDIENTE. Recibe el token de la tarjeta; **el monto lo fija el servidor** con el total del pedido. |
| `POST /pagos/webhook` | Público, pero exige firma HMAC-SHA256 válida (`x-signature`). Consulta el pago en MercadoPago y confirma el pedido. |

Los datos de la tarjeta los tokeniza el navegador con MercadoPago y **nunca pasan por el backend**. El flujo, según
el estado que devuelve MercadoPago: `approved` confirma el pedido en la misma transacción; `pending` o `in_process`
lo dejan PENDIENTE hasta el webhook; `rejected` muestra el motivo y permite reintentar con otra tarjeta. Hay un solo
`Pago` por pedido: un reintento lo actualiza con una `idempotency_key` nueva generada en el backend. El webhook es
idempotente (un aviso repetido no cambia nada) y ignora los avisos de un intento anterior ya reemplazado.

#### Probar el webhook en tu máquina (túnel)

El cobro con tarjeta funciona sin túnel. Solo hace falta para ver llegar **avisos reales** de MercadoPago (por ejemplo,
la confirmación automática de un pago que quedó pendiente). Como MercadoPago no puede llamar a `localhost`, se abre un
túnel que le da a tu máquina una dirección pública **temporal**: cambia cada vez que se abre y solo funciona mientras
el túnel, el backend y la computadora estén encendidos.

**Una sola vez**, descargar `cloudflared` (no requiere cuenta ni instalación):

```bash
mkdir -p ~/herramientas && cd ~/herramientas
curl -L -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared
```

**Cada vez que se quiera probar:**

1. Levantar la base, el backend y el frontend como siempre.
2. En otra terminal, abrir el túnel y dejarla abierta:
   ```bash
   ~/herramientas/cloudflared tunnel --url http://localhost:8000
   ```
   Tras unos segundos imprime una dirección `https://<algo>.trycloudflare.com`. Copiarla. (Con Docker, apuntar al
   puerto de Nginx: `--url http://localhost:80`.)
3. En `backend/.env` (o en el `.env` de la raíz con Docker) poner esa dirección más la ruta del webhook:
   ```
   MP_NOTIFICATION_URL=https://<algo>.trycloudflare.com/api/v1/pagos/webhook
   ```
4. **Reiniciar el backend** (`Ctrl+C` y volver a lanzar `uvicorn`; el modo `--reload` no recarga al cambiar el `.env`).
   Con Docker: `docker compose up -d backend`.
5. Pagar en la app con una tarjeta de prueba. Con el titular `CONT` el pago queda pendiente.
6. En la terminal del backend debe aparecer una línea `POST /api/v1/pagos/webhook?... 200 OK`: es el aviso real.
   Un `401` significa que `MP_WEBHOOK_SECRET` no coincide con la clave secreta del panel de MercadoPago.
7. Al terminar, cerrar el túnel con `Ctrl+C`. La próxima vez, repetir desde el paso 2 con la dirección nueva.

`MP_ACCESS_TOKEN`, `MP_PUBLIC_KEY` y `MP_WEBHOOK_SECRET` no cambian entre una sesión y otra. Si no llega ningún aviso,
registrar también la dirección nueva en el panel de MercadoPago (Webhooks, evento *Pagos*). Mientras el túnel está
abierto, toda la API local es accesible desde internet: cerrarlo al terminar.

Tarjetas de prueba (el resultado lo decide el **nombre del titular**): `APRO` aprueba, `CONT` queda pendiente,
`OTHE` rechaza, `FUND` por fondos insuficientes, `SECU` por código inválido; Visa `4509 9535 6623 3704`, CVV `123`.

## Tests y verificaciones

```bash
# Backend (requiere la base levantada): crea sola la base de prueba `foodstore_test`, aplica las migraciones y siembra los datos.
cd backend
pytest                               # 265 tests (incluye 4 de concurrencia con hilos)
pytest --cov=app                     # cobertura (98 %)
ruff check . && ruff format --check .
alembic check                        # modelos y migraciones no divergen

# Frontend
cd frontend
npm run lint && npm run build && npm test      # 54 tests
```

Los tests del backend corren cada caso dentro de una transacción que se revierte, contra PostgreSQL
real, con el Unit of Work inyectado mediante `dependency_overrides`. `tests/test_erd.py` lee
`docs/food_store_erd.puml` y lo compara con la base migrada (columnas, tipos, NOT NULL, DEFAULT, PK,
UNIQUE, FK con su `ON DELETE` y ENUM), así el ERD y las migraciones no pueden divergir (CE-09).

Además se verificó en un navegador real (Playwright + Chrome) el recorrido completo del cliente, del
personal y de las pantallas de las fases anteriores, y se auditó la accesibilidad con axe-core (WCAG 2.1 A
y AA) sobre unas 25 pantallas. Queda una excepción conocida: el texto blanco sobre el naranja `accent-600`
(botón primario) da 3,56:1 de contraste (AA pide 4,5:1); se mantiene porque ese color lo fija la
sección 11.4 de la especificación.

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
| Métricas (adición) | `/admin/metrics`: `resumen`, `ventas`, `top-productos` (ADMIN) y `stock-bajo`, `mermas` (ADMIN y STOCK). Una **venta** es un pedido con pago aprobado que no está CANCELADO; los días se miden en la zona horaria del local y los rangos admiten hasta 366 días (422 `INVALID_RANGE` / `RANGE_TOO_LARGE`). |
| `GET /pagos/formas` (agregado) | Lista las formas de pago habilitadas para el checkout (cualquier usuario autenticado). |
| Filtros en la URL | Los listados de pedidos del personal guardan estado, fechas y página en la URL: se pueden compartir y sobreviven a recargar. |
| Carrito | Persistente en el navegador; al abrirlo se revalidan precios y disponibilidad contra el servidor (casos de la sección 11.2) y el checkout manda una sola `Idempotency-Key` por intento. |
| Mapa de direcciones | Leaflet con teselas de OpenStreetMap (sin clave de API). |
| Portada | La raíz `/` es directamente el catálogo; no hay página de inicio aparte. |
| Contraste del botón primario | Ver la nota de accesibilidad en "Tests y verificaciones". |
| MercadoPago sin credenciales | La forma de pago no se ofrece (`GET /pagos/formas` la omite y crear un pedido con ella responde 422) y los endpoints de cobro responden 503 `MP_NOT_CONFIGURED`. El seed la deja `habilitado = true` (como pide el Anexo B). |
| Pago de MercadoPago en curso | Con un pago `pending` o `in_process` no se acepta otro cobro (409 `PAYMENT_IN_PROGRESS`): evita cobrar dos veces mientras se espera al webhook. |
| Pago aprobado de un pedido cancelado | El webhook registra el estado pero no revive el pedido; el reembolso queda como tarea manual (fuera de alcance, igual que en la Fase 2). |
| `GET /pagos/mercadopago/config` (agregado) | La spec dice "clave pública para el SDK del frontend" sin definir cómo llega; se sirve desde el backend para no recompilar la SPA al cambiar de credenciales. |
| Consultas al profesor | Mientras no haya respuesta se aplican las propuestas del plan de trabajo (zonas con `activo`, unidad de medida fijada por la primera receta, lotes antes que stock sin lote, pagos por estado dentro de `/admin/metrics/resumen`). |

## Estructura

```
backend/    API FastAPI (app/core, app/modules/*, app/db con seed y demo, alembic, tests)
frontend/   SPA React (src/shared, src/features, src/store, src/routes, src/pages)
docs/       food_store_erd.puml y food_store_erd.svg
docker-compose.yml       despliegue completo (db + backend + frontend + nginx)
docker-compose.dev.yml   solo la base de datos, para desarrollar
nginx/                   configuración del proxy inverso
.env.example             variables del despliegue con Docker
```

## Pendiente (bonus)

- **Despliegue en la nube** con HTTPS y `COOKIE_SECURE`: no se hará; el sistema se entrega para correr localmente
  (con o sin Docker). Con `ENVIRONMENT=production` las cookies pasan a `Secure` si se desplegara tras HTTPS.

### Verificado contra MercadoPago (credenciales de prueba, navegador real)

| Caso | Titular | Resultado |
| --- | --- | --- |
| CE-B2 pago aprobado | `APRO` | `approved / accredited`: el pedido pasa a CONFIRMADO y la pantalla lo muestra. |
| CE-B3 pago rechazado | `OTHE` | `rejected / cc_rejected_other_reason`: el pedido sigue PENDIENTE y se explica el motivo. |
| Reintento tras el rechazo | `APRO` | Se actualiza el mismo registro de pago (uno por pedido) y el pedido se confirma. |
| Pago pendiente | `CONT` | `in_process / pending_contingency`: el pedido queda PENDIENTE y la pantalla avisa que se está procesando. |
| Webhook real (túnel cloudflared) | `CONT` | Llegó el aviso firmado de MercadoPago y se aceptó (la firma `x-signature` real coincide con la implementada); al cancelar el pago desde la API, el aviso actualizó `mp_status` a `cancelled` y el pedido siguió PENDIENTE. |
| Webhook sobre un pedido ya confirmado | `APRO` | El aviso real respondió 200 sin efectos: el historial no se duplicó. |
| Firma ajena | — | 401 `INVALID_SIGNATURE`; un pago que MercadoPago no conoce se ignora con 200. |

Nota: la API de pagos (`Payments`) que usa la integración figura en la documentación de MercadoPago como *legacy*
(sigue funcionando, sin funciones nuevas); la sustituta es la API *Orders*. Se mantiene Payments porque es la que
describe el Anexo B. Migrar a Orders implicaría cambiar el cobro, las notificaciones y los tests.
