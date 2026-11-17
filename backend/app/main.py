"""FastAPI: CORS, manejadores de error, rate limiting y routers bajo /api/v1."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.media import URL_PREFIX, media_dir
from app.core.rate_limit import limiter
from app.modules.auth.router import router as auth_router
from app.modules.categorias.router import router as categorias_router
from app.modules.config.router import config_router, envio_router
from app.modules.direcciones.router import router as direcciones_router
from app.modules.inventario.router import router as inventario_router
from app.modules.produccion.router import router as produccion_router
from app.modules.productos.router import ingredientes_router, productos_router
from app.modules.usuarios.router import router as usuarios_router

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Food Store API",
        version="1.0.0",
        description="Sistema de gestión de pedidos de comida (TPI).",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.state.limiter = limiter
    # Sin el handler propio de slowapi: su RateLimitExceeded es una HTTPException de Starlette y el
    # manejador global la responde con el formato de error estándar.
    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,  # necesario para cookies HttpOnly con withCredentials
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(usuarios_router, prefix=API_PREFIX)
    app.include_router(direcciones_router, prefix=API_PREFIX)
    app.include_router(categorias_router, prefix=API_PREFIX)
    app.include_router(productos_router, prefix=API_PREFIX)
    app.include_router(ingredientes_router, prefix=API_PREFIX)
    app.include_router(inventario_router, prefix=API_PREFIX)
    app.include_router(produccion_router, prefix=API_PREFIX)
    app.include_router(config_router, prefix=API_PREFIX)
    app.include_router(envio_router, prefix=API_PREFIX)

    # Imágenes de productos. Con Docker las sirve Nginx directamente desde el volumen; en desarrollo, la app.
    media_dir().mkdir(parents=True, exist_ok=True)
    app.mount(URL_PREFIX, StaticFiles(directory=media_dir()), name="media")
    return app


app = create_app()
