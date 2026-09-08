/**
 * The composable behind the single notification bar of the application, shared by every page and dialog.
 */

import { ref, type Ref } from 'vue'

type SnackbarTone = 'success' | 'error' | 'info' | 'warning'

interface SnackbarState {
  visible: Ref<boolean>
  message: Ref<string>
  tone: Ref<SnackbarTone>
  notify: (message: string, tone?: SnackbarTone) => void
  reportError: (error: unknown) => void
}

const visible = ref<boolean>(false)
const message = ref<string>('')
const tone = ref<SnackbarTone>('info')

/**
 * Expose the shared notification bar together with the two ways of raising a message.
 */
const useSnackbar = (): SnackbarState => {
  const notify = (text: string, level: SnackbarTone = 'info') => {
    message.value = text
    tone.value = level
    visible.value = true
  }

  const reportError = (error: unknown) => {
    notify(error instanceof Error ? error.message : 'Something went wrong', 'error')
  }

  return { visible, message, tone, notify, reportError }
}

export type { SnackbarState, SnackbarTone }
export { useSnackbar }
