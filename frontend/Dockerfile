FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
COPY packages/ag-grid-ts/package.json ./packages/ag-grid-ts/package.json
COPY packages/sky-ui/package.json ./packages/sky-ui/package.json
COPY frontend/package.json ./frontend/package.json

RUN npm ci

COPY packages/ag-grid-ts ./packages/ag-grid-ts
COPY packages/sky-ui ./packages/sky-ui
COPY frontend ./frontend

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Where the coordinate field draws its map from. The system is meant to run behind a firewall, so no tile
# server is assumed: without one the field still takes a point, it just takes it as three typed numbers.
ARG VITE_MAP_TILE_URL=
ENV VITE_MAP_TILE_URL=$VITE_MAP_TILE_URL
ARG VITE_MAP_ATTRIBUTION=
ENV VITE_MAP_ATTRIBUTION=$VITE_MAP_ATTRIBUTION

RUN npm run build --workspace frontend


FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
