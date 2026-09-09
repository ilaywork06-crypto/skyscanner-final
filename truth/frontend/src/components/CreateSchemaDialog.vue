<template>
  <v-dialog
    :model-value="modelValue"
    max-width="62rem"
    scrollable
    persistent
    @update:model-value="close"
  >
    <v-card>
      <v-card-title>{{ revisedSchema === null ? t('schemas.declare') : t('schemas.reviseNamed', { name: revisedSchema.name }) }}</v-card-title>

      <v-card-text class="schema-form">
        <template v-if="revisedSchema === null">
          <div class="schema-form__field">
            <label
              class="schema-form__label"
              for="schema-name"
            ><span class="schema-form__required">*</span> Name</label>
            <v-text-field
              id="schema-name"
              v-model="name"
              :placeholder="t('schemas.namePlaceholder')"
            />
          </div>

          <div class="schema-form__field">
            <label
              class="schema-form__label"
              for="schema-description"
            >Description</label>
            <v-textarea
              id="schema-description"
              v-model="description"
              :placeholder="t('schemas.descriptionPlaceholder')"
              rows="2"
              auto-grow
            />
          </div>
        </template>

        <div
          v-else
          class="schema-form__field"
        >
          <label
            class="schema-form__label"
            for="schema-reason"
          ><span class="schema-form__required">*</span> Reason for this revision</label>
          <v-text-field
            id="schema-reason"
            v-model="revisionReason"
            :placeholder="t('schemas.reasonPlaceholder')"
          />
        </div>

        <v-divider />

        <SchemeBuilder
          :scheme="scheme"
          @update:scheme="scheme = $event"
        />

        <!--
          The service takes the industries of a schema as numeric identifiers and hands them back only as
          uuids, so there is no way from here to name one. Sending none is what leaves a schema usable by
          every industry, which is said here rather than left as a silent omission.
        -->
        <v-alert
          v-if="revisedSchema === null"
          type="info"
          variant="tonal"
          density="compact"
        >
          This schema will be available to every industry. The API takes a schema's industries as numbers it
          never hands out, so they cannot be chosen from here yet.
        </v-alert>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn
          variant="text"
          @click="close"
        >
          {{ t('identity.cancel') }}
        </v-btn>
        <v-btn
          color="primary"
          :loading="saving"
          :disabled="!canSave"
          @click="save"
        >
          {{ revisedSchema === null ? t('create.create') : t('schemas.revise') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import type { SchemaDetail } from '@/models/schema'

interface Props {
  modelValue: boolean
  /** The schema being revised, or nothing when a new one is being declared. */
  revisedSchema?: SchemaDetail | null
}

interface Emits {
  (event: 'update:modelValue', open: boolean): void
  (event: 'created', schemaId: string): void
}

/** The kind of schema, which the service holds as a number and offers no vocabulary for. */
const DEFAULT_SCHEMA_TYPE = 0
</script>

<script setup lang="ts">
import { useLanguage, useSnackbar } from '@truth-platform/core-ui'
import { computed, ref, watch } from 'vue'

import SchemeBuilder from '@/components/SchemeBuilder.vue'
import type { Scheme } from '@/models/scheme'
import { createSchema, createSchemaRevision } from '@/requests/schemas'
import { readCreator } from '@/utils/identity'
import { readScheme, writeScheme } from '@/utils/scheme'

const props = withDefaults(defineProps<Props>(), { revisedSchema: null })
const emit = defineEmits<Emits>()

const { t } = useLanguage()

const { notify, reportError } = useSnackbar()

const name = ref<string>('')
const description = ref<string>('')
const revisionReason = ref<string>('')
const scheme = ref<Scheme>({ fields: [] })
const saving = ref<boolean>(false)

const canSave = computed<boolean>(() => {
  if (saving.value) {
    return false
  }

  /* Every attribute has to be keyed, or it would be stored under nothing and read back as nothing. */
  const keys = scheme.value.fields.map((field) => field.key.trim())
  if (keys.some((key) => key.length === 0) || new Set(keys).size !== keys.length) {
    return false
  }

  /* An enumeration with nothing to choose from is a field nobody can fill in. */
  if (scheme.value.fields.some((field) => field.type === 'enum' && field.options.length === 0)) {
    return false
  }

  return props.revisedSchema === null
    ? name.value.trim().length > 0
    : revisionReason.value.trim().length > 0
})

/* Reopening starts from the schema being revised, or from an empty declaration for a new one. */
watch(
  () => props.modelValue,
  (open) => {
    if (!open) {
      return
    }

    const revised = props.revisedSchema
    name.value = ''
    description.value = ''
    revisionReason.value = ''
    scheme.value = revised === null ? { fields: [] } : readScheme(revised.scheme)
  },
)

const close = () => {
  emit('update:modelValue', false)
}

const save = async () => {
  saving.value = true
  try {
    const revised = props.revisedSchema
    const schemaId =
      revised === null
        ? await createSchema({
            name: name.value.trim(),
            description: description.value.trim(),
            type: DEFAULT_SCHEMA_TYPE,
            scheme: writeScheme(scheme.value),
            creator: readCreator(),
            /* Sent empty on purpose - see the note in the dialog. */
            industries: [],
          })
        : await createSchemaRevision(revised.id, {
            creator: readCreator(),
            revision_reason: revisionReason.value.trim(),
            scheme: writeScheme(scheme.value),
          })

    notify(revised === null ? `${name.value.trim()} was declared` : `${revised.name} was revised`, 'success')
    emit('created', schemaId)
    close()
  } catch (error) {
    reportError(error)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.schema-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.schema-form__field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.schema-form__label {
  font-size: 0.8125rem;
  font-weight: 500;
}

.schema-form__required {
  color: rgb(var(--v-theme-error));
}
</style>
