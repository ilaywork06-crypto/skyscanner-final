<template>
  <div class="sky-page">
    <AppHeader :industries="industries" />

    <div class="sky-page__content">
      <div class="snapshots__heading">
        <h1 class="snapshots__title">
          Snapshots
        </h1>
        <v-spacer />
        <v-btn
          color="primary"
          prepend-icon="mdi-camera-outline"
          :disabled="registerTotal === 0"
          @click="capture"
        >
          TAKE A SNAPSHOT
        </v-btn>
      </div>

      <!--
        A snapshot is kept in this browser and nowhere else, because the API stores none. Saying so plainly is
        the only honest way to offer the feature: somebody who took one has to know it is not a record the
        organisation holds.
      -->
      <v-alert
        type="info"
        variant="tonal"
        density="compact"
      >
        Snapshots are kept in this browser only. They are not stored by the service, nobody else can see them,
        and clearing this browser's data removes them. At most {{ MAX_SNAPSHOTS }} are kept, and each one holds
        the newest {{ SNAPSHOT_ROW_LIMIT }} assumptions rather than the whole register.
      </v-alert>

      <div
        v-if="snapshots.length === 0"
        class="snapshots__empty"
      >
        No snapshots have been taken yet. Taking one preserves the register exactly as it stands now, so it can
        be read back and compared later.
      </div>

      <div
        v-else
        class="snapshots__list"
      >
        <v-card
          v-for="snapshot in snapshots"
          :key="snapshot.id"
          class="snapshots__card"
        >
          <div class="snapshots__card-main">
            <h2 class="snapshots__card-title">
              {{ snapshot.name }}
            </h2>
            <span class="snapshots__meta">
              {{ formatDateTime(snapshot.takenAt) }} by {{ snapshot.takenBy }}
            </span>
            <span class="snapshots__meta">
              {{ snapshot.rowCount }} {{ snapshot.rowCount === 1 ? 'assumption' : 'assumptions' }}
              <template v-if="snapshot.industry !== null">— {{ industryName(snapshot.industry) }}</template>
            </span>
          </div>

          <div class="snapshots__card-actions">
            <UiChip
              :label="driftOf(snapshot)"
              :token="driftToken(snapshot)"
            />
            <v-btn
              variant="text"
              size="small"
              prepend-icon="mdi-table-eye"
              @click="open(snapshot.id)"
            >
              Open
            </v-btn>
            <v-btn
              variant="text"
              size="small"
              prepend-icon="mdi-download-outline"
              @click="download(snapshot.id)"
            >
              Export
            </v-btn>
            <v-btn
              icon="mdi-delete-outline"
              variant="text"
              size="small"
              :aria-label="`Delete ${snapshot.name}`"
              @click="remove(snapshot.id)"
            />
          </div>
        </v-card>
      </div>

      <v-dialog
        :model-value="opened !== null"
        max-width="80rem"
        scrollable
        @update:model-value="opened = null"
      >
        <v-card v-if="opened !== null">
          <v-card-title>{{ opened.name }}</v-card-title>
          <v-card-subtitle>
            {{ formatDateTime(opened.takenAt) }} by {{ opened.takenBy }}
          </v-card-subtitle>
          <v-card-text>
            <v-table density="compact">
              <thead>
                <tr>
                  <th
                    v-for="column in opened.columns"
                    :key="column"
                  >
                    {{ humanizeKey(column) }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in opened.rows"
                  :key="String(row.id)"
                >
                  <td
                    v-for="column in opened.columns"
                    :key="column"
                  >
                    {{ cellOf(row, column) }}
                  </td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn
              variant="text"
              @click="opened = null"
            >
              Close
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  UiChip,
  formatDateTime,
  humanizeKey,
  useSnackbar,
  type GridRow,
  type JsonValue,
} from '@truth-platform/core-ui'
import { onMounted, ref, shallowRef } from 'vue'

import AppHeader from '@/components/AppHeader.vue'
import { useRegister } from '@/composables/useRegister'
import { buildConfiguration } from '@/utils/columns'
import { exportRows } from '@/utils/export'
import { readCreator } from '@/utils/identity'
import {
  MAX_SNAPSHOTS,
  captureSnapshot,
  deleteSnapshot,
  SNAPSHOT_ROW_LIMIT,
  listSnapshots,
  readSnapshot,
  type Snapshot,
  type SnapshotSummary,
} from '@/utils/snapshots'
import { assumptionToRow } from '@/utils/rows'
import { listAssumptions, queryAssumptions } from '@/requests/assumptions'

