<template>
  <!--
    The marker pen goes inside the chip rather than behind it: laying a band over the whole chip said only
    that something in this cell matched, where the reader is looking for which characters of it did.
  -->
  <UiChip
    v-if="isMatch"
    :label="label"
    :token="token"
  >
    <HighlightedText
      :text="label"
      :term="search"
    />
  </UiChip>
  <UiChip
    v-else-if="label.length > 0"
    :label="label"
    :token="token"
  />
  <span
    v-else
    class="chip-cell__empty"
  >{{ EMPTY_PLACEHOLDER }}</span>
</template>

<script lang="ts">
import type { ICellRendererParams } from 'ag-grid-community'
import { EMPTY_PLACEHOLDER, UiChip } from '../../index'
import type { GridRow } from '../../models/grid'

interface Props {
  params: ICellRendererParams<GridRow> & { palette?: string }
}

const PLATFORM_TOKEN = 'chip-platform'
const DEFAULT_TOKEN = 'chip-industry-violet'
</script>

<script setup lang="ts">
import { computed } from 'vue'

import HighlightedText from '../../components/HighlightedText.vue'
import { taxonomyToken } from '../../utils/palette'
import { readContext } from '../../utils/grid-context'
import { matchesTerm } from '../../utils/highlight'

const props = defineProps<Props>()

const label = computed<string>(() => {
  const value = props.params.value

  return value === null || value === undefined ? '' : String(value)
})

const search = computed<string>(() => readContext(props.params).search)

const isMatch = computed<boolean>(() => label.value.length > 0 && matchesTerm(label.value, search.value))

const token = computed<string>(() => {
  if (props.params.palette === 'platform') {
    return PLATFORM_TOKEN
  }

  if (props.params.palette === 'industry') {
    return taxonomyToken(label.value, readContext(props.params).taxonomy)
  }

  return DEFAULT_TOKEN
})
</script>

<style>
.chip-cell__empty {
  opacity: 0.6;
}
</style>
