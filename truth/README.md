# Truth

A register of working assumptions - the conditions, figures and behaviours a project is planned on - filed by
industry and declared by schemas.

```
truth/
├── backend/          the FastAPI service and the document store behind it
├── frontend/         the Vue 3 web client
├── mock-api.py       an in-memory stand-in for the service, for working on the client alone
└── docker-compose.yml
```

The shared components both this client and the Skyscanner one render with live in `libraries/` at the root of
the repository, not here.

## Running it

### Everything, for anybody on the network

```bash
cd truth
docker compose up --build
```

Three containers: the document store, the register service, and nginx serving the built client and
forwarding `/api` on to the service. The client is published on **port 8090 of every interface**, so anybody
on the network opens `http://<this machine>:8090` and reaches both through that one port - there is no second
address to hand out and no cross-origin request to allow. Neither the service nor the store is published.

`TRUTH_PORT` moves the port; `TRUTH_DEFAULT_CREATOR` sets who the client creates things as. To keep it to
this machine, publish it as `127.0.0.1:8090:80` instead.

**The register comes up empty.** Nothing is seeded. To try it at a size worth trying it at, fill it from
inside the service - the store is not published, so the only thing that can reach it is the service itself:

```bash
docker compose exec truth-api python /app/truth/backend/scripts/seed.py --count 100000
```

Outside Docker, where the store is reachable directly, the same script runs on the host:
`uv run python truth/backend/scripts/seed.py --count 100000`.

### The client in front of the in-memory stand-in

```bash
docker compose -f docker-compose.mock.yml up --build
```

The stand-in holds its register in memory and is the same on every run, which is what makes it useful for
working on the client. Nothing written through it survives a restart.

### Without Docker, for developing

```bash
npm install                                    # from the repository root
uv sync                                        # the Python side of the workspace
docker run -d -p 27017:27017 mongo:7           # or any document store you already have
uv run uvicorn truth_service.main:create_app --factory --port 8000
npm run dev:truth                              # http://localhost:5174
```

`python3 truth/mock-api.py` serves the stand-in on the same port if you would rather not run a store.

| Variable | What it is for |
| --- | --- |
| `MONGO_URI` | Where the document store is, read by the service. |
| `MONGO_DATABASE` | Which database the register lives in. Defaults to `truth`. |
| `TRUTH_ROOT_PATH` | The path a gateway reaches the service at, when it strips that path before forwarding. Empty when the service is reached directly. |
| `TRUTH_API_URL` | Where the assumptions API is reached, at build and dev time. |
| `TRUTH_ALLOWED_HOSTS` | Extra names the dev server may be reached by. |
| `VITE_API_BASE_URL` | The address the browser sends its own requests to. Defaults to `/api`. |
| `VITE_DEFAULT_CREATOR` | Who the client creates things as before anybody sets a name. |

**Reaching the dev server by name.** It refuses a request whose `Host` is a name it was not told about -
that is what stops a page on the internet from pointing its own domain at your machine and reading the
source through a visitor's browser. An address is never a name, so `http://10.0.0.5:5174` always works; it
is `http://moon:5174` that gets turned away. Name the others with `TRUTH_ALLOWED_HOSTS=moon,truth.lan`, or
`all` to give the protection up entirely. The Docker setups have none of this to configure.

## The API

| | |
| --- | --- |
| `GET /industry` `POST /industry` | listed with `offset`/`limit`, and with `with_counts` for the assumption counts |
| `GET /industry/{id}` `GET /industry/name/{name}` | one industry |
| `GET /schema` `POST /schema` | listed; declared with a scheme of fields and constraints |
| `GET /schema/{id}` `GET /schema/{id}/latest` `GET /schema/name/{name}` | one schema, whole |
| `POST /schema/{id}/revisions` `POST /schema/name/{name}/revisions` | a new revision of a declaration |
| `GET /assumption` `POST /assumption` | listed, values and industries included; created against one or more schemas |
| `GET /assumption/{id}` `GET /assumption/{id}/latest` | one assumption, whole |
| `POST /assumption/query` | the whole question a table asks, answered as one window and a count |
| `GET /assumption/facets/{key}` | every value one column is known to hold |
| `GET /health` | whether the store is answering |

The interactive documentation is at **http://localhost:8090/api/docs**, and at `/docs` when the service is
reached directly.

The gateway strips `/api` before forwarding, so the service is reached at a path it never sees. Its routes
are right either way, but the addresses the documentation page writes for itself are not: left to guess, it
loads and then asks for the description of the service at `/openapi.json`, which is not under the prefix the
gateway routes to the API - so the client's own page comes back instead, and the page reports that what it
was handed names no version of anything. `TRUTH_ROOT_PATH` is what the service is told about that prefix,
and it is the only way it can know, because the request itself no longer carries it. Compose sets it.

`POST /assumption/query` is the one the table runs on. It takes the search, the structured restrictions, the
ordering and the window in one body and answers with that window and the size of the whole match. It is a
POST because a filter model is a structure rather than a word, and a structure in a query string is a
structure waiting to be cut short by whichever proxy in the way has the shortest opinion about addresses.

