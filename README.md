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

An empty system needs four things before the first event can be uploaded, and all of them are declared from the
web client: an **industry** on the Industries page, at least one **event type**, at least one **platform** and,
if the entities of the event should be grouped, an **entity type**, all three on the Types page. The extra
fields an event type asks for are declared on the same page under the *Event fields* kind, and the dynamic
fields of the entities are declared afterwards on the Schema page. The same declarations are reachable over the
API, and every one of them names the industries it belongs to - an empty list means every industry:

```bash
curl -X POST localhost:8080/api/industries   -H 'Content-Type: application/json' \
     -d '{"key": "robotics", "name": "Robotics", "modules": ["arm", "gripper"]}'
curl -X POST localhost:8080/api/types/events -H 'Content-Type: application/json' \
     -d '{"key": "bench_run", "name": "Bench Run", "industries": ["robotics"], "fields": ["event_date"]}'
curl -X POST localhost:8080/api/types/platforms -H 'Content-Type: application/json' \
     -d '{"key": "rig_a", "name": "Rig A", "industries": ["robotics"]}'
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

1. `GET /api/grid/events/columns?industry=robotics` merges the built in columns of the inventory with the keys
   that were written by a script but never declared (those arrive hidden). The entity tables are generated the
   same way from `GET /api/grid/entities/columns`, out of the fields the entity type declared.
2. The client resolves the `cellRenderer` name of each column against its renderer registry and renders the table.
3. `POST /api/grid/events/rows` receives the search, the filter model and the sort model, and `ag_grid_lib`
   translates them into a document store query.

A dynamic value is stored twice on purpose: as the `metadata` list the schema asks for, and as a flat `data`
sub document so that filtering, sorting and indexing stay cheap.

Declaring a field is a normal write against `POST /api/fields`, or the **Schema** page of the web client.
Filtering by an industry shows the shared fields plus that industry's fields; the global view shows only the
shared ones.

The tabs the industries are picked from can be dragged into whatever order a reader works in, and that order
is kept in their own browser under `skyscanner.industry-tabs.order` - the services have no per user identity
yet, so an order written to the document store would be handed straight back to everybody. **All** is not an
industry but the absence of a choice of one, so it always leads the row and never takes part in the ordering.

A declaration says which of the two halves of the entity form it belongs to. `additional: false` is the entity
itself - what it is called, how it was recorded - and `additional: true` is the **additional data** underneath
it, the block users used to fill in with keys of their own invention. Declaring those keys is what turns two
people describing the same thing into two people writing the same field.

### Every value follows a declaration

A key nobody declared used to be accepted, stored with whatever type it was written as, and turned into a
column of its own. That is how one person wrote `sample_rate` and the next wrote `sampling_rate` onto
neighbouring rows, and how columns appeared that nobody remembered creating. `build_values` now refuses a
value whose key no declaration covers, and the forms of the web client no longer offer to invent one: the
additional data block is a form built out of the declarations, not a blank sheet.

Two things are deliberately left alone by the rule:

- **What is already stored.** An object that carries a key from before the rule keeps it: the value is shown
  read only under the form that would have asked for it, with the offer to take it off, and an edit that
  leaves it alone is accepted. Nothing new joins it. `build_values` takes those keys as `carried`.
- **The columns inferred from the documents.** `SchemaIntrospector` still reads the keys it finds in stored
  events and generates a hidden, read only column for each of them, so that a value written before the rule
  is not simply invisible. Such a column says *found in the stored events, never declared* in the **Columns**
  menu, and an undeclared value says *not declared* under its heading in the expanded row. Declaring the
  field for the key is what turns either of them into an ordinary column.

### Event fields

An **event field** is declared on the **Types** page under the *Event fields* kind, with a name, a type, its
allowed values if it is an enum, and the industry it belongs to. An event type then names the ones it asks
for, and the create wizard renders exactly those under **Additional Event Attributes** - beside the built in
fields of `OptionalEventField`, which stay the fixed vocabulary the service itself understands. A new question
about an event therefore costs a declaration rather than a change to that enumeration and to every form that
reads it:

```bash
curl -X POST localhost:8080/api/fields -H 'Content-Type: application/json' \
     -d '{"key": "mission_phase", "name": "Mission Phase", "type": "enum", "scope": "event",
          "metadata": {"options": ["ascent", "cruise", "descent"]}}'
curl -X POST localhost:8080/api/types/events -H 'Content-Type: application/json' \
     -d '{"key": "bench_run", "name": "Bench Run", "fields": ["event_date"],
          "custom_fields": ["mission_phase"]}'
