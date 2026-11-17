"""Imágenes subidas: validación del contenido real, renombrado con UUID y almacenamiento en disco.

Solo la URL se guarda en la base (sección 6.3). El tipo se valida por la FIRMA del archivo, no por la
extensión ni por el content-type que declara el request, que el cliente controla.
"""

import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import ValidationError

MAX_BYTES = 2 * 1024 * 1024  # 2 MB
URL_PREFIX = "/media"

# extensión que se le da al archivo guardado, según la firma detectada
_EXTENSIONES = {"jpeg": "jpg", "png": "png", "webp": "webp"}


def detectar_tipo(contenido: bytes) -> str | None:
    """Devuelve 'jpeg', 'png' o 'webp' según los primeros bytes, o None si no es una imagen admitida."""
    if contenido.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "webp"
    return None


def media_dir() -> Path:
    return Path(get_settings().MEDIA_DIR)


def validar_imagen(contenido: bytes) -> str:
    """Valida tamaño y tipo real. Devuelve la extensión con la que se guardará."""
    if not contenido:
        raise ValidationError("El archivo está vacío", code="EMPTY_FILE", field="archivo")
    if len(contenido) > MAX_BYTES:
        raise ValidationError("La imagen supera el máximo de 2 MB", code="FILE_TOO_LARGE", field="archivo")
    tipo = detectar_tipo(contenido)
    if tipo is None:
        raise ValidationError("Solo se admiten imágenes JPEG, PNG o WEBP", code="INVALID_IMAGE_TYPE", field="archivo")
    return _EXTENSIONES[tipo]


def guardar_imagen(contenido: bytes, subcarpeta: str) -> str:
    """Valida y guarda la imagen con un nombre UUID. Devuelve la URL pública (relativa)."""
    extension = validar_imagen(contenido)
    nombre = f"{uuid.uuid4().hex}.{extension}"
    destino = media_dir() / subcarpeta
    destino.mkdir(parents=True, exist_ok=True)
    (destino / nombre).write_bytes(contenido)
    return f"{URL_PREFIX}/{subcarpeta}/{nombre}"


def borrar_imagen(url: str | None) -> None:
    """Elimina el archivo de una URL propia. Ignora URLs ajenas o inexistentes."""
    if not url or not url.startswith(URL_PREFIX + "/"):
        return
    base = media_dir().resolve()
    ruta = (base / url.removeprefix(URL_PREFIX + "/")).resolve()
    if base in ruta.parents and ruta.is_file():  # nunca salir de MEDIA_DIR
        ruta.unlink()