Two spellings from the original service are still accepted, because things were written against them:
`POST /schema` reads its constraints under either `constrains` or `constraints` and always answers with
`constraints`; and it accepts industries as identifiers, as names, or as the bare numbers the original
service wanted and never handed out - a number names nothing and is left out.

## How it holds a large register

The register is expected to outgrow anything a browser could be handed, and every decision below follows
from that one fact.

**Nothing reads the whole register.** The client holds the industries and the declarations - both bounded by
how many people write them - and asks the service every question about the assumptions. What crosses the
network is one screen of rows, whatever the register holds.

**A listing carries its values and its industries.** The original listing carried neither, so the client
read every row it had just listed all over again, one request each. That is why a register of a hundred
thousand could never finish loading, and it is the first thing this service changed.

**The names an assumption is filed under are copied onto it.** A listing joins nothing. The price is a
rewrite whenever a name changes, and nothing in this API can rename an industry or a schema.

**Every index answers a restriction and an ordering at once, and ends with the identifier.** A table asks
for a window of an ordering, never for a set. An index that answers the restriction but stops short of the
ordering leaves the whole match to be sorted in memory - which, before these were written this way, meant
reading a hundred thousand documents to draw twenty five rows.

**The removal flag is tested for equality, not for "not true".** A negation is two ranges either side of a
value, and an index scanned as two ranges cannot hand back the fields after it in order. That one character
is the difference between an indexed sort and a sort of the whole register.

**A free text search is a text index**, over a blob every searchable attribute is folded into on write - a
lookup rather than a pass. It matches words rather than fragments, which is the trade for it being a lookup.

**A restriction on a declared attribute is answered by a wildcard index** over the values. It is the one
index that never has to be revised when a schema is, because the attributes are written by the people using
the register and nothing knows their names in advance.

Measured against a hundred thousand assumptions, on one laptop with the store in a container:

| | |
| --- | --- |
| a page of the register, any page near the front | ~40-80ms |
| narrowed to an industry | ~40ms |
| narrowed by a declared attribute | ~45ms |
| a free text search | ~130ms |
| the vocabulary of one column | ~250ms |
| page 3,960 of 4,000 | ~830ms |
| ordered by a declared attribute | ~880ms |
| narrowed by a typed fragment | ~1,200ms |

The last three are the honest slow paths. Deep paging walks the index to where it was asked to start, and
nothing but keyset paging fixes that - which a numbered pager cannot use. An ordering by a declared
attribute cannot come out of the wildcard index, because a wildcard index cannot serve a sort. A typed
fragment is an unanchored pattern, which is a pass over the register by definition; it is offered anyway,
because it is what a person means when they type into a column.

## What is here

| | |
| --- | --- |
| Register table | dynamic columns, search, per-column filters, quick filters, sorting, paging - every one of them answered by the service |
| Row panels | the schema-declared attributes of a row, its industries, and what is known about its validation |
| Create an assumption | the two-step wizard, checked against the declarations on the way in and again in the service |
| Duplicate an assumption | the whole assumption prefilled into that wizard, from its own page |
| Revisions | a declaration is never edited, it is revised; every earlier revision stays readable exactly as it was |
| Industries | listed with counts the service gathers in one pass, each with its own register |
| Schemas | listed, read whole, declared and revised through a builder for fields and constraints |
| Export | the current view, written to a spreadsheet in the browser |
| Snapshots | the newest thousand assumptions preserved in **this browser only** |
| Themes | dark and light, every colour a token in `plugins/vuetify.ts` |

## What is not here, and why

- **Projects.** The design has an industry containing projects containing assumptions. There is no project
  resource, so the navigation is industry to assumption.
- **Editing and removal.** A schema is changed by revising it. An assumption cannot be changed once created,
  and nothing is ever erased - the removal flag exists and is indexed, but no endpoint sets it.
- **Files.** The design attaches files to assumptions. There is no storage endpoint, so no dropzone is shown.
- **Validation records.** `validation_responsible_parties` is a field on an assumption; validations are not a
  resource.
- **Snapshots are local, and bounded.** They are kept in the browser's own storage, which is a few megabytes,
  so a snapshot preserves the newest thousand assumptions rather than the register. `utils/snapshots.ts` is
  the only thing that has to change when the service grows a snapshot of its own.

## Layout

```
backend/src/truth_service/
  api/            one module per resource, plus the shared window and the health endpoint
  models/         the payloads, in and out
  documents.py    the persistence shape, and the blob a search is answered out of
  query/          the table's question translated into the store's
  repositories/   the only layer that talks to the store, and the only place indexes are declared
  services/       the register's own rules, including the tolerant reader a scheme is read with

frontend/src/
  requests/       one module per resource
  models/         the payloads, exactly as the API shapes them
  utils/          scheme reading, column generation, constraints, export, snapshots
  composables/    the vocabulary held once, and the table bound to the service
  components/     the table, its panel, the wizards and the builders
  pages/          file-based routes
```

Everything not specific to this product - the cell renderers, the filters, the dynamic form inputs, the
formatting, the theme switch - comes from `@truth-platform/core-ui` in `libraries/`, which this client shares
with the Skyscanner inventory. The service shares `libraries/skyscanner_common` and
`libraries/skyscanner_models` with the Skyscanner services, which is where its document store access,
settings, errors and filter payloads come from.
