# Truth

A register of working assumptions - the conditions, figures and behaviours a project is planned on - filed by
industry and declared by schemas.

```
truth/
├── frontend/         the Vue 3 web client, which is all of Truth that lives here
├── mock-api.py       an in-memory stand-in for your API, for working on the client alone
└── docker/           the client and the stand-in, and the client in front of your own API
```

**There is no service in this repository.** The assumptions API is yours and runs wherever you run it; this
is the client that talks to it. The client is written against exactly the endpoints that API offers and no
others, which is what the whole of "How it works with your API" below is about.

The shared components both this client and the Skyscanner one render with live in `libraries/` at the root of
the repository, not here.

## Running it

### The client and the stand-in, which is one command

```bash
cd truth/docker
docker compose up --build          # then open http://<this machine>:8090
```

Two containers and nothing else. `mock-api.py` answers exactly the endpoints your API offers, in exactly the
shapes it answers them in - including its two quirks - and holds its register in memory, so it is the same
on every run and nothing written through it survives a restart. That is what makes it useful: a register
that is always the same, for working on the client without needing your service up.

### In front of your API

```bash
cd truth/docker
TRUTH_API_URL=http://<where your API answers>/ docker compose -f docker-compose.frontend.yml up --build
```

One container: nginx serving the built client and forwarding `/api` on to your service. The client is
published on **port 8090 of every interface**, so anybody on the network opens `http://<this machine>:8090`
and reaches both through that one port - there is no second address to hand out and no cross-origin request
to allow.

The trailing slash on `TRUTH_API_URL` matters: it is what strips the `/api` the client prefixes, so that
`/api/assumption` arrives at your service as `/assumption`. `host.docker.internal` reaches a service running
on this machine outside Docker; a name or an address reaches one anywhere else. `TRUTH_PORT` moves the port,
and `127.0.0.1:8090:80` keeps it to this machine.

### Without Docker, for developing

```bash
npm install                # from the repository root
python3 truth/mock-api.py  # or point TRUTH_API_URL at your own service instead
npm run dev:truth          # http://localhost:5174
```

| Variable | What it is for |
| --- | --- |
| `TRUTH_API_URL` | Where your assumptions API is reached, at build and dev time. |
| `TRUTH_ALLOWED_HOSTS` | Extra names the dev server may be reached by. |
| `VITE_API_BASE_URL` | The address the browser sends its own requests to. Defaults to `/api`. |
| `VITE_DEFAULT_CREATOR` | Who the client creates things as before anybody sets a name. |

**Reaching the dev server by name.** It refuses a request whose `Host` is a name it was not told about -
that is what stops a page on the internet from pointing its own domain at your machine and reading the
source through a visitor's browser. An address is never a name, so `http://10.0.0.5:5174` always works; it
is `http://moon:5174` that gets turned away. Name the others with `TRUTH_ALLOWED_HOSTS=moon,truth.lan`, or
`all` to give the protection up entirely. The Docker setups have none of this to configure.

## How it works with your API

Your API offers these, and the client uses only these:

| | |
| --- | --- |
| `GET /industry` `POST /industry` | listed with `offset`/`limit`, answered as a bare array |
| `GET /industry/{id}` `GET /industry/name/{name}` | one industry |
| `GET /schema` `POST /schema` | listed; declared with a scheme of fields |
| `GET /schema/{id}` `GET /schema/{id}/latest` `GET /schema/name/{name}` | one schema, whole |
| `POST /schema/{id}/revisions` `POST /schema/name/{name}/revisions` | a new revision of a declaration |
| `GET /assumption` `POST /assumption` | listed; created against one or more schemas |
| `GET /assumption/{id}` `GET /assumption/{id}/latest` | one assumption, whole |

There is no `PATCH` and no `DELETE` anywhere, no search, no filter and no ordering, and no listing says how
many rows there are in total. Three things follow from that, and they are the shape of the whole client:

**The register is read whole and questioned in the browser.** Every listing is asked for repeatedly, a page
at a time, until one comes back short - the only signal those listings give that they have reached the end.
The search, the filters, the sorting and the paging then all run over what was read, because there is no
endpoint to ask any of them of.

