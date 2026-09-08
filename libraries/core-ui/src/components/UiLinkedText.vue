<template>
  <!--
    Every run reaches the page as text rather than as markup, exactly as the plain painter does: a value that
    happens to read like HTML is shown as the characters somebody typed. A run that is an address becomes a
    real anchor, so it can be opened, opened in a new tab, or copied out of the context menu the way every
    other link on the machine can - which is the whole point of noticing it.
  -->
  <template
    v-for="(segment, index) in segments"
    :key="index"
  >
    <a
      v-if="segment.href !== null"
      class="linked-text__link"
      :href="segment.href"
      target="_blank"
      rel="noopener noreferrer"
      @click.stop
    >
      <HighlightedText
        v-if="term.length > 0"
        :text="segment.text"
        :term="term"
      />
      <template v-else>{{ segment.text }}</template>
    </a>
    <HighlightedText
      v-else-if="term.length > 0"
      :text="segment.text"
      :term="term"
      :stored="stored"
    />
    <template v-else>{{ segment.text }}</template>
  </template>
</template>

<script lang="ts">
import type { LinkSegment } from '../utils/links'

interface Props {
  /** The value as the surface reads it out. */
  text: string
  /** What the rows on screen were searched for, when they were searched for anything. */
  term?: string
  /** The stored spelling of a value the text is a rendering of, passed through to the search painter. */
  stored?: string
}
</script>

<script setup lang="ts">
import { computed } from 'vue'

import HighlightedText from './HighlightedText.vue'
import { splitLinks } from '../utils/links'

const props = withDefaults(defineProps<Props>(), { term: '', stored: '' })

const segments = computed<LinkSegment[]>(() => splitLinks(props.text))
</script>

<!--
  AG Grid mounts a cell renderer outside the Vue render tree, so a component that may be rendered inside one
  never receives a scope attribute and a scoped block here would style nothing at all.
-->
<style>
.linked-text__link {
  color: rgb(var(--v-theme-primary));
  text-decoration: underline;
  text-underline-offset: 0.125rem;
}

.linked-text__link:hover {
  text-decoration-thickness: 0.125rem;
}
</style>
