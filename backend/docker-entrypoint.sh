#!/bin/sh
# Al iniciar: migraciones, datos iniciales (idempotentes) y el servidor.
set -e

alembic upgrade head
python -m app.db.seed

# El puerto 8000 NO se publica: solo Nginx llega hasta acá y siempre ENVÍA X-Forwarded-For con la IP real del
# cliente (sobrescribe lo que mande el cliente). Por eso se confía en esa cabecera: así el límite de intentos de
# login (sección 5.4) cuenta por IP real y no por la del proxy.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
