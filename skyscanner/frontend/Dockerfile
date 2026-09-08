FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
COPY libraries/ag-grid-ts/package.json ./libraries/ag-grid-ts/package.json
COPY libraries/core-ui/package.json ./libraries/core-ui/package.json
COPY truth/frontend/package.json ./truth/frontend/package.json
COPY skyscanner/frontend/package.json ./skyscanner/frontend/package.json

RUN npm ci

COPY libraries/ag-grid-ts ./libraries/ag-grid-ts
COPY libraries/core-ui ./libraries/core-ui
COPY skyscanner/frontend ./skyscanner/frontend

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Where the coordinate field draws its map from. The system is meant to run behind a firewall, so no tile
# server is assumed: without one the field still takes a point, it just takes it as three typed numbers.
ARG VITE_MAP_TILE_URL=
ENV VITE_MAP_TILE_URL=$VITE_MAP_TILE_URL
ARG VITE_MAP_ATTRIBUTION=
ENV VITE_MAP_ATTRIBUTION=$VITE_MAP_ATTRIBUTION

RUN npm run build --workspace skyscanner-frontend

RUN find /app/skyscanner/frontend/public -type f -exec chmod 644 {} \; && \ 
    find /app/skyscanner/frontend/public -type d -exec chmod 755 {} \;

FROM nginx:1.27-alpine

COPY skyscanner/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/skyscanner/frontend/dist /usr/share/nginx/html
COPY --from=build /app/skyscanner/frontend/public /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
