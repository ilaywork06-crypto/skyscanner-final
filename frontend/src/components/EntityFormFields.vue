<template>
  <!--
    The one set of inputs that describes an entity. Both the last step of the create wizard and the dialog
    that attaches an entity to an existing event render this, so the two paths cannot drift apart into
    asking for different things about the same object.
  -->
  <div class="entity-form">
    <div class="entity-form__grid">
      <div class="entity-form__field">
        <label
          class="entity-form__label"
          :for="`${idPrefix}-type`"
        ><span class="entity-form__required">*</span>Entity Type</label>
        <v-select
          :id="`${idPrefix}-type`"
          class="entity-form__control"
          :model-value="modelValue.typeKey"
          :items="entityTypes"
          item-title="name"
          item-value="key"
          :disabled="lockType"
          density="comfortable"
          :menu-props="MENU_PROPS"
          placeholder="Pick an entity type"
          @update:model-value="patch({ typeKey: $event })"
        />
      </div>

      <div class="entity-form__field">
        <label
          class="entity-form__label"
          :for="`${idPrefix}-name`"
        >
          <span class="entity-form__required">*</span>Name
          <SkyInfoIcon label="What Name means">
            A short name that tells this entity apart from the others in the same event, for example
            Front camera telemetry.
          </SkyInfoIcon>
        </label>
        <v-text-field
          :id="`${idPrefix}-name`"
          class="entity-form__control"
          :model-value="modelValue.name"
          density="comfortable"
          placeholder="Enter name"
          @update:model-value="patch({ name: $event })"
        />
      </div>

      <!--
        Module is a vocabulary the industry declares. While it has declared none the field stays open text,
        so a system nobody configured yet is not blocked from recording where its data came from.
      -->
      <div class="entity-form__field">
        <label
          class="entity-form__label"
          :for="`${idPrefix}-module`"
        >
          Module
          <SkyInfoIcon label="What Module means">
            {{
              modules.length > 0
                ? 'The system or sensor module the data came from. The list is declared for this industry.'
                : 'The system or sensor module the data came from. This industry has declared no list yet, so any text is accepted.'
            }}
          </SkyInfoIcon>
        </label>
        <v-select
          v-if="modules.length > 0"
          :id="`${idPrefix}-module`"
          class="entity-form__control"
          :model-value="modelValue.module"
          :items="modules"
          density="comfortable"
          :menu-props="MENU_PROPS"
          placeholder="Pick a module"
          clearable
          @update:model-value="patch({ module: $event })"
        />
        <v-text-field
          v-else
          :id="`${idPrefix}-module`"
          class="entity-form__control"
          :model-value="modelValue.module ?? ''"
          density="comfortable"
          placeholder="Enter module"
          @update:model-value="patch({ module: $event.length > 0 ? $event : null })"
        />
      </div>

      <!--
        The parsed state is a claim about the files rather than a free choice, and the service refuses a
        claim the files do not support. The form therefore states the same rule up front: parsed cannot be
        picked while nothing was parsed, and cannot be escaped while the parsing products are attached.
      -->
      <div class="entity-form__field">
        <label
          class="entity-form__label"
          :for="`${idPrefix}-status`"
        >
          Status
          <SkyInfoIcon label="What Status means">
            {{ statusExplanation }}
          </SkyInfoIcon>
        </label>
        <v-select
          :id="`${idPrefix}-status`"
          class="entity-form__control"
          :model-value="modelValue.status"
          :items="statusItems"
          density="comfortable"
          :menu-props="MENU_PROPS"
          @update:model-value="patch({ status: $event })"
        />
        <span class="entity-form__hint">
          {{ statusHint }}
        </span>
      </div>

      <div class="entity-form__field">
        <label
          class="entity-form__label"
          :for="`${idPrefix}-version`"
        >
          Code version
          <SkyInfoIcon label="What Code version means">
            The version of the code that produced this data, so that a result can be traced back to what
            ran, for example v2.4.1 or the commit it was built from.
          </SkyInfoIcon>
        </label>
        <v-text-field
          :id="`${idPrefix}-version`"
          class="entity-form__control"
          :model-value="modelValue.codeVersion"
          density="comfortable"
          placeholder="Enter code version"
          @update:model-value="patch({ codeVersion: $event })"
        />
      </div>

      <div class="entity-form__field entity-form__field--wide">
        <label class="entity-form__label">
          Notes
          <SkyInfoIcon label="What Notes means">
            One note per row. Press the add button for another one, and each row is shown as its own bullet
            when the entity is read.
          </SkyInfoIcon>
        </label>
        <SkyNotesInput
          :model-value="modelValue.notes"
          placeholder="Enter a note"
          @update:model-value="patch({ notes: $event })"
        />
      </div>
    </div>

    <MetadataFieldsPanel
      :model-value="modelValue.values"
      :types="modelValue.valueTypes"
      :fields="fields"
      :context="context"
      title="Metadata fields"
      @update:model-value="patch({ values: $event })"
      @update:types="patch({ valueTypes: $event })"
    />

    <div class="entity-form__files">
      <FileDropzone
        label="Raw files"
        :files="modelValue.rawFiles"
        @update:files="patch({ rawFiles: $event })"
      />
      <FileDropzone
        label="Parsed files"
        :files="modelValue.parsedFiles"
        @update:files="patch({ parsedFiles: $event })"
      />
      <FileDropzone
        label="Additional parsing products"
        :files="modelValue.parsedAdditionalFiles"
        @update:files="patch({ parsedAdditionalFiles: $event })"
      />
    </div>
  </div>
