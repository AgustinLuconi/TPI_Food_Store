# Frontend de Food Store. Es un servicio de UNA sola ejecución: compila la SPA con Vite y copia el resultado al
# volumen que Nginx sirve. Después termina (Nginx espera a que termine con service_completed_successfully).
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# La SPA se usa siempre a través de Nginx (mismo origen), así que la API vive en una ruta relativa: el puerto 8000
# no se publica.
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM node:22-alpine
WORKDIR /app
COPY --from=build /app/dist ./dist
CMD ["sh", "-c", "cp -r /app/dist/. /out/ && echo 'SPA copiada al volumen'"]
