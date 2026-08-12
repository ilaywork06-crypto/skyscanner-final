<template>
  <!--
    The name of a file is one of the things the inventory is searched by, so the list is told what was
    searched for: a row that is on screen because of a file it carries has to say which file that was.
  -->
  <FileList
    :files="files"
    :search="search"
    start-open
    @open="onOpen"
    @download="onDownload"
  />
</template>

<script lang="ts">
import type { ICellRendererParams } from 'ag-grid-community'
import type { Artifact } from '@/models/common'
import type { GridRow } from '@/models/grid'

interface Props {
  params: ICellRendererParams<GridRow>
}
</script>

<script setup lang="ts">
import { computed } from 'vue'

import FileList from '@/components/FileList.vue'
import { readContext } from '@/utils/grid-context'
import { readArtifacts } from '@/utils/rows'

const props = defineProps<Props>()

const files = computed<Artifact[]>(() => readArtifacts(props.params.value ?? null))

const search = computed<string>(() => readContext(props.params).search)

const onOpen = (artifact: Artifact) => {
  readContext(props.params).openArtifact(artifact)
}

const onDownload = (artifact: Artifact) => {
  readContext(props.params).downloadArtifact(artifact)
}
</script>

<style>
</style>