</template>

<script lang="ts">
import type { EntityStatus, FieldType, JsonValue } from '@/models/common'
import { SkyDropzone as FileDropzone, SkyInfoIcon, SkyNotesInput, humanizeKey } from '@skyscanner/sky-ui'
import type { EntityType } from '@/models/entity'
import type { FieldDefinition } from '@/models/field'

/** Everything one entity is described by, in the shape both callers keep it in. */
interface EntityFormValue {
  typeKey: string | null
  name: string
  module: string | null
  codeVersion: string
  status: EntityStatus
  notes: string
  values: Record<string, JsonValue>
  /** What kind of value every dynamic key holds, which a key invented on the spot carries with it. */
  valueTypes: Record<string, FieldType>
  rawFiles: File[]
  parsedFiles: File[]
  parsedAdditionalFiles: File[]
}

interface Props {
  modelValue: EntityFormValue
  entityTypes: EntityType[]
  fields: FieldDefinition[]
  modules?: string[]
  lockType?: boolean
  idPrefix?: string
  /**
   * How many parsed files the entity already carries in the system. A newly created entity carries none,
   * while an entity being edited may have been given its parsing products long before this form was opened.
   */
  storedParsedCount?: number
  /**
   * The values of the event this entity belongs to, so that an entity field may be asked for only when the
   * event says something in particular. The form passes it straight on to the metadata panel.
   */
  context?: Record<string, JsonValue>
}

interface Emits {
  (event: 'update:modelValue', value: EntityFormValue): void
}

/** One option of the status selector, in the shape Vuetify reads a disabled option from. */
interface StatusItem {
  title: string
  value: EntityStatus
  props: { disabled: boolean }
}

const STATUS_OPTIONS: EntityStatus[] = ['raw', 'parsing', 'partially_parsed', 'parsed', 'failed']

/* The states that claim the parsing products exist, which is a claim only the attached files can support. */
const PARSED_STATUSES: EntityStatus[] = ['parsed', 'partially_parsed']

/** What an entity falls back to when the parsed files that made it parsed are taken away again. */
const UNPARSED_STATUS: EntityStatus = 'raw'

/*
 * Vuetify reads an overlay width by running parseFloat over it, so the limit has to be a number of pixels.
 * Without one the menu grows to its longest option and ends up far wider than the control it belongs to.
 */
