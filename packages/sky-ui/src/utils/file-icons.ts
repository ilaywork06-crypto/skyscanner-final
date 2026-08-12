/**
 * The mapping between a stored file and the icon that tells the reader what kind of file it is at a glance.
 */

const ICONS_BY_SUFFIX: Record<string, string> = {
  csv: 'mdi-file-delimited-outline',
  tsv: 'mdi-file-delimited-outline',
  xls: 'mdi-file-table-outline',
  xlsx: 'mdi-file-table-outline',
  json: 'mdi-code-json',
  yaml: 'mdi-file-cog-outline',
  yml: 'mdi-file-cog-outline',
  xml: 'mdi-file-xml-box',
  ini: 'mdi-file-cog-outline',
  cfg: 'mdi-file-cog-outline',
  log: 'mdi-file-document-outline',
  txt: 'mdi-file-document-outline',
  md: 'mdi-language-markdown-outline',
  pdf: 'mdi-file-pdf-box',
  png: 'mdi-file-image-outline',
  jpg: 'mdi-file-image-outline',
  jpeg: 'mdi-file-image-outline',
  gif: 'mdi-file-image-outline',
  webp: 'mdi-file-image-outline',
  svg: 'mdi-file-image-outline',
  bmp: 'mdi-file-image-outline',
  mp4: 'mdi-file-video-outline',
  mov: 'mdi-file-video-outline',
  avi: 'mdi-file-video-outline',
  mkv: 'mdi-file-video-outline',
  wav: 'mdi-file-music-outline',
  mp3: 'mdi-file-music-outline',
  zip: 'mdi-folder-zip-outline',
  gz: 'mdi-folder-zip-outline',
  tar: 'mdi-folder-zip-outline',
  bz2: 'mdi-folder-zip-outline',
  '7z': 'mdi-folder-zip-outline',
  py: 'mdi-language-python',
  js: 'mdi-language-javascript',
  ts: 'mdi-language-typescript',
  sql: 'mdi-database-outline',
  bag: 'mdi-database-outline',
  db: 'mdi-database-outline',
  parquet: 'mdi-database-outline',
  bin: 'mdi-file-cabinet',
  dat: 'mdi-file-cabinet',
}

const ICONS_BY_CONTENT_PREFIX: Record<string, string> = {
  'image/': 'mdi-file-image-outline',
  'video/': 'mdi-file-video-outline',
  'audio/': 'mdi-file-music-outline',
  'text/': 'mdi-file-document-outline',
}

const DEFAULT_FILE_ICON = 'mdi-file-outline'

/**
 * Read the suffix of a file, preferring the recorded one over the tail of the name.
 */
const readSuffix = (name: string, suffix: string): string => {
  const recorded = suffix.replace('.', '').toLowerCase()

  return recorded.length > 0 ? recorded : (name.split('.').pop() ?? '').toLowerCase()
}

/**
 * Pick the icon of one stored file, going by its suffix first and by its content type second.
 */
const fileIcon = (name: string, suffix = '', contentType = ''): string => {
  const bySuffix = ICONS_BY_SUFFIX[readSuffix(name, suffix)]
  if (bySuffix !== undefined) {
    return bySuffix
  }

  const lowered = contentType.toLowerCase()
  for (const [prefix, icon] of Object.entries(ICONS_BY_CONTENT_PREFIX)) {
    if (lowered.startsWith(prefix)) {
      return icon
    }
  }

  return DEFAULT_FILE_ICON
}

export { DEFAULT_FILE_ICON, fileIcon }
