<template>
  <!--
    A status is stored as a key and read out as a label, and the search ran against the key. Both spellings
    are therefore handed to the marker pen: it paints the run of the label the term occurs in, and falls back
    to the whole label for a reader who searched for the stored spelling the label does not show.
  -->
  <SkyChip
    v-if="isMatch"
    :label="label"
    :token="token"
  >
    <HighlightedText
      :text="label"
      :term="search"
      :stored="raw"
    />
  </SkyChip>
  <SkyChip
    v-else-if="label.length > 0"
    :label="label"
    :token="token"
  />
  <span
    v-else
    class="status-cell__empty"
  >{{ EMPTY_PLACEHOLDER }}</span>
</template>

<script lang="ts">
import type { ICellRendererParams } from 'ag-grid-community'
import { EMPTY_PLACEHOLDER, SkyChip, humanizeKey } from '@skyscanner/sky-ui'
import type { GridRow } from '@/models/grid'

interface Props {
  params: ICellRendererParams<GridRow> & { palette?: string }
}
</script>

<script setup lang="ts">
import { computed } from 'vue'

import HighlightedText from '@/components/HighlightedText.vue'
import { paletteToken } from '@/utils/colors'
import { readContext } from '@/utils/grid-context'
import { matchesTerm } from '@/utils/highlight'

const props = defineProps<Props>()

const raw = computed<string>(() => {
  const value = props.params.value

  return value === null || value === undefined ? '' : String(value)
})

const label = computed<string>(() => (raw.value.length === 0 ? '' : humanizeKey(raw.value)))
const token = computed<string>(() => paletteToken(props.params.palette, raw.value))

const search = computed<string>(() => readContext(props.params).search)

const isMatch = computed<boolean>(
  () => label.value.length > 0 && (matchesTerm(label.value, search.value) || matchesTerm(raw.value, search.value)),
)
</script>

<style>
.status-cell__empty {
  opacity: 0.6;
}
</style>
