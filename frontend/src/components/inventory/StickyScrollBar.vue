<template>
  <!--
    A table that renders every one of its rows is taller than the window, which leaves the scrollbar underneath
    it out of reach until the page has been scrolled to the very last row. This bar carries the same movement
    and is pinned to the foot of the window while the table is on screen, so the columns further to the right
    can be reached from wherever the page happens to stand.
  -->
  <div
    v-show="scrollable"
    ref="track"
    class="sticky-scroll"
    :style="{ inlineSize: `${trackWidth}px`, marginInlineStart: `${trackOffset}px` }"
    aria-hidden="true"
    @scroll="onTrackScroll"
  >
    <div
      class="sticky-scroll__extent"
      :style="{ inlineSize: `${extentWidth}px` }"
    />
  </div>
</template>

<script lang="ts">
interface Props {
  /**
   * The element the table scrolls its columns with, or null while the table is still building itself. The bar
   * is a copy of it: as wide as the part of the table that is on screen, holding a strip as wide as all of it.
   */
  viewport: HTMLElement | null
}

/**
 * Two positions less than a pixel apart are the same position.
 *
 * Each bar answers the movement of the other by writing it onto itself, and writing a position an element
 * already holds raises no scroll event, so every move crosses over exactly once instead of echoing back.
 */
const SCROLL_EPSILON = 1
</script>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<Props>()

const track = ref<HTMLElement | null>(null)
const trackWidth = ref<number>(0)
const trackOffset = ref<number>(0)
const extentWidth = ref<number>(0)
const scrollable = ref<boolean>(false)

/* The element the listeners below are currently on, which is the one they have to come off again. */
let attached: HTMLElement | null = null
let observer: ResizeObserver | null = null

/**
 * Write one position onto an element, unless it is already there.
 */
const mirror = (target: HTMLElement, position: number) => {
  if (Math.abs(target.scrollLeft - position) >= SCROLL_EPSILON) {
    target.scrollLeft = position
  }
}

/**
 * Bring the bar to the place the table is currently scrolled to.
 */
const followViewport = () => {
  const bar = track.value
  if (bar === null || props.viewport === null) {
    return
  }

  mirror(bar, props.viewport.scrollLeft)
}

/**
 * Measure the table, which is what the bar is a copy of.
 *
 * The bar is given the width of the part of the table that moves and a strip as wide as all of its columns,
 * so that the distance the two can travel is the same and one can be read as the other. That width is not
 * the width of the table: the pinned columns stand still at either end of it, and a bar as wide as the whole
 * table would have less room to travel than the columns it moves - which is what left the last column out of
 * reach, however far the bar was dragged. It is laid out where the moving part of the table is instead, and
 * lines up underneath it. A table whose columns already fit has nowhere to travel and shows no bar at all.
 */
const measure = () => {
  const viewport = props.viewport
  const bar = track.value
  if (viewport === null || bar === null) {
    return
  }

  const parent = bar.parentElement
  const origin = parent === null ? 0 : parent.getBoundingClientRect().left

  trackWidth.value = viewport.clientWidth
  trackOffset.value = Math.max(0, viewport.getBoundingClientRect().left - origin)
  extentWidth.value = viewport.scrollWidth
  scrollable.value = viewport.scrollWidth - viewport.clientWidth >= SCROLL_EPSILON

  /* A bar that was hidden, or has just been given another width, has lost the place it was scrolled to. */
  void nextTick(followViewport)
}

const onTrackScroll = () => {
  const bar = track.value
  if (bar === null || props.viewport === null) {
    return
  }

  mirror(props.viewport, bar.scrollLeft)
}

const detach = () => {
  attached?.removeEventListener('scroll', followViewport)
  observer?.disconnect()
  attached = null
  observer = null
}

/**
 * Follow a table: its movement, its width and the width of the columns inside it.
 *
 * The width of the columns is not something an element reports, so the strip the table scrolls is watched as
 * well - it is held at exactly that width, and it is resized whenever a column is shown, hidden or dragged.
 */
const attach = (viewport: HTMLElement | null) => {
  detach()
  if (viewport === null) {
    return
  }

  attached = viewport
  viewport.addEventListener('scroll', followViewport)
  observer = new ResizeObserver(measure)
  observer.observe(viewport)

  const columns = viewport.firstElementChild
  if (columns !== null) {
    observer.observe(columns)
  }

  measure()
}

watch(() => props.viewport, attach, { immediate: true })

/*
 * The bar is laid out against its own place on the page, which it has none of until it is on the page. A
 * table that was already scrollable when this was created is therefore measured again once it is.
 */
onMounted(measure)

onBeforeUnmount(detach)
</script>

<style scoped>
.sticky-scroll {
  /* The bar is no thicker than the scrollbar inside it, so it takes as little of the table as it can. */
  --sticky-scroll-thickness: 0.875rem;

  position: sticky;
  /*
   * Pinned to the foot of the window while any part of the table is on screen, and coming to rest under the
   * last row once the end of the table is reached, which is where a scrollbar of a table belongs.
   */
  inset-block-end: 0;
  z-index: 1;
  align-self: flex-start;
  box-sizing: content-box;
  block-size: var(--sticky-scroll-thickness);
  overflow-x: scroll;
  overflow-y: hidden;
  /* The bar floats over the rows for as long as it is pinned, so it carries a ground of its own. */
  background-color: rgb(var(--v-theme-surface));
  border-block-start: 0.0625rem solid rgb(var(--v-theme-control-border));
  scrollbar-width: thin;
  scrollbar-color: rgb(var(--v-theme-control-border)) transparent;
}

/* Safari and the older Chromium browsers read none of the two properties above, and this instead. */
.sticky-scroll::-webkit-scrollbar {
  block-size: var(--sticky-scroll-thickness);
}

.sticky-scroll::-webkit-scrollbar-thumb {
  background-color: rgb(var(--v-theme-control-border));
  border-radius: 999rem;
}

/* Nothing is drawn here: the strip exists only to give the bar the distance the table has to travel. */
.sticky-scroll__extent {
  block-size: 0.0625rem;
}
</style>
