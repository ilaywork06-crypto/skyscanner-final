# Skyscanner

Skyscanner is the inventory of the events that produce files - every event, the entities nested inside it
(telemetries, logs, video) and every raw, parsed and additional file that belongs to them.

Three FastAPI services and a Vue 3 web client, built on the libraries in `libraries/` at the root of the
repository and sharing them with Truth. Everything runs behind one nginx container with a single
`docker compose up`.

---

## Layout

```
skyscanner/
├── docker/                       every service, the document store, the bucket and the mail relay
├── services/
│   ├── events_service/           the inventory, the entities, the dynamic schema, the templates, the exports
│   ├── storage_service/          uploads, downloads and temporary links for every stored file
│   └── notification_service/     turns the pending notifications of the inventory into mails
├── frontend/                     Vue 3, Vuetify, TypeScript, unplugin-vue-router, AG Grid
├── docs/                         the user guide
└── pictures/                     the designs the client was built to
```

and the libraries it is built on, which live at the root of the repository and are shared with Truth:

```
libraries/
├── skyscanner_models/            the API models - pydantic and nothing else, shared by every service
├── skyscanner_common/            settings, logging, mongo access, object storage, identity, error handling
├── ag_grid_lib/                  schema introspection, column generation and query translation for AG Grid
├── ag-grid-ts/                   the client half of the grid library - parsing, grid setup, reactive controller
└── core-ui/                      the shared Vue components and formatting rules both clients render with
```

Every service is split into an **api**, a **service** and a **repository** layer. Only the repository layer
talks to the document store, and only the storage service talks to the bucket.

---

## Running the whole thing

```bash
cd skyscanner/docker
docker compose up --build
```

Every value has a default, so there is nothing to configure to start it. An `.env` in that directory,
beside the compose file, overrides any of them.

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

An empty system needs four things before the first event can be uploaded, and each of them is declared on the
page named after it: an **industry** on Industries, a **platform** on Platforms, at least one **event type**
and - if the entities of the event should be grouped - an **entity type** on Types. Everything an event or an
entity is *asked* is declared on Schema, whether it is asked of the event itself or of the entities inside it.

That split is the whole of it: **Types** holds the shapes an event and an entity take, **Schema** holds the
questions they answer, **Platforms** and **Industries** hold the two vocabularies an event is filed under. The
event fields used to be declared on the Types page and the platforms used to be a third kind of type there,
which put three unrelated things behind one selector on a page named after only one of them.

The same declarations are reachable over the API, and every one of them names the industries it belongs to -
an empty list means every industry:

```bash
curl -X POST localhost:8080/api/industries   -H 'Content-Type: application/json' \
     -d '{"key": "robotics", "name": "Robotics", "modules": ["arm", "gripper"]}'
curl -X POST localhost:8080/api/platforms    -H 'Content-Type: application/json' \
     -d '{"key": "rig_a", "name": "Rig A", "industries": ["robotics"]}'
curl -X POST localhost:8080/api/types/events -H 'Content-Type: application/json' \
     -d '{"key": "bench_run", "name": "Bench Run", "industries": ["robotics"], "fields": ["event_date"]}'
```

`POST /api/types/platforms` still answers and is marked deprecated, because it is what the README, the client
and anything anybody scripted have called for as long as the service has existed.

### Running the pieces by hand

