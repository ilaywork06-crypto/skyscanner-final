/**
 * The reading, writing and formatting of the points a coordinate field holds.
 *
 * A point travels as three named numbers, which is the shape the service stores and validates. Nothing here
 * knows about a map: the map is one way of picking a point, and typing the numbers is another.
 */

import type { Coordinate, JsonValue } from '../models/common'

/**
 * Where the map tiles are fetched from, and what that server is credited with underneath the map.
 *
 * The system is meant to run behind a firewall, so the tile server is named by the deployment rather than
 * being wired to a public one. It is handed in by the product that installs the library rather than read out
 * of the environment here, because only the product knows how its own deployment is configured - and a
 * product with no maps at all should not have to declare a variable it never uses.
 *
 * Without a server the field still works: the numbers are typed and read exactly as before, and the map
 * simply says that none was configured for it.
 */
interface MapTiles {
  url: string
  attribution: string
}

let tiles: MapTiles = { url: '', attribution: '' }

/**
 * Name the tile server this deployment fetches its map from.
 *
 * Called once while the application starts, before anything renders a coordinate field.
 */
const configureMapTiles = (configuration: MapTiles): void => {
  tiles = configuration
}

/**
 * Read the tile server currently configured, which is nothing at all until one has been named.
 */
const mapTiles = (): MapTiles => tiles

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

export type { MapTiles }
export type { Coordinate }
export {
  DEFAULT_CENTER,
  DEFAULT_ZOOM,
  DEGREE_DECIMALS,
  PICKED_ZOOM,
  configureMapTiles,
  mapTiles,
  buildCoordinate,
  formatCoordinate,
  toCoordinate,
}