const { industries, fields, findIndustry } = useRegister()
const { notify, reportError } = useSnackbar()

const snapshots = ref<SnapshotSummary[]>([])
const opened = shallowRef<Snapshot | null>(null)

const refresh = () => {
  snapshots.value = listSnapshots()
}

onMounted(refresh)

/* How many assumptions the register currently holds, which is what a snapshot is compared against. */
const registerTotal = ref<number>(0)

const loadTotal = async () => {
  try {
    registerTotal.value = (await queryAssumptions({ search: null, industry: null, filters: [], sort: [], offset: 0, limit: 1 })).total
  } catch (error) {
    reportError(error)
  }
}

onMounted(() => {
  void loadTotal()
})

const industryName = (identifier: string): string => findIndustry(identifier)?.name ?? identifier

/**
 * How far the register has moved since a snapshot was taken, counted in assumptions.
 */
const driftOf = (snapshot: SnapshotSummary): string => {
  const difference = registerTotal.value - snapshot.rowCount

  if (difference === 0) {
    return 'Unchanged in count'
  }

  return difference > 0 ? `+${difference} since` : `${difference} since`
}

const driftToken = (snapshot: SnapshotSummary): string =>
  registerTotal.value === snapshot.rowCount ? 'status-positive' : 'status-pending'

/**
 * Preserve the register as it stands, under a name that says when it was taken.
 */
const capture = async () => {
  const columns = buildConfiguration(fields.value)
    .columns.filter((column) => column.colId !== 'expand')
    .map((column) => column.colId)

  let preserved: GridRow[]
  try {
    preserved = (await listAssumptions(0, SNAPSHOT_ROW_LIMIT)).map((row) => assumptionToRow(row))
  } catch (error) {
    reportError(error)

    return
  }

  const taken = captureSnapshot({
    name: `Register of ${new Date().toLocaleString()}`,
    takenBy: readCreator(),
    industry: null,
    columns,
    rows: preserved,
  })

  if (taken === null) {
    reportError(new Error('This browser could not store the snapshot — its storage is full or unavailable'))

    return
  }

  refresh()
  notify('The register was preserved in this browser', 'success')
}

const open = (snapshotId: string) => {
  opened.value = readSnapshot(snapshotId)
}

const remove = (snapshotId: string) => {
  deleteSnapshot(snapshotId)
  refresh()
}

/**
 * Write one snapshot out as a spreadsheet, which is the one way it leaves this browser.
 */
const download = (snapshotId: string) => {
  const snapshot = readSnapshot(snapshotId)
  if (snapshot === null) {
    return
  }

  try {
    const columns = buildConfiguration(fields.value).columns.filter((column) =>
      snapshot.columns.includes(column.colId),
    )
    exportRows(snapshot.rows, columns)
    notify('The snapshot was exported', 'success')
  } catch (error) {
    reportError(error)
  }
}

/**
 * Render one cell of a preserved row, which is read by column identifier rather than by column path.
 */
const cellOf = (row: GridRow, column: string): string => {
  const direct = row[column]
  const value: JsonValue =
    direct === undefined
      ? ((row.values as Record<string, JsonValue> | undefined)?.[column] ?? null)
      : direct

  if (value === null || value === '') {
    return '—'
  }

  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join(', ')
  }

  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}
</script>

<style scoped>
.snapshots__heading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.snapshots__title {
  font-size: 1.75rem;
  font-weight: 600;
}

.snapshots__empty,
.snapshots__meta {
  color: rgb(var(--v-theme-app-muted));
  font-size: 0.875rem;
}

.snapshots__empty {
  padding-block: 2rem;
  text-align: center;
}

.snapshots__list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* A card is a row on a wide screen and a stack on a narrow one, without either being a breakpoint. */
.snapshots__card {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1rem;
  background-color: rgb(var(--v-theme-surface));
}

.snapshots__card-main {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-inline-size: 0;
}

.snapshots__card-title {
  font-size: 1rem;
  font-weight: 600;
}

.snapshots__card-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
}

/* A wide table of preserved rows scrolls inside the dialog rather than widening it. */
.snapshots__card :deep(.v-table__wrapper),
:deep(.v-card-text .v-table__wrapper) {
  overflow-x: auto;
}
</style>
