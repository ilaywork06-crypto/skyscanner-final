# Truth

A register of working assumptions - the conditions, figures and behaviours a project is planned on - filed by
industry and declared by schemas.

This directory holds the web client only. The API it reads is the FastAPI service described below.

## Running it

### Everything, for anybody on the network

```bash
cd truth
docker compose up --build
```

Two containers: the stand-in API, and nginx serving the built client and forwarding `/api` on to it. The
client is published on **port 8090 of every interface**, so anybody on the network opens
`http://<this machine>:8090` and reaches both through that one port - there is no second address to hand
out and no cross-origin request to allow. The API itself is deliberately not published.

`TRUTH_PORT` moves the port; `TRUTH_DEFAULT_CREATOR` sets who the client creates things as. To keep it to
this machine, publish it as `127.0.0.1:8090:80` instead.

The mock holds its register in memory, so `docker compose restart truth-api` puts the data back as it started.

### The client on its own, in front of a real API

```bash
TRUTH_API_URL=http://10.0.0.7:8000/ docker compose -f docker-compose.frontend.yml up --build
```

One container: the built page and an nginx that forwards `/api` on to wherever you point it. The address is
read when the container starts, so the same image serves any deployment - there is nothing to rebuild.

**The trailing slash matters.** It is what strips the `/api` the client prefixes, so `/api/assumption`
arrives at the service as `/assumption`.

`TRUTH_API_URL` defaults to `http://host.docker.internal:8000/`, which reaches a service running on this
machine outside Docker. For that to work the service has to listen on more than the loopback, or the
container's request is refused before it arrives:

```bash
MOCK_API_HOST=0.0.0.0 python3 truth/mock-api.py
```

### Without Docker, for developing

```bash
npm install                 # from the repository root
python3 truth/mock-api.py   # the stand-in API on http://localhost:8000
npm run dev:truth           # http://localhost:5174
```

| Variable | What it is for |
| --- | --- |
| `TRUTH_API_URL` | Where the assumptions API is reached, at build and dev time. |
| `TRUTH_ALLOWED_HOSTS` | Extra names the dev server may be reached by. See below. |
| `VITE_API_BASE_URL` | The address the browser sends its own requests to. Defaults to `/api`. |
| `VITE_DEFAULT_CREATOR` | Who the client creates things as before anybody sets a name. |

**Reaching the dev server by name.** It refuses a request whose `Host` is a name it was not told about -
that is what stops a page on the internet from pointing its own domain at your machine and reading the
source through a visitor's browser. An address is never a name, so `http://10.0.0.5:5174` always works; it
is `http://moon:5174` that gets turned away with *"This host is not allowed"*. The machine's own hostname is
allowed for you, so colleagues typing the obvious name get in. Name any others they use:

```bash
TRUTH_ALLOWED_HOSTS=moon,truth.lan npm run dev:truth
TRUTH_ALLOWED_HOSTS=.example.com  npm run dev:truth   # every name under a domain
TRUTH_ALLOWED_HOSTS=all           npm run dev:truth   # any name at all
```

The Docker setups have none of this to configure: nginx serves the built files and does not check the host.

## What the API offers, and what follows from it

Every endpoint the client uses:

| | |
| --- | --- |
| `GET /industry` `POST /industry` | listed with `offset`/`limit`; created with a name, description and creator |
| `GET /industry/{id}` `GET /industry/name/{name}` | one industry |
| `GET /schema` `POST /schema` | listed; declared with a scheme of fields and constraints |
| `GET /schema/{id}` `GET /schema/{id}/latest` `GET /schema/name/{name}` | one schema, whole |
| `POST /schema/{id}/revisions` `POST /schema/name/{name}/revisions` | a new revision of a declaration |
| `GET /assumption` `POST /assumption` | listed; created against one or more schemas |
| `GET /assumption/{id}` `GET /assumption/{id}/latest` | one assumption, whole |

Three properties of that surface shape the whole client:

**Nothing can be searched, filtered or ordered server side.** Each listing takes an offset and a limit and
answers with a bare array. The client therefore reads each collection whole (`requests/paging.ts`, which pages
until a short page comes back) and answers every question against what it holds (`utils/query.ts`). The table
keeps its search, its column filters, its sorting and its paging; all of it runs in the browser.

**The listing of an assumption carries neither its values nor its industries.** Only
`GET /assumption/{id}/latest` does. Every listed assumption is therefore read again on its own, six at a time
(`requests/assumptions.ts`), and the table is usable throughout rather than after: rows appear from the
listing and gain their values and industries as the readings land, with the progress said plainly above the
table. There is no endpoint that would make this fewer requests.

