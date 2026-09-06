<template>
  <header class="app-header">
    <nav
      class="app-header__nav"
      aria-label="Sections"
    >
      <RouterLink
        v-for="link in LINKS"
        :key="link.to"
        class="app-header__link"
        :class="{ 'app-header__link--active': isActive(link.to) }"
        :to="link.to"
      >
        {{ link.label }}
      </RouterLink>

      <!--
        The industries are a menu rather than a row of links, because a register may carry more of them than
        a header has room for. Picking one leads to that industry's own page; the entry above them leads to
        the list of all of them.
      -->
      <v-menu location="bottom start">
        <template #activator="{ props: activator }">
          <button
            v-bind="activator"
            type="button"
            class="app-header__link app-header__link--menu"
            :class="{ 'app-header__link--active': isActive('/industries') }"
          >
            <v-icon
              size="x-small"
              icon="mdi-chevron-up"
            />
            INDUSTRIES
          </button>
        </template>
        <v-list
          class="app-header__menu"
          density="compact"
        >
          <v-list-item
            title="All industries"
            prepend-icon="mdi-view-grid-outline"
            to="/industries"
          />
          <v-divider v-if="industries.length > 0" />
          <v-list-item
            v-for="industry in industries"
            :key="industry.id"
            :title="industry.name"
            :to="`/industries/${industry.id}`"
          />
          <v-list-item
            v-if="industries.length === 0"
            title="No industries yet"
            disabled
          />
        </v-list>
      </v-menu>

      <RouterLink
        class="app-header__link"
        :class="{ 'app-header__link--active': isActive('/assumptions') }"
        to="/assumptions"
      >
        ALL
      </RouterLink>
    </nav>

    <div class="app-header__actions">
      <v-btn
        class="app-header__toggle"
        variant="text"
        role="switch"
        :ripple="false"
        :aria-checked="isDark"
        :aria-label="isDark ? 'Switch to the light theme' : 'Switch to the dark theme'"
        @click="toggle"
      >
        <span
          class="app-header__toggle-knob"
          :class="{ 'app-header__toggle-knob--end': !isDark }"
        >
          <v-icon
            size="x-small"
            :icon="isDark ? 'mdi-weather-night' : 'mdi-white-balance-sunny'"
          />
        </span>
      </v-btn>

      <v-menu location="bottom end">
        <template #activator="{ props: activator }">
          <v-btn
            v-bind="activator"
            icon="mdi-cog"
            variant="text"
            aria-label="Settings"
            title="Settings"
          />
        </template>
        <v-list density="compact">
          <v-list-subheader>Settings</v-list-subheader>
          <v-list-item
            title="Schemas"
            prepend-icon="mdi-table-cog"
            to="/schemas"
          />
          <v-list-item
            title="Industries"
            prepend-icon="mdi-domain"
            to="/industries"
          />
          <v-list-item
            title="Snapshots"
            prepend-icon="mdi-camera-outline"
            to="/snapshots"
          />
          <v-divider />
          <!--
            Every write of the API takes a creator and the service authenticates nobody, so who the client is
            creating as is something the person has to be able to see and change.
          -->
          <v-list-item
            :title="creator"
            subtitle="Creating as"
            prepend-icon="mdi-account-outline"
            @click="identityOpen = true"
          />
        </v-list>
      </v-menu>
    </div>

    <RouterLink
      class="app-header__brand"
      to="/assumptions"
    >
      <svg
        class="app-header__mark"
        viewBox="0 0 32 32"
        aria-hidden="true"
      >
        <path
          d="M16 3 L29 10 L16 17 L3 10 Z"
          fill="currentColor"
          opacity="0.9"
        />
        <path
          d="M3 16 L16 23 L29 16"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linejoin="round"
          opacity="0.6"
        />
        <path
          d="M3 22 L16 29 L29 22"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linejoin="round"
          opacity="0.35"
        />
      </svg>
      <span class="app-header__wordmark">TRUTH</span>
    </RouterLink>

    <IdentityDialog v-model="identityOpen" />

    <slot name="tabs" />
  </header>
</template>

<script lang="ts">
import type { Industry } from '@/models/industry'

interface Props {
  industries?: Industry[]
}