const MENU_MAX_WIDTH_PX = 320
const MENU_PROPS = { maxWidth: MENU_MAX_WIDTH_PX }

/**
 * Build the empty entity a fresh form starts from.
 */
const emptyEntityForm = (): EntityFormValue => ({
  typeKey: null,
  name: '',
  module: null,
  codeVersion: '',
  status: 'raw',
  notes: '',
  values: {},
  valueTypes: {},
  rawFiles: [],
  parsedFiles: [],
  parsedAdditionalFiles: [],
})

export type { EntityFormValue }
export { emptyEntityForm }
</script>

<script setup lang="ts">
import { computed, watch } from 'vue'

import MetadataFieldsPanel from '@/components/MetadataFieldsPanel.vue'

const props = withDefaults(defineProps<Props>(), {
  modules: () => [],
  lockType: false,
  idPrefix: 'entity',
  storedParsedCount: 0,
  context: () => ({}),
})
const emit = defineEmits<Emits>()

/* Parsed products count whether they are already stored or were only just picked in this form. */
const parsedFileCount = computed<number>(() => props.storedParsedCount + props.modelValue.parsedFiles.length)

const isParsed = computed<boolean>(() => parsedFileCount.value > 0)

const statusItems = computed<StatusItem[]>(() =>
  STATUS_OPTIONS.map((status) => ({
    title: humanizeKey(status),
    value: status,
    props: { disabled: PARSED_STATUSES.includes(status) && !isParsed.value },
  })),
)

const statusHint = computed<string>(() =>
  isParsed.value
    ? 'This entity carries parsed files. Say partially parsed when only some of the data came through.'
    : 'Parsed cannot be chosen while no parsed files are attached. Uploading parsed files moves the entity to parsed on its own.',
)

const statusExplanation = computed<string>(() =>
  isParsed.value
    ? `The status follows the files: ${parsedFileCount.value} parsed file(s) are attached, so the entity is parsed - or partially parsed, when only some of what was recorded came through.`
    : 'The status follows the files. Raw is data as it arrived, parsing is a run in progress, failed is a run that did not produce anything, and the parsed states are only reachable by attaching the parsed files themselves.',
)


let pending: EntityFormValue = props.modelValue

watch(
  () => props.modelValue,
  (value) => {
    pending = value
  },
)

/**
 * Hand the parent a whole new value with one part of it replaced, so the form owns no state of its own.
 */
const patch = (changes: Partial<EntityFormValue>) => {
  pending = { ...pending, ...changes }
  emit('update:modelValue', pending)
}

/*
 * The status is kept in step with the files rather than left to disagree with them: attaching the parsing
 * products makes the entity parsed, and taking them away again makes a claim the service would refuse, so
 * the status returns to raw with them.
 */
watch(
  () => [isParsed.value, props.modelValue.status] as const,
  ([parsed, status]) => {
    if (parsed && !PARSED_STATUSES.includes(status)) {
      patch({ status: 'parsed' })

      return
    }

    if (!parsed && PARSED_STATUSES.includes(status)) {
      patch({ status: UNPARSED_STATUS })
    }
  },
)
</script>

<style scoped>
.entity-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.entity-form__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 1rem;
}

.entity-form__field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  min-inline-size: 0;
}

.entity-form__field--wide {
  grid-column: 1 / -1;
}

/*
 * The labels of neighbouring fields have to occupy the same height whether or not they carry an information
 * icon, otherwise the control underneath one of them starts lower and the pair reads as two different sizes.
 */
.entity-form__label {
  font-size: 0.875rem;
  line-height: 1.5;
  min-block-size: 1.5rem;
}

.entity-form__required {
  color: rgb(var(--v-theme-error));
  margin-inline-end: 0.125rem;
}

/* Every control of the form is the same height, so a selector never towers over the one beside it. */
.entity-form__control :deep(.v-input__control) {
  min-block-size: 3rem;
}

.entity-form__hint {
  font-size: 0.75rem;
  opacity: 0.65;
}

.entity-form__files {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  gap: 1rem;
}
</style>