**A scheme is `list[dict[str, JsonValue]]`.** The service stores whatever it is handed and promises nothing
about the keys, so `utils/scheme.ts` reads generously and writes strictly.

Reading accepts what a script or a person might plausibly have written: a field named `key`, `name` or
`field`; a display name written as `display_name`, `label` or `title`; `list[str]` and `string[]` alike; and
a whole field written as `{"berth_count": "int"}`.

Writing goes out in exactly the shape the service expects. Every field carries these five, the flags always
present - a box the user left unticked is written `false`, never left out:

| | |
| --- | --- |
| `key` | what the value is stored under |
| `display_name` | what a person reads |
| `type` | one of the kinds below |
| `required` | `true` or `false` |
| `array` | `true` or `false` |

and then only what its own kind calls for:

| `type` | Also carries |
| --- | --- |
| `string` | — |
| `boolean` | — |
| `confined_number` | `min`, `max`, `step` — each optional, whole numbers |
| `confined_float` | `min`, `max`, `step` — each optional |
| `enum` | `options: list[str]` |
| `date` | — |

Those bounds are what the create form enforces before it sends: a required field, a value outside its
`min`/`max`, one off its `step`, or one that is not in an enumeration's `options` is caught beside the
input that caused it. The scheme's constraint list is always written empty, under the `constrains` spelling
the service reads, because the service does not support constraints yet.

### Columns are generated from the database, not written down

No endpoint generates column definitions, so the generation that would run in the backend runs in
`utils/columns.ts` - but off the same source it would have run off there. Nothing in that file names an
attribute of an assumption. The fixed columns are the fields the API itself returns on every assumption, and
every other column is read out of the schemas the register holds. Declaring a schema with a new attribute
gives the table a new column, with the renderer and the filter its declared type asks for.

### Two quirks of the API the client works around

- `POST /schema` reads its constraints under `constrains`; every read hands them back under `constraints`.
  Both are accepted on the way in and the former is what is sent, always empty - see `models/scheme.ts`.
- `POST /schema` takes its industries as numeric identifiers that no endpoint hands out. An empty list is
  sent, which leaves a schema reaching across every industry, and the dialog says so rather than leaving it
  as a silent omission.

## What is here

| | |
| --- | --- |
| Register table | dynamic columns, search, per-column filters, quick filters, sorting, paging, column picker |
| Row panels | the schema-declared attributes of a row, its industries, and what is known about its validation |
| Create an assumption | the two-step wizard: what every assumption carries, then the fields its schemas declare |
| Duplicate an assumption | the whole assumption prefilled into that wizard, from its own page |
| Constraint checking | `required`, `min`, `max`, `min_length`, `max_length`, `pattern`, `one_of`, shown per field |
| Industries | listed with counts, each with its own register; the drill-down is a chip that can be lifted |
| Schemas | listed, read whole, declared and revised through a builder for fields and constraints |
| Export | the current view, as it stands on screen, written to a spreadsheet in the browser |
| Snapshots | the register preserved in **this browser only** - see below |
| Themes | dark and light, every colour a token in `plugins/vuetify.ts` |

## What is not here, and why

- **Projects.** The design has an industry containing projects containing assumptions, with project tabs and a
  version selector. The API has no project and no version endpoint, so the navigation is industry to
  assumption. Nothing else in the client assumes projects will never exist.
- **Editing.** There is no `PATCH` or `DELETE` on anything. A schema is changed by revising it, which is
  offered; an assumption and an industry cannot be changed at all once created.
- **Files.** The design attaches files to assumptions. There is no storage endpoint, so no dropzone is shown.
- **Validation records.** `validation_responsible_parties` is a field on an assumption; validations are not a
  resource. The panel shows what the register actually knows rather than an empty table promising more.
- **Assumption history.** An assumption carries a `revision` number, but nothing lists its revisions or reads
  an earlier one.
- **Snapshots are local.** The design asks for the history of the table to be preserved and the API stores
  nothing of the sort. `utils/snapshots.ts` keeps them in this browser's own storage, and the page says so on
  every visit. When a snapshot endpoint exists, that module is the only thing that has to change.

## Layout

```
src/requests/    one module per resource, plus the pager that reads a collection whole
src/models/      the payloads, exactly as the API shapes them
src/utils/       scheme reading, column generation, the query engine, constraints, export, snapshots
src/composables/ the register held once and shared, and the table bound to it
src/components/  the table, its panel, the wizards and the builders
src/pages/       file-based routes
```

Everything not specific to this product - the cell renderers, the filters, the dynamic form inputs, the
formatting, the theme switch - comes from `@truth-platform/core-ui`, which this client shares with the
Skyscanner inventory.
