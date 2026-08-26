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
          :modules="modules"
          :lock-type="isEdit || lockType"
          :stored-parsed-count="storedParsedCount"
          :context="eventValues"
          id-prefix="add-entity"
        />

        <!--
          The files an entity already carries. They used to be add only, so a raw file uploaded by mistake or
          a parsing product that was superseded stayed on the entity for good. Marking one here detaches it
          as part of this very edit, under the same reason, and the history records it beside the rest.
        -->
        <div
          v-if="isEdit && entity !== null"
          class="add-entity__files"
        >
          <StoredFilesEditor
            v-for="set in storedFileSets"
            :key="set.role"
            :model-value="keptFiles[set.role]"
            :stored="set.files"
            :label="set.label"
            @update:model-value="keepFiles(set.role, $event)"
          />
          <p
            v-if="duplicateWarning.length > 0"
            class="add-entity__duplicate"
          >
            {{ duplicateWarning }}
          </p>
        </div>

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
import type { Artifact, JsonValue } from '@/models/common'
import type { EntityResponse, EntityType } from '@/models/entity'
import type { EventDetail } from '@/models/event'
import type { FieldDefinition } from '@/models/field'

/** The three roles a file plays for an entity, each with its own stored list and its own dropzone. */
type FileRole = 'raw' | 'parsed' | 'parsedAdditional'

/** One stored file set as the editor renders it: what it is called and what it currently holds. */
interface StoredFileSet {
  role: FileRole
  label: string
  files: Artifact[]
}

/** Which form field, stored list and bucket folder each role answers to, in one place rather than three. */
const FILE_ROLES: { role: FileRole; label: string; folder: string }[] = [
  { role: 'raw', label: 'Raw files', folder: 'raw_files' },
  { role: 'parsed', label: 'Parsed files', folder: 'parsed_files' },
  { role: 'parsedAdditional', label: 'Additional parsing products', folder: 'parsed_additional_files' },
]

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
const DUPLICATE_FILES = 'A file cannot be attached twice under the same name'
</script>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import EntityFormFields, { emptyEntityForm, type EntityFormValue } from '@/components/EntityFormFields.vue'
import StoredFilesEditor from '@/components/StoredFilesEditor.vue'
import UnsavedChangesDialog from '@/components/UnsavedChangesDialog.vue'
import { useDirtyGuard } from '@/composables/useDirtyGuard'
import { useSnackbar } from '@/composables/useSnackbar'
import { useIndustries } from '@/composables/useIndustries'
import { addEntity, updateEntity } from '@/requests/entities'
import { listEntityTypes, listFields } from '@/requests/schema'
import { uploadArtifacts } from '@/requests/storage'
import { collisionMessage } from '@/utils/artifacts'
import { toMetadataAttributes, toValueMap, toValueTypeMap } from '@/utils/rows'

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

/* The stored files of each role that will survive the edit, which starts out as every one of them. */
const keptFiles = ref<Record<FileRole, Artifact[]>>({ raw: [], parsed: [], parsedAdditional: [] })

const keepFiles = (role: FileRole, files: Artifact[]) => {
  keptFiles.value = { ...keptFiles.value, [role]: files }
}

/* What the form was filled with when it opened, which is what an edit is measured against. */
const openedWith = ref<string>('')

const isEdit = computed<boolean>(() => props.entity !== null)

const modules = computed<string[]>(() => findIndustry(props.event.industry)?.modules ?? [])

/*
 * The parsed products the entity already carries decide whether parsed can be chosen at all, and the entity
 * being attached for the first time carries none of them yet. What counts is what survives this edit: an
 * entity whose parsed products are all being detached is on its way back to raw, and the service reads it
 * the same way.
 */
const storedParsedCount = computed<number>(() =>
  props.entity === null ? 0 : keptFiles.value.parsed.length,
)

/* The three stored sets as the editors render them, in the order the dropzones underneath ask for them. */
const storedFileSets = computed<StoredFileSet[]>(() => {
  const entity = props.entity
  if (entity === null) {
    return []
  }

  return [
    { role: 'raw', label: 'Stored raw files', files: entity.raw_files },
    { role: 'parsed', label: 'Stored parsed files', files: entity.parsed_files },
    {
      role: 'parsedAdditional',
      label: 'Stored additional parsing products',
      files: entity.parsed_additional_files,
    },
  ]
})

/*
 * A picked file that the entity already holds in the same role under the same name is refused rather than
 * stored beside it. Files marked for removal do not count, so replacing one is take the old off, add the new.
 */
const duplicateWarning = computed<string>(() => {
  const picked: Record<FileRole, File[]> = {
    raw: form.value.rawFiles,
    parsed: form.value.parsedFiles,
    parsedAdditional: form.value.parsedAdditionalFiles,
  }

  for (const role of FILE_ROLES) {
    const message = collisionMessage(keptFiles.value[role.role], picked[role.role], role.folder, role.label)
    if (message.length > 0) {
      return message
    }
  }

  return ''
})

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
    /* Detaching a stored file is a change like any other, so it counts towards a dirty form. */
    keptFiles: FILE_ROLES.map((role) => keptFiles.value[role.role].map((file) => file.id)),
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

  if (duplicateWarning.value.length > 0) {
    return DUPLICATE_FILES
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
  const entity = props.entity
  reason.value = ''
  /*
   * The file sets are taken hold of before anything is awaited: the dialog renders as soon as it is opened,
   * and a list that is still empty at that moment would show every stored file struck through for a frame.
   */
  keptFiles.value = {
    raw: [...(entity?.raw_files ?? [])],
    parsed: [...(entity?.parsed_files ?? [])],
    parsedAdditional: [...(entity?.parsed_additional_files ?? [])],
  }

  try {
    entityTypes.value = await listEntityTypes(props.event.industry)
  } catch (error) {
    reportError(error)
  }

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
      module: entity.module,
      codeVersion: entity.code_version ?? '',
      status: entity.status,
      notes: entity.notes,
      values: toValueMap(entity.metadata),
      valueTypes: toValueTypeMap(entity.metadata),
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
        module: form.value.module,
        code_version: form.value.codeVersion.length > 0 ? form.value.codeVersion : null,
        status: form.value.status,
        notes: form.value.notes,
        upload_source: 'manual',
        requested_at: null,
        received_at: null,
        raw_files: raw,
        parsed_files: parsed,
        parsed_additional_files: additional,
        metadata: toMetadataAttributes(form.value.values, form.value.valueTypes),
      })
      notify('The entity was added', 'success')
    } else {
      await updateEntity(props.event.id, entity.id, {
        reason: reason.value.trim(),
        name: form.value.name.trim(),
        module: form.value.module,
        code_version: form.value.codeVersion.length > 0 ? form.value.codeVersion : null,
        status: form.value.status,
        notes: form.value.notes,
        /* What survives the edit plus what was just added, which is how a removal reaches the service. */
        raw_files: [...keptFiles.value.raw, ...raw],
        parsed_files: [...keptFiles.value.parsed, ...parsed],
        parsed_additional_files: [...keptFiles.value.parsedAdditional, ...additional],
        metadata: toMetadataAttributes(form.value.values, form.value.valueTypes),
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

.add-entity__files {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-radius: 0.75rem;
  padding: 1rem;
}

.add-entity__duplicate {
  font-size: 0.8125rem;
  color: rgb(var(--v-theme-error));
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
