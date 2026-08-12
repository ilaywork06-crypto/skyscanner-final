<template>
  <v-icon
    :icon="icon"
    :color="color"
    size="small"
  />
</template>

<script lang="ts">
import type { ICellRendererParams } from 'ag-grid-community'
import type { GridRow } from '@/models/grid'

interface Props {
  params: ICellRendererParams<GridRow>
}
</script>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<Props>()

const truthy = computed<boolean>(() => props.params.value === true || props.params.value === 'true')

const icon = computed<string>(() => (truthy.value ? 'mdi-check-circle-outline' : 'mdi-minus-circle-outline'))
const color = computed<string>(() => (truthy.value ? 'status-positive' : 'app-muted'))
</script>

<style>
</style>
