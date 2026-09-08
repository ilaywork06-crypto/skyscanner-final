# Two systems, one repository

**[Skyscanner](skyscanner/README.md)** is the inventory of the events that produce files - every event, the
entities nested inside it, and every raw, parsed and additional file that belongs to them.

**[Truth](truth/README.md)** is the register of working assumptions - the conditions, figures and behaviours
a project is planned on, filed by industry and declared by schemas.

They are separate systems with separate stores and separate deployments. They are in one repository because
they are built out of the same libraries, and a shared component that lives in two repositories is a shared
component that has already started to diverge.

```
libraries/                 built by both, owned by neither
├── core-ui/               the Vue components, the formatting and the theme both clients render with
├── ag-grid-ts/            the client half of the grid - parsing, grid setup, the reactive controller
├── ag_grid_lib/           the service half - schema introspection, column generation, query translation
├── skyscanner_common/     settings, logging, document store access, object storage, identity, errors
└── skyscanner_models/     the API models, pydantic and nothing else

skyscanner/                the inventory
├── services/              events, storage, notifications
├── frontend/              the client
└── docker/                every service, the document store, the bucket and the mail relay

truth/                     the register
├── backend/               the register service
├── frontend/              the client
└── docker/                the store, the service and the client, and the two narrower setups
```

The two libraries named for Skyscanner are shared with Truth and no longer named for what they hold. Renaming
a Python package is not a rename - it is every import in the repository - so it has not been done yet, and
this is the note saying so rather than a reader having to work it out from the import list.

## Running either one

```bash
cd skyscanner/docker && docker compose up --build     # http://localhost:8080
cd truth/docker      && docker compose up --build     # http://localhost:8090
```

Each brings up its own store and is independent of the other. Their own READMEs cover configuration, seeding
and the development setups that run without Docker.

## The workspaces

One npm workspace and one uv workspace span the whole repository, so a library is edited in place and both
products see the change without anything being published or linked.

```bash
npm install     # every TypeScript workspace, from here
uv sync         # every Python workspace, from here
```

```bash
uv run mypy -p skyscanner_models -p skyscanner_common -p ag_grid_lib \
            -p events_service -p storage_service -p notification_service -p truth_service
uv run pylint skyscanner_models skyscanner_common ag_grid_lib \
              events_service storage_service notification_service truth_service

npm run type-check --workspace skyscanner/frontend
npm run lint       --workspace skyscanner/frontend
npm run type-check --workspace truth/frontend
npm run lint       --workspace truth/frontend
```
