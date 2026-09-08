/**
 * The composable that loads the industries once and shares them with the tabs, the chips and the create wizard.
 */

import { computed, ref, type ComputedRef, type Ref } from 'vue'

import type { Industry } from '@/models/industry'
import { listIndustries } from '@/requests/schema'

interface IndustriesState {
  industries: Ref<Industry[]>
  loading: Ref<boolean>
  totalEvents: ComputedRef<number>
  load: (force?: boolean) => Promise<void>
  findIndustry: (key: string) => Industry | undefined
}

const industries = ref<Industry[]>([])
const loading = ref<boolean>(false)
let loaded = false

/**
 * Expose the industries of the organisation together with the loader that fills them once.
 */
const useIndustries = (): IndustriesState => {
  const totalEvents = computed<number>(() =>
    industries.value.reduce((sum, industry) => sum + industry.event_count, 0),
  )

  const load = async (force = false): Promise<void> => {
    if (loaded && !force) {
      return
    }

    loading.value = true
    try {
      industries.value = await listIndustries()
      loaded = true
    } finally {
      loading.value = false
    }
  }

  const findIndustry = (key: string): Industry | undefined => industries.value.find((industry) => industry.key === key)

  return { industries, loading, totalEvents, load, findIndustry }
}

export type { IndustriesState }
export { useIndustries }