```

---

## Deleting

Nothing is ever taken out of the document store. Deleting an event, an entity, a field, a type, a platform, a
template or a subscription writes `deleted: true` onto it together with the moment and the user, and every read
of every collection leaves the marked documents behind - which is what makes a deletion recoverable, keeps the
edit history answerable and stops the object storage pointing at records that cannot be read any more. Every
collection that can be deleted from carries an index on that attribute, because every single read of it now
narrows on the flag.

Undoing one is a single write:

```bash
docker compose exec mongo mongosh skyscanner --eval \
  'db.events.updateOne({_id: "<id>"}, {$set: {deleted: false}})'
```

---

## Paging the listing endpoints

Every endpoint that answers with a plain list takes an `offset` and a `limit`, where a limit of zero means every
match. The endpoints that answer with a `Page` envelope keep their `page` and `page_size`.

```bash
curl 'localhost:8080/api/fields?scope=event&offset=0&limit=25'
curl 'localhost:8080/api/types/events?offset=0&limit=10'
curl 'localhost:8080/api/industries?offset=0&limit=10'
```

`offset`/`limit` are offered by `/api/fields`, `/api/types/events`, `/api/types/entities`,
`/api/types/platforms`, `/api/industries`, `/api/templates`, `/api/subscriptions` and
`/api/events/{id}/entities`.

---

## Saved views

A **template** is the inventory table as somebody arranged it: which columns are shown, in what order and at
what width, what it is ordered by and what it is filtered to. Shared templates live in the document store;
private ones never leave the browser they were saved in, for the same reason the industry tab order does not.

The toolbar names the view the table is showing rather than only offering the list, and the choice is
remembered per table in this browser under `skyscanner.templates.active` - a user who works out of one view is
not made to pick it again every morning. A template that was deleted since simply leaves the table on the
default view and the stale memory of it is dropped.

**Default view** is always the last entry of the list: the table exactly as the backend generates it, with
every column at its declared place, nothing filtered and nothing searched. Returning to it throws away
whatever was arranged since, so a view with unsaved arrangements is asked about first and can be kept under a
name of its own - the same question, and the same way out, that switching between two templates asks.

---

## Uploading an event

The two steps of the create wizard map onto the API like this:

1. **Data** - event type, industry, the platforms it ran on, status, the **event brief** the event is listed
   under and the files of the event itself. The files go to `POST /api/storage/artifacts` first and come back
   as artifact records. The wizard requires the brief, which is stored as the `name` of the event; `event_id`
   is minted by the service and is never part of the payload. The rest of the built in fields - the reference
   id, the date, the experiment result and the free text - are only asked for when the chosen **event type**
   declares them, which is what keeps an experiment result off an event that is not an experiment, and the
   **event fields** that type names are asked for underneath them.
2. **Add Entities** - any number of entities, each with its own type, its own dynamic fields, its own
   additional data and its own raw files.

What an event is asked for beyond the built in fields is decided by its **event type** rather than by its
industry, and the entities underneath it are shaped by the dynamic schema of their own entity type, which an
industry does vary along with its modules.

`POST /api/events` then stores the whole thing as one document.

### Attaching and detaching files

The same file cannot be attached twice: two artifacts under one owner are the same file when they carry the
same name in the same folder, and the second one is refused rather than stored beside it - the key in the
bucket says nothing about it, because every upload is written under a fresh identifier so that two uploads can
never overwrite one another. `require_unique_artifacts` enforces it on both the create and the update paths.

Detaching one is an ordinary edit: `PATCH /api/events/{id}` and `PATCH /api/events/{id}/entities/{entity_id}`
take the whole replacement list, so a list that leaves a file out detaches it, under the same reason as the
rest of the edit and recorded in the history beside it. The edit dialogs mark a file for removal rather than
reaching into the bucket, so the mark can be taken back until Save is pressed. The bytes stay in the bucket:
detaching drops the reference, exactly as deleting an event does.

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

## The map behind a coordinate

A dynamic field may be declared as a `coordinate`, which stores a longitude, a latitude and an optional
altitude and is filled in by pointing at a map. The map is drawn with Leaflet against whatever tile server the
deployment names, because the system is meant to run behind a firewall and no public one is assumed:

```bash
VITE_MAP_TILE_URL='https://tiles.internal/{z}/{x}/{y}.png' docker compose up --build web
```

Without it the field still takes a point - it just takes it as three typed numbers rather than a click.

---

## Browsers

The table library derives most of its palette at run time with `color-mix()`, which reached Chrome in version
111; on anything older every derived border, hover and header separator is dropped as invalid. The generated
stylesheet is therefore rewritten once on browsers without it, by `packages/ag-grid-ts/src/compatibility.ts`,
and the bundler targets the floor named in `frontend/vite.config.ts` rather than inheriting a recent baseline.

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
