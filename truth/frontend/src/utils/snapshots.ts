/**
 * Keeping a record of what the register looked like at a moment, held in the browser.
 *
 * The design asks for the history of the table to be preserved, and the API stores nothing of the sort - it
 * has no snapshot endpoint, and no endpoint that reads an assumption as it stood at an earlier revision. What
 * can honestly be offered is therefore a local one: the rows on screen are copied into this browser's own
 * storage, and can be read back and compared against the register as it stands now.
 *
 * A snapshot is deliberately never presented as a record the organisation holds. It lives in one browser, it
 * is lost when that browser's storage is cleared, and nobody else can see it. When the service grows a
 * snapshot endpoint, this module is the one place that has to change.
 */

import type { GridRow } from '@truth-platform/core-ui'

const STORAGE_KEY = 'truth.snapshots'

/**
 * How many snapshots are kept before the oldest is dropped.
 *
 * Each one holds a copy of every row, and browser storage is a few megabytes in total, so they cannot simply
 * accumulate. Twenty is far more than anybody compares against and well inside what will fit.
 */
const MAX_SNAPSHOTS = 20

/** One preserved reading of the register. */
interface Snapshot {
  id: string
  name: string
  /** Who took it, which is whoever the browser was creating as at the time. */
  takenBy: string
  takenAt: string
  /** The industry the register was narrowed to when it was taken, or nothing for the whole of it. */
  industry: string | null
  /** Which columns were on screen, so that reading it back shows what was actually being looked at. */
  columns: string[]
  rows: GridRow[]
}

/** What a snapshot is described by in a listing, without the weight of its rows. */
type SnapshotSummary = Omit<Snapshot, 'rows'> & { rowCount: number }

/**
 * Read every snapshot this browser holds, newest first.
 *
 * Storage that cannot be read - a private window, a browser told to block site data, or a value some other
 * version of this client wrote - answers with nothing rather than throwing, because a page of snapshots is
 * not worth failing to render over.
 */
const readSnapshots = (): Snapshot[] => {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored === null) {
      return []
    }

    const parsed: unknown = JSON.parse(stored)

    return Array.isArray(parsed) ? (parsed as Snapshot[]) : []
  } catch {
    return []
  }
}

/**
 * Write the snapshots back, and carry on without them if the browser refuses to store them.
 *
 * Storage is a few megabytes and a register of many rows can fill it, so a write that is refused drops the
 * oldest snapshots and tries again rather than losing the one just taken.
 */
const writeSnapshots = (snapshots: Snapshot[]): boolean => {
  for (let kept = snapshots.length; kept > 0; kept -= 1) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshots.slice(0, kept)))

      return true
    } catch {
      /* Too large, or storage is unavailable. Try again with fewer, and give up once one alone will not fit. */
    }
  }

  return false
}

/**
 * List what this browser holds, without carrying every row of every snapshot along with it.
 */
const listSnapshots = (): SnapshotSummary[] =>
  readSnapshots().map(({ rows, ...summary }) => ({ ...summary, rowCount: rows.length }))

/**
 * Read one snapshot whole.
 */
const readSnapshot = (snapshotId: string): Snapshot | null =>
  readSnapshots().find((snapshot) => snapshot.id === snapshotId) ?? null

/**
 * Preserve the register as it currently stands.
 */
const captureSnapshot = (input: Omit<Snapshot, 'id' | 'takenAt'>): Snapshot | null => {
  const snapshot: Snapshot = {
    ...input,
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    takenAt: new Date().toISOString(),
  }

  return writeSnapshots([snapshot, ...readSnapshots()].slice(0, MAX_SNAPSHOTS)) ? snapshot : null
}

/**
 * Forget one snapshot.
 */
const deleteSnapshot = (snapshotId: string): void => {
  writeSnapshots(readSnapshots().filter((snapshot) => snapshot.id !== snapshotId))
}

export type { Snapshot, SnapshotSummary }
export { MAX_SNAPSHOTS, captureSnapshot, deleteSnapshot, listSnapshots, readSnapshot, readSnapshots }
