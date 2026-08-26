/**
 * The rules about the identity of a stored file, which is what tells a second copy of one from a new one.
 *
 * Two files under the same owner are the same file when they sit in the same folder under the same name.
 * The key in the bucket says nothing about it - every upload is written under a fresh identifier so that two
 * uploads can never overwrite one another - so the identity a user means is the one written here.
 */

import type { Artifact } from '@/models/common'

/** How a file is addressed inside its owner: the folder it was filed under and the name it carries. */
const artifactKey = (folder: string | null, name: string): string => `${folder ?? ''}/${name}`

/** The address of one stored file, read out of the record the storage service handed back. */
const keyOfArtifact = (artifact: Artifact): string => artifactKey(artifact.folder, artifact.name)

/**
 * Name every picked file that would land on top of a file the owner already holds, or on top of each other.
 *
 * Uploading the same path and name twice leaves the owner with two records nobody can tell apart, one of
 * which is unreachable in every listing that groups by name. It is refused rather than resolved, because
 * only the person picking the file knows which of the two they meant.
 */
const collidingNames = (stored: Artifact[], picked: File[], folder: string | null): string[] => {
  const taken = new Set(stored.map(keyOfArtifact))
  const clashing: string[] = []

  picked.forEach((file) => {
    const key = artifactKey(folder, file.name)
    if (taken.has(key)) {
      clashing.push(file.name)

      return
    }

    taken.add(key)
  })

  return [...new Set(clashing)]
}

/**
 * Say what is wrong when files were picked that the owner already holds, or nothing when none were.
 */
const collisionMessage = (stored: Artifact[], picked: File[], folder: string | null, label: string): string => {
  const clashing = collidingNames(stored, picked, folder)
  if (clashing.length === 0) {
    return ''
  }

  return `${label} already holds ${clashing.join(', ')}. Remove the stored copy first, or rename the file.`
}

export { artifactKey, collidingNames, collisionMessage, keyOfArtifact }
