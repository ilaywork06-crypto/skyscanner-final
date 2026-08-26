<template>
  <!--
    A point is three numbers, and the two that matter are far easier to point at than to type. The map is
    therefore the primary way in and the boxes stay beside it, so a value copied out of a report can still be
    pasted in, and so the altitude - which no map knows - has somewhere to go.
  -->
  <div class="coordinate">
    <div
      v-if="hasTiles"
      ref="canvas"
      class="coordinate__map"
      role="application"
      :aria-label="`Pick ${label} on the map`"
    />
    <p
      v-else
      class="coordinate__no-map"
    >
      No map server is configured for this deployment, so the point is typed rather than pointed at.
    </p>

    <div class="coordinate__inputs">
      <v-text-field
        :model-value="latText"
        label="Latitude"
        type="number"
        density="compact"
        hide-details
        :step="STEP"
        :readonly="readonly"
        @update:model-value="onTyped('lat', $event)"
      />
      <v-text-field
        :model-value="lonText"
        label="Longitude"
        type="number"
        density="compact"
        hide-details
        :step="STEP"
        :readonly="readonly"
        @update:model-value="onTyped('lon', $event)"
      />
      <v-text-field
        :model-value="altText"
        label="Altitude (m)"
        type="number"
        density="compact"
        hide-details
        :readonly="readonly"
        @update:model-value="onTyped('alt', $event)"
      />
      <v-btn
        v-if="!readonly"
        icon="mdi-close"
        size="x-small"
        variant="text"
        :disabled="point === null"
        aria-label="Clear the coordinate"
        @click="clear"
      />
    </div>
  </div>
</template>

<script lang="ts">
import type { Coordinate, JsonValue } from '@/models/common'

interface Props {
  modelValue: JsonValue
  label?: string
  /** Whether the point is only being shown, which is how a cell of the table opens it. */
  readonly?: boolean
}

interface Emits {
  (event: 'update:modelValue', value: JsonValue): void
}

/** Which of the three numbers a keystroke landed in. */
type Part = 'lon' | 'lat' | 'alt'

/** How far one press of the spinner moves a degree, which is roughly a metre. */
const STEP = 0.00001
</script>

<script setup lang="ts">
import 'leaflet/dist/leaflet.css'

import type { CircleMarker, LeafletMouseEvent, Map as LeafletMap } from 'leaflet'
import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue'

import {
  DEFAULT_CENTER,
  DEFAULT_ZOOM,
  DEGREE_DECIMALS,
  PICKED_ZOOM,
  TILE_ATTRIBUTION,
  TILE_URL,
  buildCoordinate,
  toCoordinate,
} from '@/utils/coordinates'

const props = withDefaults(defineProps<Props>(), { label: 'the coordinate', readonly: false })
const emit = defineEmits<Emits>()

const canvas = ref<HTMLElement | null>(null)
const map = shallowRef<LeafletMap | null>(null)
const marker = shallowRef<CircleMarker | null>(null)

/*
 * What is currently being typed, kept separately from the point that was emitted. Half a number is not a
 * point, so a field being edited would otherwise be erased from under the pointer on every keystroke.
 */
const typed = ref<Partial<Record<Part, string>>>({})

const hasTiles = computed<boolean>(() => TILE_URL.length > 0)

const point = computed<Coordinate | null>(() => toCoordinate(props.modelValue))

const partText = (part: Part): string => {
  const pending = typed.value[part]
  if (pending !== undefined) {
    return pending
  }

  const current = point.value
  if (current === null) {
    return ''
  }

  const value = current[part]

  return value === null ? '' : String(value)
}

const latText = computed<string>(() => partText('lat'))
const lonText = computed<string>(() => partText('lon'))
const altText = computed<string>(() => partText('alt'))

/**
 * Hand the parent the point the three boxes currently spell, or nothing while they do not spell one yet.
 */
const emitTyped = () => {
  const read = (part: Part): number => Number(partText(part))
  const altitude = altText.value.length === 0 ? null : read('alt')
  const built =
    latText.value.length === 0 || lonText.value.length === 0
      ? null
      : buildCoordinate(read('lon'), read('lat'), altitude)

  emit('update:modelValue', built === null ? null : { ...built })
}

const onTyped = (part: Part, value: string) => {
  if (props.readonly) {
    return
  }

  typed.value = { ...typed.value, [part]: value }
  emitTyped()
}

const clear = () => {
  typed.value = {}
  emit('update:modelValue', null)
}

/**
 * Take the point the pointer landed on, which replaces whatever the two degree boxes were holding.
 *
 * The altitude is left exactly as it was: a map says where a thing is, never how high it was, so a height
 * that was typed survives the point being moved.
 */
const onMapClick = (event: LeafletMouseEvent) => {
  if (props.readonly) {
    return
  }

  const picked = buildCoordinate(
    Number(event.latlng.lng.toFixed(DEGREE_DECIMALS)),
    Number(event.latlng.lat.toFixed(DEGREE_DECIMALS)),
    altText.value.length === 0 ? null : Number(altText.value),
  )
  if (picked === null) {
    return
  }

  typed.value = {}
  emit('update:modelValue', { ...picked })
}

/**
 * Put the marker where the value says, and move the map there the first time a point appears.
 */
const paint = async (): Promise<void> => {
  const instance = map.value
  const current = point.value
  if (instance === null) {
    return
  }

  const { circleMarker } = await import('leaflet')
  if (current === null) {
    marker.value?.remove()
    marker.value = null

    return
  }

  const position: [number, number] = [current.lat, current.lon]
  if (marker.value === null) {
    marker.value = circleMarker(position, { radius: 7, weight: 2 }).addTo(instance)
    instance.setView(position, Math.max(instance.getZoom(), PICKED_ZOOM))

    return
  }

  marker.value.setLatLng(position)
}

/**
 * Build the map once the element it draws into exists, which only happens when a tile server was named.
 */
const build = async (): Promise<void> => {
  const element = canvas.value
  if (element === null || map.value !== null) {
    return
  }

  const { map: createMap, tileLayer } = await import('leaflet')
  const instance = createMap(element).setView([...DEFAULT_CENTER], DEFAULT_ZOOM)
  tileLayer(TILE_URL, { attribution: TILE_ATTRIBUTION }).addTo(instance)
  instance.on('click', onMapClick)
  map.value = instance

  await paint()
}

watch(canvas, build, { immediate: true, flush: 'post' })
watch(point, paint)

onBeforeUnmount(() => {
  map.value?.remove()
  map.value = null
  marker.value = null
})
</script>

<style scoped>
.coordinate {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.coordinate__map {
  block-size: 14rem;
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-radius: 0.5rem;
  /* Leaflet stacks its own panes, and without this the overlay of a dialog ends up underneath them. */
  z-index: 0;
}

.coordinate__no-map {
  font-size: 0.8125rem;
  opacity: 0.7;
}

/* The two degrees are read together and the altitude beside them, so the row keeps them on one line. */
.coordinate__inputs {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.5rem;
}

@media (max-width: 40rem) {
  .coordinate__inputs {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
}
</style>
