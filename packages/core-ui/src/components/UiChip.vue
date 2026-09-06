<template>
  <span
    class="sky-chip"
    :class="{ 'sky-chip--solid': solid }"
    :style="chipStyle"
  ><!--
    A chip reads out its label itself, and a caller that has to say something about the label rather than
    only what it says - a run of it the search matched, painted inside the chip instead of over the whole of
    it - fills the slot with the label it built. Leaving the slot alone is what every other caller does.
  --><slot>{{ label }}</slot></span>
</template>

<script lang="ts">
interface Props {
  /** What the chip reads out, and what it falls back to whenever the slot is left alone. */
  label: string
  token: string
  solid?: boolean
}
</script>

<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from 'vuetify'

const props = withDefaults(defineProps<Props>(), { solid: false })

const theme = useTheme()

const chipStyle = computed<Record<string, string>>(() => {
  const variable = `var(--v-theme-${props.token})`
  const isDark = theme.current.value.dark

  if (props.solid || !isDark) {
    return {
      backgroundColor: `rgb(${variable})`,
      color: '#FFFFFF',
      borderColor: `rgba(${variable}, 0.6)`,
    }
  }

  return {
    backgroundColor: `rgba(${variable}, 0.18)`,
    color: `rgb(${variable})`,
    borderColor: `rgba(${variable}, 0.35)`,
  }
})
</script>

<style scoped>
.sky-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0.0625rem solid transparent;
  border-radius: 0.375rem;
  padding-inline: 0.75rem;
  padding-block: 0.25rem;
  font-size: 0.8125rem;
  font-weight: 500;
  line-height: 1.25;
  white-space: nowrap;
  max-inline-size: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sky-chip--solid {
  font-weight: 600;
}
</style>
