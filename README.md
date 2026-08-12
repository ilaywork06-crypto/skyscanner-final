# Skyscanner

Skyscanner is the inventory of the events that produce files - every event, the entities nested inside it
(telemetries, logs, video) and every raw, parsed and additional file that belongs to them.

The system is a monorepo with three FastAPI services, three shared Python packages, one TypeScript grid library
and a Vue 3 web client. Everything runs behind one nginx container with a single `docker compose up`.

---

## Layout

```
sky3/
├── docker-compose.yml            every service, the document store, the bucket and the mail relay
├── pyproject.toml                the uv workspace of the Python side
├── package.json                  the npm workspace of the TypeScript side
├── packages/
│   ├── skyscanner_models/        the API models - pydantic and nothing else, shared by every service
│   ├── skyscanner_common/        settings, logging, mongo access, object storage, identity, error handling
│   ├── ag_grid_lib/              schema introspection, column generation and query translation for AG Grid
│   ├── ag-grid-ts/               the client half of the grid library - parsing, grid setup, reactive controller
│   └── sky-ui/                   the shared Vue components and formatting rules the client renders with
├── services/
│   ├── events_service/           the inventory, the entities, the dynamic schema, the templates, the exports
│   ├── storage_service/          uploads, downloads and temporary links for every stored file
│   └── notification_service/     turns the pending notifications of the inventory into mails
└── frontend/                     Vue 3, Vuetify, TypeScript, unplugin-vue-router, AG Grid
```

Every service is split into an **api**, a **service** and a **repository** layer. Only the repository layer
talks to the document store, and only the storage service talks to the bucket.

---

## Running the whole thing

```bash
cp .env.example .env      # optional, every value has a default
docker compose up --build
```

| What | Where |
| --- | --- |
| Web client | http://localhost:8080 |
| Events service API docs | http://localhost:8080/api/docs |
| Storage service API docs | http://localhost:8080/api/storage/docs |
| Notification service API docs | http://localhost:8080/api/notifications/docs |
| MinIO console | http://localhost:9001 (`skyscanner` / `skyscanner-secret`) |
| MailHog inbox | http://localhost:8025 |

On the first start the events service only creates its indexes. Nothing is seeded, so the system comes up with an
empty document store and the inventory starts out with no rows at all.

An empty system needs three things before the first event can be uploaded, and all of them are declared from the
web client: a **industry** on the Industries page, at least one **event type** on the Types page, and, if the entities of
the event should be grouped, an **entity type** on the same page. The dynamic fields of an industry are declared
afterwards on the Schema page. The same declarations are reachable over the API:

```bash
curl -X POST localhost:8080/api/industries        -H 'Content-Type: application/json' \
     -d '{"key": "robotics", "name": "Robotics"}'
curl -X POST localhost:8080/api/types/events -H 'Content-Type: application/json' \
     -d '{"key": "bench_run", "name": "Bench Run"}'
```

### Running the pieces by hand

```bash
uv sync --all-packages
uv run uvicorn events_service.main:create_app       --factory --port 8000
uv run uvicorn storage_service.main:create_app      --factory --port 8001
uv run uvicorn notification_service.main:create_app --factory --port 8002

npm install
npm run dev --workspace frontend        # http://localhost:5173, proxies /api to the services
```

---

## How the dynamic schema works

Nothing about a column is written in the web client. The backend keeps the field declarations in the `fields`
collection, and `ag_grid_lib` turns them into AG Grid column definitions:

1. `GET /api/grid/events/columns?industry=robotics` merges the built in columns of the inventory with every field
   the industry declared, plus the keys that were written by a script but never declared (those arrive hidden).
2. The client resolves the `cellRenderer` name of each column against its renderer registry and renders the table.
3. `POST /api/grid/events/rows` receives the search, the filter model and the sort model, and `ag_grid_lib`
   translates them into a document store query.

A dynamic value is stored twice on purpose: as the `metadata` list the schema asks for, and as a flat `data`
sub document so that filtering, sorting and indexing stay cheap.

