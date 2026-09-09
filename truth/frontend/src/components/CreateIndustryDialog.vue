<template>
  <v-dialog
    :model-value="modelValue"
    max-width="32rem"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title>{{ t('industry.create') }}</v-card-title>
      <v-card-text class="industry-form">
        <div class="industry-form__field">
          <label
            class="industry-form__label"
            for="industry-name"
          ><span class="industry-form__required">*</span> {{ t('industry.name') }}</label>
          <v-text-field
            id="industry-name"
            v-model="name"
            :placeholder="t('industry.namePlaceholder')"
            autofocus
          />
        </div>

        <div class="industry-form__field">
          <label
            class="industry-form__label"
            for="industry-description"
          >{{ t('industry.description') }}</label>
          <v-textarea
            id="industry-description"
            v-model="description"
            :placeholder="t('industry.descriptionPlaceholder')"
            rows="3"
            auto-grow
          />
        </div>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn
          variant="text"
          @click="emit('update:modelValue', false)"
        >
          {{ t('identity.cancel') }}
        </v-btn>
        <v-btn
          color="primary"
          :loading="saving"
          :disabled="name.trim().length === 0 || saving"
          @click="create"
        >
          {{ t('create.create') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
interface Props {
  modelValue: boolean
}

interface Emits {
  (event: 'update:modelValue', open: boolean): void
  (event: 'created', industryId: string): void
}
</script>

<script setup lang="ts">
import { useLanguage, useSnackbar } from '@truth-platform/core-ui'
import { ref, watch } from 'vue'

import { createIndustry } from '@/requests/industries'
import { readCreator } from '@/utils/identity'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { notify, reportError } = useSnackbar()
const { t } = useLanguage()

const name = ref<string>('')
const description = ref<string>('')
const saving = ref<boolean>(false)

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      name.value = ''
      description.value = ''
    }
  },
)

const create = async () => {
  if (name.value.trim().length === 0) {
    return
  }

  saving.value = true
  try {
    const industryId = await createIndustry({
      name: name.value.trim(),
      description: description.value.trim(),
      creator: readCreator(),
    })

    notify(t('industry.created'), 'success')
    emit('created', industryId)
    emit('update:modelValue', false)
  } catch (error) {
    reportError(error)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.industry-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.industry-form__field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.industry-form__label {
  font-size: 0.8125rem;
  font-weight: 500;
}

.industry-form__required {
  color: rgb(var(--v-theme-error));
}
</style>
