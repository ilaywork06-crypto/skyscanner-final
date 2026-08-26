/**
 * The reading, writing and formatting of the points a coordinate field holds.
 *
 * A point travels as three named numbers, which is the shape the service stores and validates. Nothing here
 * knows about a map: the map is one way of picking a point, and typing the numbers is another.
 */

import type { Coordinate, JsonValue } from '@/models/common'

/**
 * Where the map tiles are fetched from.
 *
 * The system is meant to run behind a firewall, so the tile server is named by the deployment rather than
 * being wired to a public one. Without it the field still works - the numbers are typed and read as before -
 * and the map simply says that no server was configured for it.
 */
const TILE_URL: string = import.meta.env.VITE_MAP_TILE_URL ?? ''

/** What a tile server is credited with underneath the map, when the deployment names one. */
const TILE_ATTRIBUTION: string = import.meta.env.VITE_MAP_ATTRIBUTION ?? ''

/** Where a map opens when the field is still empty, which is the middle of the world rather than anywhere. */
const DEFAULT_CENTER: readonly [number, number] = [0, 0]
const DEFAULT_ZOOM = 2
const PICKED_ZOOM = 8

/** How many decimals a degree is shown with, which is a bit better than a metre anywhere on the globe. */
const DEGREE_DECIMALS = 5

/**
 * Read a stored value as a point, accepting the object it is stored as and the list a script may write.
 */
const toCoordinate = (value: JsonValue): Coordinate | null => {
  if (Array.isArray(value) && value.length >= 2) {
    const [lon, lat, alt] = value
    return buildCoordinate(Number(lon), Number(lat), alt === undefined || alt === null ? null : Number(alt))
  }

  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return null
  }

  const record = value as Record<string, JsonValue>

  return buildCoordinate(
    Number(record.lon),
    Number(record.lat),
    record.alt === null || record.alt === undefined ? null : Number(record.alt),
  )
}

/**
 * Build a point out of three numbers, refusing anything that is not a place on the globe.
 */
const buildCoordinate = (lon: number, lat: number, alt: number | null): Coordinate | null => {
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) {
    return null
  }

  if (lon < -180 || lon > 180 || lat < -90 || lat > 90) {
    return null
  }

  return { lon, lat, alt: alt !== null && Number.isFinite(alt) ? alt : null }
}

/**
 * Write a point the way it is read out of a cell: the two degrees, and the altitude only when there is one.
 */
const formatCoordinate = (point: Coordinate): string => {
  const degrees = `${point.lat.toFixed(DEGREE_DECIMALS)}, ${point.lon.toFixed(DEGREE_DECIMALS)}`

  return point.alt === null ? degrees : `${degrees} · ${point.alt} m`
}

export type { Coordinate }
export {
  DEFAULT_CENTER,
  DEFAULT_ZOOM,
  DEGREE_DECIMALS,
  PICKED_ZOOM,
  TILE_ATTRIBUTION,
  TILE_URL,
  buildCoordinate,
  formatCoordinate,
  toCoordinate,
}