```bash
uv sync --all-packages
uv run uvicorn events_service.main:create_app       --factory --port 8000
uv run uvicorn storage_service.main:create_app      --factory --port 8001
uv run uvicorn notification_service.main:create_app --factory --port 8002

npm install
npm run dev                             # http://localhost:5173, proxies /api to the services
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

### Filtering by picking rather than by typing

A column whose values are a vocabulary somebody declared - a platform, an industry, an event type, a status,
an experiment result, an entity type, a module, or any field declared as an `enum` - carries that vocabulary
with its definition, as `filterOptions`, and declares `SetColumnFilter` instead of the text filter its type
would otherwise get. The community build of AG Grid ships no such filter, so the web client registers one
under that name in `useColumnFilters`, exactly as it registers the cell renderers. Remembering that *Rig A*
is stored as `rig_a` is not something the table asks of anybody any more.

The few of those a reader narrows by every day are also marked `quickFilter`, and the row of pills under the
toolbar is built out of them. A pill writes its pick into the filter of its own column rather than beside it,
which is what makes one pick show up as a chip under the toolbar, come off from there, and travel into a
saved view like any filter typed into a header.

Adding a value to a vocabulary is declaring it on the **Types**, **Industries** or **Schema** page. Nothing
in the web client lists a platform or a status by hand.

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

An **event field** is declared on the **Schema** page under the *Event fields* section, with a name, a type,
its allowed values if it is an enum, and the industry it belongs to - beside the fields of the entities, which
are declared the same way and were always declared there. An event type then names the ones it asks for, and
the create wizard renders exactly those under **Additional Event Attributes** - beside the built in fields of
`OptionalEventField`, which stay the fixed vocabulary the service itself understands. A new question about an
event therefore costs a declaration rather than a change to that enumeration and to every form that reads it:

```bash
curl -X POST localhost:8080/api/fields -H 'Content-Type: application/json' \
     -d '{"key": "mission_phase", "name": "Mission Phase", "type": "enum", "scope": "event",
          "metadata": {"options": ["ascent", "cruise", "descent"]}}'
curl -X POST localhost:8080/api/types/events -H 'Content-Type: application/json' \
     -d '{"key": "bench_run", "name": "Bench Run", "fields": ["event_date"],
          "custom_fields": ["mission_phase"]}'
