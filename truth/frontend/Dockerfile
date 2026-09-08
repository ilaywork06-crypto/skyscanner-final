FROM node:22-alpine AS build

WORKDIR /app

# Every workspace of the repository has to be declared before the lockfile can be installed against it,
# even the ones this image never builds.
COPY package.json package-lock.json ./
COPY packages/ag-grid-ts/package.json ./packages/ag-grid-ts/package.json
COPY packages/core-ui/package.json ./packages/core-ui/package.json
COPY frontend/package.json ./frontend/package.json
COPY truth/frontend/package.json ./truth/frontend/package.json

RUN npm ci

COPY packages/ag-grid-ts ./packages/ag-grid-ts
COPY packages/core-ui ./packages/core-ui
COPY truth/frontend ./truth/frontend

# The client asks its own origin for the API, and nginx is what forwards that on to whatever is answering.
# Where that is, is decided when the container starts rather than here, so one image serves any deployment.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Who the client creates things as until somebody sets a name of their own.
ARG VITE_DEFAULT_CREATOR=
ENV VITE_DEFAULT_CREATOR=$VITE_DEFAULT_CREATOR

RUN npm run build --workspace truth-frontend


FROM nginx:1.27-alpine

COPY truth/frontend/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/truth/frontend/dist /usr/share/nginx/html

# Where the API is. Override it to put this image in front of any deployment, mock or real; the trailing
# slash matters, because it is what strips the /api prefix off on the way through.
ENV TRUTH_API_URL=http://truth-api:8000/

# Without this filter envsubst would also replace nginx's own variables and leave the config broken.
ENV NGINX_ENVSUBST_FILTER=TRUTH_API_URL

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
