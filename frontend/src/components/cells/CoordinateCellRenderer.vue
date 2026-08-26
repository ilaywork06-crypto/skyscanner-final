<template>
  <!--
    A point in a cell is read rather than picked, so the numbers are what the row shows. The map behind them
    is one click away, because a pair of degrees tells nobody where a thing actually was.
  -->
  <span class="coordinate-cell">
    <template v-if="point === null">{{ EMPTY_PLACEHOLDER }}</template>
    <template v-else>
      <v-icon
        size="x-small"
        icon="mdi-map-marker-outline"
      />
      <span class="coordinate-cell__text">{{ formatCoordinate(point) }}</span>
      <button
        type="button"
        class="coordinate-cell__open"
        :aria-label="`Show ${headerName} on the map`"
        @click.stop="dialog = true"
      >
        <v-icon
          icon="mdi-map-outline"
          size="x-small"
        />
      </button>
    </template>

    <v-dialog
      v-if="point !== null"
      v-model="dialog"
      max-width="44rem"
    >
      <v-card>
        <v-card-title>{{ headerName }}</v-card-title>
        <v-card-text>
          <CoordinateField
            :model-value="params.value ?? null"
            :label="headerName"
            readonly
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="dialog = false"
          >
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </span>
</template>

<script lang="ts">
import type { ICellRendererParams } from 'ag-grid-community'
import { EMPTY_PLACEHOLDER } from '@skyscanner/sky-ui'
import type { Coordinate } from '@/models/common'
import type { GridRow } from '@/models/grid'

interface Props {
  params: ICellRendererParams<GridRow>
}
</script>

<script setup lang="ts">
import { computed, ref } from 'vue'

import CoordinateField from '@/components/CoordinateField.vue'
import { formatCoordinate, toCoordinate } from '@/utils/coordinates'

const props = defineProps<Props>()

const dialog = ref<boolean>(false)

const point = computed<Coordinate | null>(() => toCoordinate(props.params.value ?? null))

const headerName = computed<string>(() => props.params.colDef?.headerName ?? 'Coordinate')
</script>

<style scoped>
.coordinate-cell {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  min-inline-size: 0;
}

.coordinate-cell__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

/* The way onto the map stays out of sight until the row is pointed at, exactly as the other cells do it. */
.coordinate-cell__open {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  border: none;
  background: none;
  padding: 0;
  color: inherit;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s ease-in-out;
}

.coordinate-cell:hover .coordinate-cell__open,
.coordinate-cell__open:focus-visible {
  opacity: 0.75;
}
</style>
