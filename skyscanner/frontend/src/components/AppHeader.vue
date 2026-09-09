<template>
  <header class="app-header">
    <svg
      class="app-header__trail"
      viewBox="0 0 1200 120"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d="M0 84 C 90 16, 190 8, 268 44 C 340 78, 402 82, 470 44 C 540 6, 606 12, 660 44"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-dasharray="14 12"
        stroke-linecap="round"
      />
      <path
        d="M760 30 L 700 52 L 726 58 L 736 82 Z M726 58 L 760 30 L 742 66 Z"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linejoin="round"
      />
      <path
        d="M790 40 C 860 74, 960 76, 1050 44 C 1110 22, 1160 20, 1200 30"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-dasharray="14 12"
        stroke-linecap="round"
      />
    </svg>

    <div class="app-header__content">
      <RouterLink
        to="/events"
        class="app-header__brand-link"
      >
        <!--
          The badge is the same file the browser tab draws its icon from, so the tab and the page a user
          lands on carry one mark rather than two that can drift apart. It is decorative beside a wordmark
          that already says the name, which is why it is hidden from a screen reader.
        -->
        <img
          class="app-header__logo"
          src="/logo.svg"
          alt=""
          aria-hidden="true"
        >
        <span class="app-header__brand">Skyscanner</span>
      </RouterLink>

      <div class="app-header__actions">
        <v-btn
          class="app-header__toggle"
          variant="text"
          role="switch"
          :ripple="false"
          :aria-checked="isDark"
          :aria-label="isDark ? t('app.toLight') : t('app.toDark')"
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

        <!--
          The language is a pair of buttons rather than a menu, because there are two of them and each is
          written in itself: a reader who cannot read the language currently on screen can still find the
          one they came for.
        -->
        <div
          class="app-header__languages"
          role="group"
          :aria-label="t('language.label')"
        >
          <button
            v-for="name in LANGUAGES"
            :key="name"
            type="button"
            class="app-header__language"
            :class="{ 'app-header__language--active': language === name }"
            :aria-pressed="language === name"
            @click="setLanguage(name)"
          >
            {{ LANGUAGE_NAMES[name] }}
          </button>
        </div>

        <!--
          How the system is configured and who is looking at it are two different questions, and they used to
          share one button: the industries, the schema and the types all hung off the account icon, where
          nobody would look for them. The cog now holds everything that shapes the system, and the account
          icon is left to the person - which is what it will hold once there is an identity to show.
        -->
        <v-menu location="bottom end">
          <template #activator="{ props: activator }">
            <v-btn
              v-bind="activator"
              icon="mdi-cog"
              variant="text"
              :aria-label="t('app.settings')"
              :title="t('app.settings')"
            />
          </template>
          <v-list density="compact">
            <v-list-subheader>{{ t('app.settings') }}</v-list-subheader>
            <!--
              Subscriptions are hidden behind their flag rather than taken out of the menu, so the entry
              comes back with the feature instead of having to be written a second time.
            -->
            <v-list-item
              v-if="SUBSCRIPTIONS_ENABLED"
              :title="t('app.subscriptions')"
              prepend-icon="mdi-bell-outline"
              to="/subscriptions"
            />
            <v-list-item
              :title="t('app.industries')"
              prepend-icon="mdi-account-group-outline"
              to="/industries"
            />
            <!--
              A platform is a piece of equipment an event ran on rather than a shape an event takes, so it
              reads beside the industries rather than two levels inside a page about types.
            -->
            <v-list-item
              :title="t('app.platforms')"
              prepend-icon="mdi-alpha-p-box"
              to="/platforms"
            />
            <v-list-item
              :title="t('app.schema')"
              prepend-icon="mdi-table-cog"
              to="/schema"
            />
            <v-list-item
              :title="t('app.types')"
              prepend-icon="mdi-shape-outline"
              to="/types"
            />
          </v-list>
        </v-menu>

        <v-menu location="bottom end">
          <template #activator="{ props: activator }">
            <v-btn
              v-bind="activator"
              icon="mdi-account-circle-outline"
              variant="text"
              :aria-label="t('app.account')"
              :title="t('app.account')"
            />
          </template>
          <!--
            The services read the identity out of the headers the reverse proxy injects and never authenticate
            anybody themselves, so there is nothing of the person to show here yet. The menu says so rather
            than being empty, and it is where the settings of the account itself will go.
          -->
          <v-list density="compact">
            <v-list-subheader>{{ t('app.account') }}</v-list-subheader>
            <v-list-item
              :title="t('app.noAccount')"
              :subtitle="t('app.identityNote')"
              prepend-icon="mdi-account-outline"
              disabled
            />
          </v-list>
        </v-menu>
      </div>
    </div>

    <slot name="tabs" />
  </header>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'

import { LANGUAGES, LANGUAGE_NAMES, useAppTheme, useLanguage } from '@truth-platform/core-ui'
import { SUBSCRIPTIONS_ENABLED } from '@/features'

const { isDark, toggle } = useAppTheme()
const { t, language, setLanguage } = useLanguage()
</script>

<style scoped>
.app-header {
  position: relative;
  display: flex;
  flex-direction: column;
  background-image: linear-gradient(
    100deg,
    rgb(var(--v-theme-app-header-start)) 0%,
    rgb(var(--v-theme-app-header-end)) 100%
  );
  color: rgb(var(--v-theme-on-surface));
  overflow: hidden;
}

.app-header__trail {
  position: absolute;
  inset-block-start: 0;
  inset-inline: 0;
  block-size: 5rem;
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.35;
  pointer-events: none;
}

.app-header__content {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 1rem;
  padding-inline: 2rem;
  padding-block: 1.25rem 0.75rem;
}

.app-header__brand-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  text-decoration: none;
  color: inherit;
}

/*
 * The badge is sized off the wordmark beside it rather than in pixels of its own, so the pair keeps its
 * proportions as the wordmark grows with the viewport.
 */
.app-header__logo {
  inline-size: clamp(2rem, 2.7vw, 2.75rem);
  block-size: clamp(2rem, 2.7vw, 2.75rem);
  border-radius: 0.5rem;
  flex: 0 0 auto;
}

/* The wordmark is the one piece of the design drawn in the display family rather than in the interface one. */
.app-header__brand {
  font-family: var(--sky-font-display);
  font-size: clamp(1.75rem, 2.4vw, 2.5rem);
  font-weight: 400;
  letter-spacing: 0.01em;
}

.app-header__actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
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
  cursor: pointer;
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

/*
 * The two languages sit in one pill, the way the two halves of a segmented control do. Each is written in
 * itself rather than in the language currently on screen, so the switch is legible from either side of it.
 */
.app-header__languages {
  display: inline-flex;
  align-items: center;
  border: 0.0625rem solid rgba(var(--v-theme-on-surface), 0.35);
  border-radius: 999rem;
  overflow: hidden;
}

.app-header__language {
  border: none;
  background: none;
  color: inherit;
  font: inherit;
  font-size: 0.75rem;
  line-height: 1;
  padding-inline: 0.625rem;
  padding-block: 0.375rem;
  cursor: pointer;
  opacity: 0.7;
  transition:
    opacity 0.15s ease-in-out,
    background-color 0.15s ease-in-out;
}

.app-header__language:hover {
  opacity: 1;
}

.app-header__language--active {
  opacity: 1;
  background-color: rgba(var(--v-theme-on-surface), 0.16);
  font-weight: 600;
}

.app-header__toggle-knob--end {
  transform: translateX(0);
}

@media (max-width: 48rem) {
  .app-header__content {
    padding-inline: 1rem;
  }
}
</style>