**A listed assumption is not a whole one.** `GET /assumption` carries neither the values of an assumption nor
the industries it belongs to; only `/latest` does. So every listed assumption is read again on its own, six
at a time, and the table is usable while that happens rather than after it - the rows appear from the
listing and gain their values and their industries as the readings land. There is no endpoint that would
make this fewer requests.

**A scheme is read generously and written strictly.** The API types a scheme as `list[dict[str, JsonValue]]`
and promises nothing about the keys, so the reader understands a field that named itself `field` rather than
`key`, a type written as `list[str]` or `string[]`, and a whole field written as `{"speed": "number"}`.
Everything written back goes out in exactly the shape the service expects.

Every field goes out carrying the five keys every field must have - `key`, `display_name`, `type`, `required`
and `array` - and the flags go out as real booleans whether or not anybody ticked them, because a missing
flag is not the same thing as a false one. Past those, a field carries what its own kind calls for: `options`
for either enumeration, and whichever of `min`, `max` and `step` were actually set for a confined number or
float. **Anything else the stored field carried is carried back out untouched**, so revising a schema through
this client cannot quietly delete a key it does not know about.

| Kind | Written as | And carries |
| --- | --- | --- |
| Text | `string` | |
| Yes / no | `boolean` | |
| Whole number | `confined_number` | `min`, `max`, `step`, each when set |
| Decimal number | `confined_float` | `min`, `max`, `step`, each when set |
| One of a list | `enum` | `options` |
| One of a list, ultra | `ultra_enum` | `options` |
| Date | `date` | |
| Several fields in one | `multi_field` | whatever it was declared with |

The last two are read, shown and written back exactly as they were found, but the builder does not offer
them when a new field is declared: what they carry beyond the five keys is not written down here yet, so a
picker that offered them would let somebody declare one that is missing it. A field that already is one
keeps its kind in the picker, so revising the schema around it cannot turn it into a line of text.

Two quirks of the API the client works around: `POST /schema` takes constraints under `constrains` but
answers with `constraints`; and it takes industries as numeric identifiers that no endpoint hands out, so an
empty list is sent and the schema is declared globally.

## What is here

| | |
| --- | --- |
| Industries | listed with their counts, each with its own register - and the only way into one |
| Register table | dynamic columns, search, per-column filters, quick filters, sorting and paging, all in the browser |
| Whole values | a cell shows all of what it holds - the row grows for it rather than the value being cut short |
| Row panels | the schema-declared attributes of a row, its industries, and a list of its validations that narrows the register to any of them |
| Create an assumption | the two-step wizard, checked against the declarations on the way in |
| Duplicate an assumption | the whole assumption prefilled into that wizard, from its own page |
| Revisions | a declaration is never edited, it is revised; every earlier revision stays readable as it was |
| Schemas | listed, read whole, declared and revised through a builder for fields |
| Export | the view as a spreadsheet, or the register as a bundle |
| Import | a bundle, restored |
| Hebrew | the whole interface in English or Hebrew, laid out in the direction the language runs |
| Mixed text | every value reads the way it was written, whichever language the page is in |
| Themes | dark and light, every colour a token in `plugins/vuetify.ts` |

### Export, and import

There are two exports, because they answer two different questions.

**The spreadsheet** is for a person. It carries the columns that were on screen, in the order they were on
screen, with every value flattened into the one cell a sheet holds it in. That flattening is exactly what
makes it something to read rather than something to restore: a flattened value has lost whether it was a
number or the word for one, a hidden column has lost its values entirely, and a renamed header no longer
says which key it came from.

**The bundle** is the other thing. It carries the register in the shapes the API itself creates things in -
the industries, the schemas with their declarations exactly as the service stored them, and the assumptions
with their values - so restoring one is the same sequence of writes a person would have made by hand.
Everything inside is named rather than identified, because the identifiers of one register mean nothing in
another and the API accepts a name wherever it accepts an identifier. A bundle taken from one register
therefore restores into a second one that has never seen a single one of its uuids.

