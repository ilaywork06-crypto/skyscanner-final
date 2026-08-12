<template>
  <!--
    The icon and the tooltip are siblings inside this span on purpose. A font icon is rendered by Vuetify's
    VClassIcon, which draws an <i> and drops whatever was written between the tags, so a tooltip nested inside
    a <v-icon icon="mdi-..."> is never mounted and never appears. The span is what the tooltip attaches itself
    to, and it is also what carries the focus, so the explanation is reachable by keyboard and not only by hover.
  -->
  <span
    class="sky-info-icon"
    :aria-label="label"
    tabindex="0"
  >
    <v-icon
      class="sky-info-icon__glyph"
      :size="size"
      :icon="ICON"
    />
    <SkyTooltip
      activator="parent"
      :location="location"
    >
      <slot />
    </SkyTooltip>
  </span>
</template>

<script lang="ts">
interface Props {
  /** What the explanation is about, announced to a reader that cannot see the icon. */
  label?: string
  size?: 'x-small' | 'small' | 'default'
  location?: 'top' | 'bottom' | 'start' | 'end'
}

const ICON = 'mdi-information-outline'
</script>

<script setup lang="ts">
import SkyTooltip from './SkyTooltip.vue'

withDefaults(defineProps<Props>(), {
  label: 'More information',
  size: 'x-small',
  location: 'top',
})
</script>

<style scoped>
.sky-info-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  vertical-align: middle;
  border-radius: 50%;
  cursor: help;
  opacity: 0.65;
}

.sky-info-icon:hover,
.sky-info-icon:focus-visible {
  opacity: 1;
}

/* The glyph is decoration next to the label the span already announces, so it stays out of the tab order. */
.sky-info-icon__glyph {
  pointer-events: none;
}
</style>
