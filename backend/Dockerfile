# Backend de Food Store (FastAPI). La imagen no incluye los tests ni las dependencias de desarrollo.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY docker-entrypoint.sh .

# No se corre como root. /app/media es el volumen de las imágenes de productos (lo comparte Nginx, de solo lectura).
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/media \
    && chown -R app:app /app/media \
    && chmod +x docker-entrypoint.sh
USER app

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