```

---

## Changing a declaration after it exists

Every declaration can be edited from the page it lives on - the label, the description, the industries it
serves, the fields an event type asks for, the icon of an entity type. All of that is an ordinary `PATCH`.

The **key** is the one that is not ordinary, and it is worth saying why. A key is not an identifier here: an
event stores the keys of the types it was filed under, the platforms it ran on and the fields it answered
rather than pointing at the declarations. Changing one is therefore a write across the store, and doing
nothing about that would leave half the documents naming something that no longer exists.

The alternative would be to keep the old key as an alias and let both spellings resolve. That is deliberately
not what happens, because it is the exact thing this system was built to stop: the whole point of refusing an
undeclared key is that two people describing one thing write one field, and an alias is a supported way to
have two live spellings of it. So a rename is carried through instead, by `services/rename_service.py`:

| Renaming | Rewrites |
| --- | --- |
| An event type | `events.event_type_keys`, the subscriptions following it, the saved views filtering by it |
| A platform | `events.platforms`, the saved views filtering by it |
| An entity type | `objects.object_type_key`, `entity_counts`, the fields scoped to it, the saved views |
| A field | `metadata[].key` **and** `data.<key>` on every event or entity, the types asking for it, the views |

Two things make that safe to offer rather than merely possible. The key is locked in the form until it is
deliberately unlocked, so it cannot be changed by tabbing through a dialog; and unlocking it reads
`GET /api/{types,platforms,fields}/{id}/rename?key=…`, which counts exactly what would move and touches
nothing, so the dialog can say *"saving rewrites 142 events, 3 templates"* before anybody commits to it.
Every rewrite starts from a query matching only the documents that carry the old key, so renaming something
nobody ever used costs one query per collection and writes nothing.

A changed **label** is carried the same way and for the same reason. An event stores the name of its type
beside the reference to it so a row reads without a lookup, so a label changed on the declaration alone was a
label the table went on showing the old spelling of forever.

---

## Reaching the page of an event

The page of an event shows everything the event says about itself: the built in facts, the information, the
files, the entities - and, under **Additional Event Attributes**, the fields its industry declared, the ones
its type asked for and anything a script left on it. The expanded row of the inventory had shown those all
along while the page dedicated to a single event showed the built in facts and stopped, so the one surface
about one event was the one place its own answers could not be read. Both surfaces now render the identical
value through the identical generated column. The attributes of an entity are under the arrow on its row.

Every event is a page of its own. The number and the brief have always led there, but nothing on a row said
so, and a reader who never happened to click one of those two cells never found the page at all. Every row
therefore ends in the arrow that every list uses to mean *there is more of this behind here*, pinned to the
end of the row where the eye lands after reading it, and it is a real link - it opens in a new tab, it can be
copied, and it leads exactly where the other two do. It is furniture of the table rather than a value of it,
so the **Columns** menu does not offer to hide it.

---

## Reading what is on the screen

Two things a reader does with a value constantly, and could not do here at all.

**Selecting it.** Almost nothing in the system could be picked up with the pointer, and none of that was a
decision anybody made - the component libraries switch selection off on the things they expect to be clicked,
and between them they covered most of what is actually read. AG Grid puts `ag-unselectable` on the inventory
unless it is told otherwise, which is answered in the grid options with `enableCellTextSelection`; Vuetify
puts `user-select: none` on every `v-table`, which is the listing on Schema, Types, Platforms and Industries,
and that is answered in `App.vue`. The controls stay unselectable, so dragging across a button presses it
rather than highlighting the word on it.

**Following it.** Nothing ever asked for a field to hold a link and people put them in anyway - a ticket, a
dashboard, a folder on a share. Stored as a string they were shown as a string, so the one thing a reader
wanted to do with the value was the one thing it would not do. `libraries/core-ui/src/utils/links.ts` reads
the addresses back out of any value and `UiLinkedText` paints them as real anchors, in the table, in the
attribute tables, in the value viewer and in the information of an event.

Two things it is careful about. The page always shows the characters somebody typed rather than markup built
out of them; and an address is offered only when the browser's own parser says it is `http`, `https` or
`mailto`, so a value reading `javascript:...` is text like any other. A cell that had to window a long value
shows characters rather than a link, because half an address is not one - the viewer behind the expand
affordance holds the whole value and reads the addresses out of that.

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
`/api/platforms`, `/api/industries`, `/api/templates`, `/api/subscriptions` and
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

A view saved before a column existed does not hide that column: the arrangement it names is kept and anything
it has never heard of joins the end of it showing whatever its declaration says it should. Otherwise every
column added to the system would be invisible to everybody who works out of a saved view.

Everything narrowing the table is one and the same restriction whether it was typed into a column header or
picked from a quick filter above it, because a quick filter writes into the filter of its own column. A view
therefore saves and restores both, and reopening one lights its pills back up.

**Which columns are shown is state, not declaration.** Handing AG Grid a new set of column definitions makes
it build its columns again from scratch, and a column built again is a column whose filter was thrown away -
so a table that rebuilt its definitions every time a box was ticked in the **Columns** menu was a table that
silently dropped every filter it was running, saved views included. `columnDefs` therefore changes only when
the generated configuration does, and visibility is written into the running grid with `applyColumnState`.

**Default view** is always the last entry of the list: the table exactly as the backend generates it, with
every column at its declared place, nothing filtered and nothing searched. Returning to it throws away
whatever was arranged since, so a view with unsaved arrangements is asked about first and can be kept under a
name of its own - the same question, and the same way out, that switching between two templates asks.

---

## Uploading an event

The two steps of the create wizard map onto the API like this:

1. **Data** - event type, industry, the platforms it ran on, status, the **event brief** the event is listed
   under and the files of the event itself. The files go to `POST /api/storage/artifacts` first and come back
   as artifact records. The brief is stored as the `name` of the event and is optional; `event_id` is minted
   by the service and is never part of the payload. The rest of the built in fields - the reference
   id, the date, the experiment result and the free text - are only asked for when the chosen **event type**
   declares them, which is what keeps an experiment result off an event that is not an experiment, and the
   **event fields** that type names are asked for underneath them.
2. **Add Entities** - any number of entities, each with its own type, its own dynamic fields, its own
   additional data and its own raw files.

What an event is asked for beyond the built in fields is decided by its **event type** rather than by its
industry, and the entities underneath it are shaped by the dynamic schema of their own entity type, which an
industry does vary along with its modules.

`POST /api/events` then stores the whole thing as one document.

### The brief an event is listed under

The brief is the short line the inventory shows, searches and recognises an event by, and asking for it was
the one thing standing between a watchdog - or a user in a hurry - and an uploaded event. Leaving it out is
therefore allowed, and `events_service.services.brief` writes one out of what the event already says about
itself, in a fixed order so that two events written a month apart read alike:

```
<event types> · <platforms> · <industry> · <date> [· via <upload source>] · #<event number>
Ferry flight · rig_a + rig_b · robotics · 27 Aug 2026 · #142
Experiment · falcon · aviation · 27 Aug 2026 · via watchdog · #7
```

The date is the date of the activity when the event type asks for one and the moment of the upload otherwise;
the running number closes it, so two events that agree on everything else are still told apart; and the upload
source is named only when it was not a person filling the wizard in. Past three platforms the rest are counted
rather than named. A generated brief is an ordinary value: the create wizard shows the one it is about to
write underneath the empty field, and the event page edits it like anything else. Clearing it on an edit
writes the convention again rather than storing an event with no brief at all.

### Large files, many files

Nothing about an upload is held in memory as a whole any more. The web layer hands the storage service the
*way to read* an upload rather than its bytes, and `ObjectStorageClient.upload_stream` decides what to do
with it: below `S3_MULTIPART_THRESHOLD_BYTES` it is one ordinary write, and above it the bucket takes it as a
**multipart upload** - part by part, `S3_MULTIPART_CONCURRENCY` parts of one file in the air at once, so the
memory a file costs is that many parts rather than the size of the file. A part that fails aborts the upload
instead of leaving the pieces of half a file in the bucket. Archives are built the same way: an entry is
streamed out of the bucket into the zip rather than downloaded whole first.

The other half of the wait is the round trips. `S3_UPLOAD_CONCURRENCY` files of one request are written at the
same time, and the web client no longer sends every picked file in a single request: it splits a pick into
batches, runs several of them side by side, and gives any file past sixteen megabytes a request of its own -
a batch is only ever as quick as the largest file in it.

### The file the request cannot survive

All of the above still assumes one request per file, and past a certain size that assumption is the problem
rather than a detail of it. A request carrying forty gigabytes has to survive from the first byte to the
last, and a connection that drops thirty gigabytes in costs all thirty - there is nothing in the shape of
that request that could ever have made it cost less.

Past **64 MiB** the browser drives the upload itself instead, one part per request:

```
POST   /api/storage/artifacts/uploads              -> upload_id, path, part_size
PUT    /api/storage/artifacts/uploads/{id}/parts/1    the bytes, as the raw body
PUT    /api/storage/artifacts/uploads/{id}/parts/2    ...four at a time, each retried on its own
GET    /api/storage/artifacts/uploads/{id}            what the bucket is already holding
POST   /api/storage/artifacts/uploads/{id}/complete -> the artifact record
DELETE /api/storage/artifacts/uploads/{id}            give it up, and the parts leave the bucket
```

Three things follow from that shape. A part that fails is retried on its own rather than costing the file. An
upload that is interrupted altogether is **resumed**: the browser remembers the open upload under
`skyscanner.uploads.open`, and picking the same file again reads what actually landed - from the bucket,
which is the only honest account of it - and sends only the rest. And nginx never sees a request larger than
one part, so `client_max_body_size` stops being a ceiling on how large a file the system accepts.

Nothing about a half finished upload is remembered on the service side. The bucket already remembers the
parts, so a second store of pending uploads - kept in step with it, swept when a browser never comes back -
would be a second source of truth about the same thing. What the service is not told, it cannot get wrong.

A pick large enough to be written this way is shown as the wait it is: the three dialogs that upload carry a
progress bar reading the bytes that have actually gone, added up across every pick running side by side.

---

### The alphabet a file is named in

A file is named in the alphabet its owner works in, and none of that is a reason to rename it: a name written
in Hebrew is stored, listed, archived and downloaded in Hebrew. `safe_path_segment` replaces only what would
change where a file ends up or break the tool reading it - the separators, the control characters and the two
edges a file system trims by itself - and normalises the rest so that two spellings of one letter cannot
become two different files. Three places used to lose such a name and no longer do:

- **The key in the bucket.** Keys are UTF-8 and always were; the name goes in as it was written.
- **The attributes stored beside the object.** Those travel as headers, which carry ASCII and nothing else,
  so `ascii_metadata_value` percent encodes them rather than replacing the letters the bucket cannot spell.
- **The header of a download and the entries of an archive.** Both carry the real name - the download in the
  encoded form of RFC 5987 beside a plain fallback, the archive in the UTF-8 the format has carried for two
  decades. A download is also offered under the name the file was picked with rather than under its key,
  which is minted per upload so that two uploads can never overwrite one another.

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

The entity table shows those file sets as two columns of their own - **RAW FILES** and **PARSED FILES**, the
products of the parsing folded in with the parsed ones - rather than as one column of folders that had to be
opened before it said anything. The single `files` column they replaced is still generated, hidden, so that a
saved view or a script naming it finds a column rather than nothing, and every row still carries the whole
list under that key.

Raw first, parsed later is the normal flow: upload an entity with its raw files, and once the parsing products
exist, open the event, edit the entity and drop the parsed files in. The status follows the files rather than
the caller: an entity that carries parsed files is stored as `parsed`, and a request that claims `parsed`
without a single parsed file is refused. `POST /api/events`, `POST /api/events/{id}/entities` and
`PATCH /api/events/{id}/entities/{entity_id}` all read it the same way.

---

## Opening a file without downloading it

A stored file is read through `GET /api/storage/artifacts/content`, and that endpoint honours a `Range`,
answering with the `206` and the `Content-Range` the protocol asks for. `proxy_buffering` is off for the
storage service and the header is passed through, so a window asked for is a window that arrives.

That is what lets the viewer open a sheet nobody could open before. A text shaped file past **2 MiB** used to
be refused outright - a reader with a four gigabyte telemetry csv was told to download it and find something
else - and it is now read a **1 MiB** window at a time. The heading is read once out of the beginning of the
file and kept, so the columns stay named ten gigabytes in; a window taken by byte offset opens and closes
mid row, so both partial rows are dropped rather than shown with their first or last columns missing; and the
controls under the pane move through the file, including to its end, which is the place a reader of a very
large file could never reach at all.

A **workbook** is the one shape still capped, and for a reason rather than by oversight: it is compressed and
its rows are not laid out in the order the file stores them, so there is no window of the bytes that answers
to a window of the rows.

| Setting | Default | What it decides |
| --- | --- | --- |
| `S3_MULTIPART_THRESHOLD_BYTES` | 16 MiB | Past this a file is written as a multipart upload |
| `S3_MULTIPART_CHUNK_BYTES` | 8 MiB | How much of a file one part carries, floored at the 5 MiB of the protocol |
| `S3_MULTIPART_CONCURRENCY` | 4 | How many parts of one file travel at once |
| `S3_UPLOAD_CONCURRENCY` | 6 | How many files of one request are written at once |

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
roles named in `AUTH_ANONYMOUS_ROLES`. `skyscanner/frontend/nginx.conf` is where the real proxy plugs in.

---

## Notifications

The events service never sends a mail. It writes a row into `notification_outbox`, and the notification service
polls that collection, resolves the subscriptions that match the industry, the event type or the single event, and
hands the message to the mail relay. Subscriptions live on the **Subscriptions** page and on the bell of an
event page.

Both of those are **hidden from the web client for now**: subscriptions are an advanced feature that has not been
opened to users yet. The switch is a single constant, `SUBSCRIPTIONS_ENABLED` in `skyscanner/frontend/src/features.ts`; while
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

The client is opened on whatever browser a given workstation happens to carry, and the floor it is built for
is named in `skyscanner/frontend/vite.config.ts`. Three separate things have to be answered for that floor to
mean anything, because the bundler only ever answers the first of them.

**Syntax.** The bundler rewrites it, which is what the target in the build configuration does.

**The stylesheet the table generates.** It carries two things an older browser cannot read, one version of
Chrome apart, and `libraries/ag-grid-ts/src/compatibility.ts` rewrites both. The sheets are watched rather
than swept once, and the two questions are asked separately - a browser on Chrome 111 needs one of them and
not the other.

- **`color-mix()`** reached Chrome 111. Below it every derived border, hover and header separator is dropped
  as invalid, which is not a slightly different table but a table with no borders and unreadable headers.
- **Nested rules** reached Chrome 112. The grid writes about a hundred and forty of its rules inside other
  rules - `.ag-header-cell-resize { ...; &:after { ... } }` is the shape nearly all of them take - and below
  that version each one is a parse error the browser throws away, taking every resize handle, checkbox tick,
  sort arrow, hovered row and focus ring with it. They are hoisted out to stand on their own, with the
  nesting selector replaced by whatever the rule around it selected. `npm run test --workspace
  @truth-platform/ag-grid-ts` checks that against the stylesheets AG Grid actually ships: every rule is
  flattened and then compared, declaration by declaration and in order, with what a CSS parser resolves from
  the nested original.

**The methods the code calls.** This is the one the bundler says nothing about, because a missing method is
not a compile time fact: `Array.prototype.findLast` arrived in Chrome 97 and is emitted exactly as written.
The code path is rarely ours - it belongs to the component libraries, which are built against a far more
recent baseline than this client is opened on - and it fails where a user can least explain it, as a ripple
that kills a click. `libraries/core-ui/src/utils/runtime.ts` installs the handful that matter, each only
where the browser lacks it, and `main.ts` calls it before the application is created.

One of those was our own and was broken on *every* browser: private saved views were minted with
`crypto.randomUUID`, which is offered only in a secure context, so on a deployment reached as
`http://<machine>:8080` from another desk - which is how this system is actually opened - saving a view threw
on the newest Chrome there is. It is used where it exists and worked out by hand where it is not.

