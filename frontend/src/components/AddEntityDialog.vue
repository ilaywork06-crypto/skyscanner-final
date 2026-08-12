<template>
  <v-dialog
    :model-value="modelValue"
    max-width="56rem"
    scrollable
    @update:model-value="attemptClose"
  >
    <v-card class="add-entity">
      <v-card-title class="add-entity__title">
        {{ isEdit ? 'Edit the entity' : 'Add an entity' }}
      </v-card-title>

      <v-card-text class="add-entity__body">
        <EntityFormFields
          v-model="form"
          :entity-types="entityTypes"
          :fields="fields"
          :origins="origins"
          :lock-type="isEdit || lockType"
          :stored-parsed-count="storedParsedCount"
          :context="eventValues"
          id-prefix="add-entity"
        />

        <!-- Only a change to something that already exists has a history to explain. -->
        <div
          v-if="isEdit"
          class="add-entity__reason"
        >
          <label
            class="add-entity__label"
            for="add-entity-reason"
          ><span class="add-entity__required">*</span>Reason for this edit</label>
          <v-text-field
            id="add-entity-reason"
            v-model="reason"
            placeholder="For example: the parsed products arrived from the parsing run"
          />
        </div>
      </v-card-text>

      <v-card-actions class="add-entity__actions">
        <!-- A button that refuses to be pressed without saying why reads as a broken button. -->
        <span
          v-if="blockedReason.length > 0"
          class="add-entity__blocked"
        >
          {{ blockedReason }}
        </span>
        <v-spacer />
        <v-btn
          variant="text"
          @click="attemptClose"
        >
          Cancel
        </v-btn>
        <v-btn
          color="primary"
          :loading="saving"
          :disabled="!canSave || saving"
          @click="submit"
        >
          {{ isEdit ? 'Save' : 'Add' }}
        </v-btn>
      </v-card-actions>
    </v-card>

    <UnsavedChangesDialog
      v-model="confirmOpen"
      @discard="discard"
    />
  </v-dialog>
</template>

<script lang="ts">
import type { JsonValue } from '@/models/common'
import type { EntityResponse, EntityType } from '@/models/entity'
import type { EventDetail } from '@/models/event'
import type { FieldDefinition } from '@/models/field'

interface Props {
  modelValue: boolean
  event: EventDetail
  /** The entity being changed, or null while a new one is being attached to the event. */
  entity?: EntityResponse | null
  defaultTypeKey?: string | null
  /** Keep the type selector shut even for a new entity, for a caller that has already decided the type. */
  lockType?: boolean
}

interface Emits {
  (event: 'update:modelValue', value: boolean): void
  (event: 'added'): void
}

/** What the user is told while the button is refusing to be pressed. */
const NAME_MISSING = 'A type and a name are needed'
const NOTHING_CHANGED = 'Nothing has changed yet'
const REASON_MISSING = 'A reason is needed before this can be saved'
</script>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import EntityFormFields, { emptyEntityForm, type EntityFormValue } from '@/components/EntityFormFields.vue'
import UnsavedChangesDialog from '@/components/UnsavedChangesDialog.vue'
import { useDirtyGuard } from '@/composables/useDirtyGuard'
import { useSnackbar } from '@/composables/useSnackbar'
import { useIndustries } from '@/composables/useIndustries'
import { addEntity, updateEntity } from '@/requests/entities'
import { listEntityTypes, listFields } from '@/requests/schema'
import { uploadArtifacts } from '@/requests/storage'
import { toMetadataAttributes, toValueMap } from '@/utils/rows'

const props = withDefaults(defineProps<Props>(), {
  entity: null,
  defaultTypeKey: null,
  lockType: false,
})
const emit = defineEmits<Emits>()

const { notify, reportError } = useSnackbar()
const { findIndustry } = useIndustries()

const entityTypes = ref<EntityType[]>([])
const fields = ref<FieldDefinition[]>([])
const form = ref<EntityFormValue>(emptyEntityForm())
const reason = ref<string>('')
const saving = ref<boolean>(false)

/* What the form was filled with when it opened, which is what an edit is measured against. */
const openedWith = ref<string>('')

const isEdit = computed<boolean>(() => props.entity !== null)

const origins = computed<string[]>(() => findIndustry(props.event.industry)?.entity_origins ?? [])

/*
 * The parsed products the entity already carries decide whether parsed can be chosen at all, and the entity
 * being attached for the first time carries none of them yet.
 */
const storedParsedCount = computed<number>(() => props.entity?.parsed_files.length ?? 0)

/* The values of the owning event, so that an entity field may be asked for only when the event says so. */
const eventValues = computed<Record<string, JsonValue>>(() => toValueMap(props.event.metadata))

/**
 * Describe what the form holds as one comparable string, so that an edit that changes nothing can be told
 * from one that does. Files carry no value equality, so a picked file is described by what identifies it.
 */
const snapshot = (): string =>
  JSON.stringify({
    ...form.value,
    rawFiles: form.value.rawFiles.map((file) => `${file.name}:${file.size}`),
    parsedFiles: form.value.parsedFiles.map((file) => `${file.name}:${file.size}`),
    parsedAdditionalFiles: form.value.parsedAdditionalFiles.map((file) => `${file.name}:${file.size}`),
  })

const isDirty = computed<boolean>(() => snapshot() !== openedWith.value)

/*
 * A nameless entity is indistinguishable from the next one, and repeatedly pressing Add used to create a
 * row of them, so the name is required. An edit is refused on top of that when it would change nothing:
 * saving one only bumps the timestamp, mails the subscribers and leaves a line in the history for nothing.
 */
