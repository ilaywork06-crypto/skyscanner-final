# Truth

A register of working assumptions - the conditions, figures and behaviours a project is planned on - filed by
industry and declared by schemas.

This directory holds the web client only. The API it reads is the FastAPI service described below.

## Running it

```bash
npm install                 # from the repository root
npm run dev:truth           # http://localhost:5174
```

The client proxies `/api` to `http://localhost:8000`, which `TRUTH_API_URL` overrides.

| Variable | What it is for |
| --- | --- |
| `TRUTH_API_URL` | Where the assumptions API is reached, at build and dev time. |
| `VITE_API_BASE_URL` | The address the browser sends its own requests to. Defaults to `/api`. |
| `VITE_DEFAULT_CREATOR` | Who the client creates things as before anybody sets a name. |

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
about the keys. `utils/scheme.ts` reads generously - a field named `key`, `name` or `field` is the same field,
`list[str]` and `string[]` both mean a list of text, and a schema written as `{"berth_count": "int"}` is
understood - and writes strictly, so a schema built here reads back exactly as it was declared.

### Columns are generated from the database, not written down

No endpoint generates column definitions, so the generation that would run in the backend runs in
`utils/columns.ts` - but off the same source it would have run off there. Nothing in that file names an
attribute of an assumption. The fixed columns are the fields the API itself returns on every assumption, and
every other column is read out of the schemas the register holds. Declaring a schema with a new attribute
gives the table a new column, with the renderer and the filter its declared type asks for.

### Two quirks of the API the client works around

- `POST /schema` reads its constraints under `constrains`; every read hands them back under `constraints`.
  Both are accepted on the way in and the former is what is sent - see `models/scheme.ts`.
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