Almost none of those mixes name a colour outright. The grid writes them over its own custom properties -
`color-mix(in srgb, transparent, var(--ag-active-color) 12%)` is the shape nearly all of them take - so the
properties are read out of the same stylesheets first and an operand naming one is expanded before the mix
over it is worked out. Of the thirty seven distinct mixes the shipped stylesheets contain, thirty seven
resolve; reading only literal colours resolved sixteen, and left every border and every hover on the floor.

The channels are weighted by their own alpha before being mixed and divided back out afterwards, because that
is how the function being replaced is defined. Skipping it turns a hover written over `transparent` into a
dark smear rather than a tint - and a hover written over `transparent` is what nearly all of them are.

The rewrite is not a single sweep. The grid writes that stylesheet again whenever the theme it is handed
changes, and the sheet it writes has its mixes unresolved, so switching between dark and light would have
taken the borders back off the table until the page was reloaded. The injected sheets are watched instead,
and every rewrite the grid makes is answered - the watch exists only on the browsers that need it, sees the
head alone rather than the thousands of mutations a table redraw makes, and drops the records of its own
writing so that it does not answer itself.

---

## Checks

```bash
uv run mypy -p skyscanner_models -p skyscanner_common -p ag_grid_lib \
            -p events_service -p storage_service -p notification_service
uv run pylint skyscanner_models skyscanner_common ag_grid_lib \
              events_service storage_service notification_service

npm run type-check --workspace skyscanner/frontend
npm run lint --workspace skyscanner/frontend

npm run test --workspace @truth-platform/ag-grid-ts
```

Both Python checks are clean, and the web client passes `vue-tsc` and `eslint` with zero warnings.

The one test suite in the repository covers the compatibility shim, because it is the piece whose failure is
both invisible here and total on the machines it exists for: it reads the stylesheets AG Grid actually ships
out of the installed package, flattens every nested rule, and compares the result declaration by declaration
and in order against what a CSS parser resolves from the nested original.
