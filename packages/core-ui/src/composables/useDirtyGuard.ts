/**
 * The guard that stands between a filled in form and the click that would throw it away.
 *
 * A dialog closes on its backdrop, on its cancel button and on Escape, and every one of those is one click
 * away from losing everything that was typed. Rather than each dialog inventing its own confirmation, they
 * all route their close through `attemptClose`: a form nobody touched closes straight away, and a form that
 * carries changes raises the confirmation first and only closes once the user says so.
 */

import { ref, type Ref } from 'vue'

interface DirtyGuardOptions {
  /** Whether the form currently holds changes worth warning about. */
  isDirty: () => boolean
  /** What closing actually means for the owner - usually emitting `update:modelValue` with false. */
  close: () => void
}

interface DirtyGuard {
  /** Whether the confirmation is being shown. Bind it to `UnsavedChangesDialog`. */
  confirmOpen: Ref<boolean>
  /** Close when there is nothing to lose, ask first when there is. */
  attemptClose: () => void
  /** Leave and lose the changes, which is what the confirmation offers. */
  discard: () => void
  /** Stay on the form and keep editing. */
  cancel: () => void
}

const useDirtyGuard = (options: DirtyGuardOptions): DirtyGuard => {
  const confirmOpen = ref<boolean>(false)

  const attemptClose = (): void => {
    if (!options.isDirty()) {
      options.close()

      return
    }

    confirmOpen.value = true
  }

  const discard = (): void => {
    confirmOpen.value = false
    options.close()
  }

  const cancel = (): void => {
    confirmOpen.value = false
  }

  return { confirmOpen, attemptClose, discard, cancel }
}

export { useDirtyGuard }
export type { DirtyGuard, DirtyGuardOptions }
