/**
 * How far along an upload is, so that a wait measured in minutes is a wait somebody can watch.
 *
 * A pick of a few small files lands before anybody could look at a bar. A file large enough to be written
 * part by part does not: it may take a quarter of an hour, and a dialog that says nothing for a quarter of
 * an hour is a dialog people close and try again from the beginning. The reporting is per pick rather than
 * per file, because what a user is waiting for is the whole of what they dropped in.
 */

import { computed, ref } from 'vue'

import { formatBytes } from '@truth-platform/core-ui'

import type { UploadProgress } from '@/models/storage'

/** Below this a pick lands quickly enough that a bar would flash rather than inform. */
const WORTH_SHOWING_BYTES = 8 * 1024 * 1024

const FULL_PERCENT = 100

/**
 * Track the progress of the uploads one dialog is running.
 *
 * A dialog rarely runs one upload. The create wizard writes the raw files, the parsed files and the products
 * of the parsing side by side, and a single reporter shared between the three would show whichever of them
 * spoke last - a bar that jumps backwards as often as forwards. Each pick is therefore given a reporter of
 * its own and the three are added together, so the bar answers the only question being asked: how much of
 * what I dropped in has actually gone.
 *
 * :return: The state a progress bar renders from, the per pick reporter factory, and the reset.
 */
const useUploadProgress = () => {
  const sources = ref<UploadProgress[]>([])

  /**
   * Take a reporter for one pick, which the upload is handed and reports its own progress through.
   *
   * :return: The handler that belongs to this pick alone.
   */
  const track = (): ((update: UploadProgress) => void) => {
    const slot = sources.value.length
    sources.value = [...sources.value, { written: 0, total: 0, name: '' }]

    return (update: UploadProgress): void => {
      const next = [...sources.value]
      next[slot] = update
      sources.value = next
    }
  }

  const reset = (): void => {
    sources.value = []
  }

  const written = computed<number>(() =>
    sources.value.reduce((sum, source) => sum + source.written, 0),
  )

  const total = computed<number>(() => sources.value.reduce((sum, source) => sum + source.total, 0))

  /* A pick small enough to land in a moment is not worth interrupting the dialog for. */
  const visible = computed<boolean>(() => total.value >= WORTH_SHOWING_BYTES)

  const percent = computed<number>(() =>
    total.value === 0 ? 0 : Math.min((written.value / total.value) * FULL_PERCENT, FULL_PERCENT),
  )

  /* Which file is named is whichever one is still being written, since the finished ones say nothing. */
  const label = computed<string>(() => {
    const working = sources.value.find((source) => source.total > 0 && source.written < source.total)

    return `${formatBytes(written.value)} of ${formatBytes(total.value)}${
      working === undefined ? '' : ` · ${working.name}`
    }`
  })

  return { track, reset, visible, percent, label }
}

export { useUploadProgress }