Importing reads a bundle and writes what is not already there, in three passes - industries, then schemas,
then assumptions - because an assumption names its schemas and its industries by name and a name that has
not been created yet is a name the service refuses. An assumption whose name and text are already in the
register is left alone, which is what makes a restore that was interrupted safe to run again. One write that
fails does not stop the rest; the dialog names every one that could not be written.

The API has no file storage, so a bundle carries no files. Skyscanner's does, and its bundle is a zip with
the files inside it.

### Hebrew

The switch is in the header, and the whole interface follows it - the words, and the direction they run in.

Three separate things have to be moved for a page to actually mirror, and `useLanguage` in the shared library
is the one thing that knows about all three: the document's own `dir`, which is what makes every CSS logical
property in the layouts mean the other thing; Vuetify's locale, because Vuetify mirrors its own components
off that rather than off the document; and AG Grid, which reads its direction once when it builds itself and
never looks again - so the table is keyed on the language and rebuilt rather than told.

The words come out of dictionaries. The shared library ships the vocabulary of the table itself and this
client adds the vocabulary of the register, and a phrase named by both is this client's - which is how the
bar under the table counts assumptions rather than rows. A phrase with no Hebrew falls back to its English,
so a dictionary that is behind leaves a few English words on a Hebrew page rather than holes in it.

### Text that is in both languages at once

A register written by people who work in two languages holds values that are in two languages - a Hebrew
note naming an English part number, an English assumption quoting a Hebrew requirement. Left to the page,
each of those reads in the direction the *page* runs, which turns the other language backwards: an English
identifier inside a Hebrew line arrives at the wrong end of it, and a bracket or a full stop lands on the
wrong side.

So no value takes its direction from the page. Every cell, chip, attribute and viewer is `unicode-bidi:
plaintext` - `dir="auto"` written as a rule rather than an attribute - which gives each value its own
direction, taken from the first letter in it that has one. A Hebrew value reads right to left inside an
English table, an English one reads left to right inside a Hebrew table, and a value mixing the two keeps
each run the way it was typed. The table itself still turns around with the language; the values inside it
do not turn around with the table.

**What is deliberately not translated is your data.** The names of the industries, the names of the schemas
and the attributes a schema declares are written by the people using the register, in whichever language they
chose, and inventing words for those would be worse than leaving them alone. The one exception is a declared
attribute, which can carry a Hebrew name of its own: write `display_name_he` beside its `display_name` -
`label_he`, `name_he` and plain `he` are read too - and the column is headed in Hebrew on a Hebrew page and
in its declared name otherwise. The schema builder offers that field.

## What is not here, and why

- **Projects.** The design has an industry containing projects containing assumptions. There is no project
  resource, so the navigation is industry to assumption.
- **A register of every industry at once.** An assumption is always read under the industry it was filed
  under, so a table of all of them together answered a question nobody was asking - and cost a reading of
  the whole register to draw.
- **Editing and removal.** A schema is changed by revising it. An assumption cannot be changed once created,
  and nothing is ever erased - the removal flag exists but no endpoint sets it.
- **Files.** The design attaches files to assumptions. There is no storage endpoint, so no dropzone is shown
  and a bundle carries none.
- **Validation records.** `validation_responsible_parties` is a field on an assumption; validations are not a
  resource.

## Layout

```
frontend/src/
  requests/       one module per resource, and the pager that reads a whole listing out of a windowed one
  models/         the payloads, exactly as the API shapes them
  utils/          scheme reading, column generation, constraints, the query the table runs, export, bundles,
                  and this client's half of the dictionary
  composables/    the register held once, and the table bound to it
  components/     the table, its panel, the wizards, the builders and the import dialog
  pages/          file-based routes
```

Everything not specific to this product - the cell renderers, the filters, the dynamic form inputs, the
formatting, the theme switch, the language switch - comes from `@truth-platform/core-ui` in `libraries/`,
which this client shares with the Skyscanner inventory.
