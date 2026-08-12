<template>
  <!--
    Every run is bound as text rather than as markup, because every value painted here was typed by a user:
    a name that happens to read like HTML has to reach the page as the characters it is. The whole of the
    text is rendered in one piece when the term never occurs in it, so a value that did not match costs a
    scan and nothing else.
  -->
  <template
    v-for="(segment, index) in segments"
    :key="index"
  >
    <mark
      v-if="segment.matched"
      class="highlighted-text__mark"
    >{{ segment.text }}</mark>
    <template v-else>
      {{ segment.text }}
    </template>
  </template>
  <template v-if="segments.length === 0">
    {{ text }}
  </template>
</template>

<script lang="ts">
import type { HighlightSegment } from '@/utils/highlight'

interface Props {
  /** The text as the surface reads it out. */
  text: string
  /** What the rows on screen were searched for. */
  term: string
  /**
   * The value the search ran against, where the text is a rendering of that value rather than the value.
   *
   * A status is stored as `in_progress` and read out as "In Progress", so a reader who searched for the
   * stored spelling matched a row whose label the term does not occur in anywhere. Marking the whole label
   * is what keeps that row from reading as if nothing about it matched.
   */
  stored?: string
}
</script>

<script setup lang="ts">
import { computed } from 'vue'

import { matchesTerm, splitHighlights } from '@/utils/highlight'

const props = withDefaults(defineProps<Props>(), { stored: '' })

const segments = computed<HighlightSegment[]>(() => {
  const runs = splitHighlights(props.text, props.term)
  if (runs.length > 0 || props.stored.length === 0 || !matchesTerm(props.stored, props.term)) {
    return runs
  }

  return [{ text: props.text, matched: true }]
})
</script>

<style scoped>
/*
 * A browser paints a mark in its own yellow on its own black, which is unreadable the moment either palette
 * moves away from that pair, so both colours are restated in the theme: the pen is the warning colour and
 * the ink is the colour the theme itself picked to be read against it, whichever palette is on.
 */
.highlighted-text__mark {
  border-radius: 0.1875rem;
  padding-inline: 0.0625rem;
  background-color: rgb(var(--v-theme-warning));
  color: rgb(var(--v-theme-on-warning));
}
</style>