/** The sections of the register, in the order the design puts them across the header. */
const LINKS: { to: string; label: string }[] = [{ to: '/snapshots', label: 'SNAPSHOTS' }]
</script>

<script setup lang="ts">
import { useAppTheme } from '@truth-platform/core-ui'
import { ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import IdentityDialog from '@/components/IdentityDialog.vue'
import { readCreator } from '@/utils/identity'

withDefaults(defineProps<Props>(), { industries: () => [] })

const route = useRoute()
const { isDark, toggle } = useAppTheme()

const identityOpen = ref<boolean>(false)
const creator = ref<string>(readCreator())

/** A section is lit while the reader is anywhere underneath it, not only on its own address. */
const isActive = (path: string): boolean => route.path === path || route.path.startsWith(`${path}/`)
</script>

<style scoped>
/*
 * The header is a single dark band across the top of every page: the sections at one end, the wordmark at the
 * other, and the controls between them. It lays itself out in a row that wraps rather than in fixed columns,
 * so a narrow window stacks it instead of pushing the wordmark off the screen.
 */
.app-header {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
  padding-inline: 2rem;
  padding-block: 0.75rem;
  background-image: linear-gradient(
    100deg,
    rgb(var(--v-theme-app-header-start)) 0%,
    rgb(var(--v-theme-app-header-end)) 100%
  );
  color: rgb(var(--v-theme-on-surface));
}

.app-header__nav {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  flex: 1 1 auto;
  min-inline-size: 0;
}

.app-header__link {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding-block: 0.25rem;
  border: none;
  background: none;
  color: inherit;
  font: inherit;
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-decoration: none;
  cursor: pointer;
  opacity: 0.75;
  transition: opacity 0.15s ease-in-out;
}

.app-header__link:hover,
.app-header__link--active {
  opacity: 1;
}

.app-header__link--active {
  box-shadow: inset 0 -0.125rem 0 0 currentColor;
}

.app-header__menu {
  min-inline-size: 12rem;
}

.app-header__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.app-header__brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: inherit;
  text-decoration: none;
}

.app-header__mark {
  inline-size: clamp(1.75rem, 2.2vw, 2.25rem);
  block-size: clamp(1.75rem, 2.2vw, 2.25rem);
  color: rgb(var(--v-theme-primary));
  flex: 0 0 auto;
}

/* The wordmark is the one piece of the design drawn in the display family rather than in the interface one. */
.app-header__wordmark {
  font-family: var(--truth-font-display);
  font-size: clamp(1.25rem, 1.8vw, 1.75rem);
  font-weight: 500;
  letter-spacing: 0.3em;
}

/*
 * The toggle is a switch rather than a button. A v-btn lays its children out in a grid whose middle track is
 * sized by its content, so the knob has to be freed from that track: the button becomes a plain flex box and
 * the content box grows to the full width of the pill. Without this the track collapses onto the knob, the
 * grid centres it, and the transform that slides it across pushes it outside the pill.
 */
.app-header__toggle.v-btn {
  position: relative;
  display: flex;
  align-items: center;
  inline-size: 3.5rem;
  min-inline-size: 3.5rem;
  block-size: 1.75rem;
  min-block-size: 1.75rem;
  border-radius: 999rem;
  border: 0.0625rem solid rgba(var(--v-theme-on-surface), 0.5);
  background: transparent;
  padding: 0.125rem;
}

.app-header__toggle.v-btn :deep(.v-btn__content) {
  display: flex;
  flex: 1 1 auto;
  align-items: center;
  justify-content: flex-start;
  block-size: 100%;
}

.app-header__toggle.v-btn :deep(.v-btn__overlay),
.app-header__toggle.v-btn :deep(.v-btn__underlay) {
  border-radius: 999rem;
}

.app-header__toggle-knob {
  display: flex;
  align-items: center;
  justify-content: center;
  inline-size: 1.375rem;
  block-size: 1.375rem;
  border-radius: 50%;
  transition: transform 0.2s ease-in-out;
  transform: translateX(1.625rem);
  color: rgb(var(--v-theme-on-surface));
}

.app-header__toggle-knob--end {
  transform: translateX(0);
}

@media (max-width: 48rem) {
  .app-header {
    padding-inline: 1rem;
  }

  .app-header__nav {
    gap: 1rem;
  }
}
</style>