const blockedReason = computed<string>(() => {
  if (form.value.typeKey === null || form.value.name.trim().length === 0) {
    return NAME_MISSING
  }

  if (!isEdit.value) {
    return ''
  }

  if (!isDirty.value) {
    return NOTHING_CHANGED
  }

  return reason.value.trim().length === 0 ? REASON_MISSING : ''
})

const canSave = computed<boolean>(() => blockedReason.value.length === 0)

const loadFields = async (typeKey: string | null): Promise<void> => {
  if (typeKey === null) {
    fields.value = []

    return
  }

  try {
    fields.value = await listFields({
      scope: 'entity',
      industry: props.event.industry,
      entityType: typeKey,
    })
  } catch (error) {
    reportError(error)
  }
}

const fill = async (): Promise<void> => {
  reason.value = ''

  try {
    entityTypes.value = await listEntityTypes(props.event.industry)
  } catch (error) {
    reportError(error)
  }

  const entity = props.entity
  if (entity === null) {
    const preselected = entityTypes.value.find(
      (type) => type.key === props.defaultTypeKey || type.name === props.defaultTypeKey,
    )
    form.value = {
      ...emptyEntityForm(),
      typeKey: preselected?.key ?? entityTypes.value[0]?.key ?? null,
    }
  } else {
    form.value = {
      ...emptyEntityForm(),
      typeKey: entity.object_type_key.length > 0 ? entity.object_type_key : null,
      name: entity.name,
      origin: entity.origin,
      codeVersion: entity.code_version ?? '',
      status: entity.status,
      notes: entity.notes,
      values: toValueMap(entity.metadata),
    }
  }

  openedWith.value = snapshot()

  await loadFields(form.value.typeKey)
}

const close = () => {
  emit('update:modelValue', false)
}

/* Whatever was typed into the reason is worth keeping as well, so it counts towards leaving with changes. */
const { confirmOpen, attemptClose, discard } = useDirtyGuard({
  isDirty: () => isDirty.value || reason.value.trim().length > 0,
  close,
})

const submit = async (): Promise<void> => {
  const typeKey = form.value.typeKey
  if (typeKey === null || !canSave.value || saving.value) {
    return
  }

  saving.value = true
  try {
    const [raw, parsed, additional] = await Promise.all([
      uploadArtifacts(form.value.rawFiles, {
        ownerKind: 'entities',
        ownerId: props.event.id,
        kind: 'raw',
        folder: 'raw_files',
        descriptor: 'Raw files of the entity',
      }),
      uploadArtifacts(form.value.parsedFiles, {
        ownerKind: 'entities',
        ownerId: props.event.id,
        kind: 'parsed',
        folder: 'parsed_files',
        descriptor: 'Parsed files of the entity',
      }),
      uploadArtifacts(form.value.parsedAdditionalFiles, {
        ownerKind: 'entities',
        ownerId: props.event.id,
        kind: 'parsed_additional',
        folder: 'parsed_additional_files',
        descriptor: 'Extra products of the parsing',
      }),
    ])

    const entity = props.entity
    if (entity === null) {
      await addEntity(props.event.id, {
        name: form.value.name.trim(),
        entity_type_key: typeKey,
        origin: form.value.origin,
        code_version: form.value.codeVersion.length > 0 ? form.value.codeVersion : null,
        status: form.value.status,
        notes: form.value.notes,
        upload_source: 'manual',
        requested_at: null,
        received_at: null,
        raw_files: raw,
        parsed_files: parsed,
        parsed_additional_files: additional,
        metadata: toMetadataAttributes(form.value.values),
      })
      notify('The entity was added', 'success')
    } else {
      await updateEntity(props.event.id, entity.id, {
        reason: reason.value.trim(),
        name: form.value.name.trim(),
        origin: form.value.origin,
        code_version: form.value.codeVersion.length > 0 ? form.value.codeVersion : null,
        status: form.value.status,
        notes: form.value.notes,
        raw_files: [...entity.raw_files, ...raw],
        parsed_files: [...entity.parsed_files, ...parsed],
        parsed_additional_files: [...entity.parsed_additional_files, ...additional],
        metadata: toMetadataAttributes(form.value.values),
      })
      notify('The entity was updated', 'success')
    }

    emit('added')
    close()
  } catch (error) {
    reportError(error)
  } finally {
    saving.value = false
  }
}

/*
 * The dialog is mounted lazily by its parent, so on the very first use it is created with the flag already
 * true and a plain watcher would never run - which left the preselected entity type unresolved until the
 * dialog had been closed and opened a second time. Running the watcher immediately fills it on that first
 * open as well.
 */
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      void fill()
    }
  },
  { immediate: true },
)

watch(
  () => form.value.typeKey,
  (typeKey) => {
    void loadFields(typeKey)
  },
)
</script>

<style scoped>
.add-entity {
  background-color: rgb(var(--v-theme-surface));
}

.add-entity__title {
  font-size: 1.25rem;
  font-weight: 600;
}

.add-entity__body {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-block-size: 65vh;
}

.add-entity__reason {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.add-entity__label {
  font-size: 0.875rem;
}

.add-entity__required {
  color: rgb(var(--v-theme-error));
  margin-inline-end: 0.125rem;
}

.add-entity__actions {
  padding-inline: 1rem;
}

.add-entity__blocked {
  font-size: 0.8125rem;
  opacity: 0.7;
}
</style>
