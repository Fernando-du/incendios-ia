# frontend/Dockerfile
# Etapa 1: Construcción (Vite + React)
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

# Etapa 2: Producción (Nginx)
FROM nginx:alpine
# Copiamos la build de Vite (por defecto en la carpeta /dist)
COPY --from=build /app/dist /usr/share/nginx/html
# Copiamos la configuración del proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]