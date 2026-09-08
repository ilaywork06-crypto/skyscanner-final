<template>
  <!--
    A cell can only ever show the first line of a long note or of a JSON document. Rather than making the
    reader hover and squint at a tooltip, the whole value opens here, formatted and selectable.
  -->
  <v-dialog
    :model-value="modelValue"
    max-width="56rem"
    scrollable
    @update:model-value="close"
  >
    <v-card class="value-viewer">
      <v-card-title class="value-viewer__title">
        <span>{{ title }}</span>
        <v-spacer />
        <v-btn
          icon="mdi-content-copy"
          variant="text"
          density="comfortable"
          aria-label="Copy the value"
          @click="copy"
        />
        <v-btn
          icon="mdi-close"
          variant="text"
          density="comfortable"
          aria-label="Close"
          @click="close"
        />
      </v-card-title>

      <v-card-text class="value-viewer__body">
        <!--
          The whole value, with whatever addresses it holds read out of it. This is where a link stored in a
          field is actually reachable: the cell it came from had room for a fragment, and a fragment of an
          address is not one, so the cell shows characters and this shows the link.
        -->
        <pre
          class="value-viewer__content"
          :class="{ 'value-viewer__content--code': monospace }"
        ><UiLinkedText :text="value" /></pre>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
interface Props {
  modelValue: boolean
  value: string
  title?: string
  monospace?: boolean
}

interface Emits {
  (event: 'update:modelValue', value: boolean): void
  (event: 'copied', succeeded: boolean): void
}
</script>

<script setup lang="ts">
import UiLinkedText from './UiLinkedText.vue'

const props = withDefaults(defineProps<Props>(), { title: 'Value', monospace: false })
const emit = defineEmits<Emits>()

const close = () => {
  emit('update:modelValue', false)
}

/**
 * Put the value on the clipboard and tell the caller how it went, so that whoever renders this decides
 * how the outcome is announced.
 */
const copy = async (): Promise<void> => {
  try {
    await navigator.clipboard.writeText(props.value)
    emit('copied', true)
  } catch {
    emit('copied', false)
  }
}
</script>

<style scoped>
.value-viewer {
  background-color: rgb(var(--v-theme-surface));
}

.value-viewer__title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.0625rem;
  font-weight: 600;
}

.value-viewer__body {
  max-block-size: 65vh;
}

.value-viewer__content {
  margin: 0;
  border-radius: 0.5rem;
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  padding: 1rem;
  font-family: inherit;
  font-size: 0.875rem;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.value-viewer__content--code {
  font-family: ui-monospace, 'SFMono-Regular', 'Consolas', monospace;
  font-size: 0.8125rem;
}
</style>
