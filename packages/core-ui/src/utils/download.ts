/**
 * The helpers that hand a file to the browser, either from a blob the API returned or from a temporary link.
 */

/**
 * Hand a blob to the browser as a download with the given file name.
 */
const downloadBlob = (blob: Blob, fileName: string) => {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

/**
 * Follow a link the backend minted, letting the browser decide whether it renders or saves the file.
 */
const openLink = (url: string) => {
  window.open(url, '_blank', 'noopener,noreferrer')
}

export { downloadBlob, openLink }
