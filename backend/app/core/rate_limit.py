"""Rate limiting del login con slowapi (sección 5.4).

El decorador `@limiter.limit` de slowapi cuenta TODOS los requests, y la spec pide limitar solo los
intentos FALLIDOS. Por eso el login usa el almacenamiento y la estrategia del limiter directamente:
`test` consulta sin consumir, `hit` registra un fallo y `clear` limpia al autenticarse bien.
"""

import time

from limits import RateLimitItemPerMinute
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.errors import TooManyRequestsError

limiter = Limiter(key_func=get_remote_address)

_SCOPE = "login-fallido"


def _item() -> RateLimitItemPerMinute:
    settings = get_settings()
    return RateLimitItemPerMinute(settings.LOGIN_MAX_FAILED_ATTEMPTS, settings.LOGIN_WINDOW_MINUTES)


def ensure_login_allowed(ip: str) -> None:
    """Lanza 429 con Retry-After si la IP ya acumuló el máximo de intentos fallidos."""
    item = _item()
    if limiter.limiter.test(item, _SCOPE, ip):
        return
    stats = limiter.limiter.get_window_stats(item, _SCOPE, ip)
    raise TooManyRequestsError(
        "Demasiados intentos fallidos. Intente nuevamente más tarde.",
        retry_after=int(stats.reset_time - time.time()) + 1,
        code="TOO_MANY_LOGIN_ATTEMPTS",
    )


def register_failed_login(ip: str) -> None:
    limiter.limiter.hit(_item(), _SCOPE, ip)


def clear_failed_logins(ip: str) -> None:
    limiter.limiter.clear(_item(), _SCOPE, ip)