Declaring a field is a normal write against `POST /api/fields`, or the **Schema** page of the web client.
Filtering by an industry shows the shared fields plus that industry's fields; the global view shows only the shared ones.

---

## Paging the listing endpoints

Every endpoint that answers with a plain list takes an `offset` and a `limit`, where a limit of zero means every
match. The endpoints that answer with a `Page` envelope keep their `page` and `page_size`.

```bash
curl 'localhost:8080/api/fields?scope=event&offset=0&limit=25'
curl 'localhost:8080/api/types/events?offset=0&limit=10'
curl 'localhost:8080/api/industries?offset=0&limit=10'
```

`offset`/`limit` are offered by `/api/fields`, `/api/types/events`, `/api/types/entities`, `/api/industries`,
`/api/templates`, `/api/subscriptions` and `/api/events/{id}/entities`.

---

## Uploading an event

The three steps of the create wizard map onto the API like this:

1. **Data** - event type, industry, platform, status, the name the event is listed under, the reference id the
   user knows it by, free text and the files of the event itself. The files go to `POST /api/storage/artifacts`
   first and come back as artifact records. The wizard requires the name; `event_id` is minted by the service
   and is never part of the payload.
2. **Industry Fields** - the dynamic fields declared for the chosen industry, validated server side against
   their type, their options and their constraints.
3. **Add Entities** - any number of entities, each with its own type, its own dynamic fields and its own raw files.

`POST /api/events` then stores the whole thing as one document.

Raw first, parsed later is the normal flow: upload an entity with its raw files, and once the parsing products
exist, open the event, edit the entity and drop the parsed files in. The status follows the files rather than
the caller: an entity that carries parsed files is stored as `parsed`, and a request that claims `parsed`
without a single parsed file is refused. `POST /api/events`, `POST /api/events/{id}/entities` and
`PATCH /api/events/{id}/entities/{entity_id}` all read it the same way.

---

## Authentication

The services never authenticate anybody. They read the identity from the headers the reverse proxy injects:

```
X-Auth-User    the login name
X-Auth-Email   the mail address
X-Auth-Roles   viewer | editor | admin, comma separated
X-Auth-Industries   the industry keys the caller belongs to
```

`skyscanner_common.identity` maps the roles onto permissions, and every endpoint is guarded by a
`require_permission(...)` dependency. While the proxy is not in place, `AUTH_ALLOW_ANONYMOUS=true` grants the
roles named in `AUTH_ANONYMOUS_ROLES`. `frontend/nginx.conf` is where the real proxy plugs in.

---

## Notifications

The events service never sends a mail. It writes a row into `notification_outbox`, and the notification service
polls that collection, resolves the subscriptions that match the industry, the event type or the single event, and
hands the message to the mail relay. Subscriptions live on the **Subscriptions** page and on the bell of an
event page.

Both of those are **hidden from the web client for now**: subscriptions are an advanced feature that has not been
opened to users yet. The switch is a single constant, `SUBSCRIPTIONS_ENABLED` in `frontend/src/features.ts`; while
it is false the menu entry and the bell are not rendered and a router guard sends `/subscriptions` back to the
inventory. Nothing else is disabled - the endpoints, the outbox and the notification service all keep working, so
flipping that one constant to true brings the whole feature back.

---

## Watchdogs

Online ingestion is not built yet, but nothing stands in its way: `UploadSource` already tells `manual` apart
from `watchdog`, `automation` and `script`, and both `POST /api/events` and `POST /api/events/{id}/entities`
take the same payload a watchdog would send. A watchdog is a new producer against the existing API, not a
change to it.

---

## Checks

```bash
uv run mypy -p skyscanner_models -p skyscanner_common -p ag_grid_lib \
            -p events_service -p storage_service -p notification_service
uv run pylint skyscanner_models skyscanner_common ag_grid_lib \
              events_service storage_service notification_service

npm run type-check --workspace frontend
npm run lint --workspace frontend
```

Both Python checks are clean, and the web client passes `vue-tsc` and `eslint` with zero warnings.
