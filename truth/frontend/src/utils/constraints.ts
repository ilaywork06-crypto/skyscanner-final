/**
 * Checking a filled in assumption against what its schemas declare, before it is sent.
 *
 * The service enforces its own rules and has the last word; this is here so that a mistake is caught while
 * the form is still open and beside the field that caused it, rather than coming back as one sentence about
 * a form that has already been dismissed.
 *
 * What is checked comes from the fields themselves rather than from a separate list of constraints: whether
 * a field is required, what an enumeration may be chosen from, and what a confined number is bounded by.
 */

import type { JsonValue } from '@truth-platform/core-ui'

import type { SchemeField } from '@/models/scheme'
import { isNumeric } from '@/utils/scheme'

/** What a value has to fail before it is called empty. */
const isFilled = (value: JsonValue | undefined): boolean => {
  if (value === null || value === undefined) {
    return false
  }

  if (typeof value === 'string') {
    return value.trim().length > 0
  }

  if (Array.isArray(value)) {
    return value.length > 0
  }

  return true
}

/**
 * Read one value as the number it is meant to be, or nothing when it does not read as one at all.
 */
const asNumber = (value: JsonValue): number | null => {
  const parsed = typeof value === 'number' ? value : Number(String(value))

  return Number.isNaN(parsed) ? null : parsed
}

/**
 * Say what is wrong with one value of a confined number, or nothing when it is inside its bounds.
 *
 * The increment is checked against the lower bound where there is one, so a field stepping by 5 from 10
 * accepts 15 rather than only multiples of 5.
 */
const checkNumber = (field: SchemeField, value: JsonValue): string | null => {
  const number = asNumber(value)
  if (number === null) {
    return `${field.displayName} must be a number`
  }

  if (field.type === 'confined_number' && !Number.isInteger(number)) {
    return `${field.displayName} must be a whole number`
  }

  if (field.min !== null && number < field.min) {
    return `${field.displayName} must be at least ${field.min}`
  }

  if (field.max !== null && number > field.max) {
    return `${field.displayName} must be at most ${field.max}`
  }

  if (field.step !== null && field.step > 0) {
    const from = field.min ?? 0
    const steps = (number - from) / field.step
    /*
     * A decimal step never divides exactly in binary floating point - 0.1 three times is not 0.3 - so the
     * remainder is compared against a tolerance rather than against zero.
     */
    if (Math.abs(steps - Math.round(steps)) > 1e-9) {
      return `${field.displayName} must go up in steps of ${field.step}${field.min === null ? '' : ` from ${field.min}`}`
    }
  }

  return null
}

/**
 * Say what is wrong with the value held under one field, or nothing when there is nothing wrong with it.
 */
const checkField = (field: SchemeField, value: JsonValue | undefined): string | null => {
  if (!isFilled(value)) {
    return field.required ? `${field.displayName} is required` : null
  }

  const held = value as JsonValue
  /* A field holding several values is right only if every one of them is. */
  const values: JsonValue[] = field.array && Array.isArray(held) ? held : [held]

  for (const single of values) {
    if (field.type === 'enum' && field.options.length > 0 && !field.options.includes(String(single))) {
      return `${field.displayName} must be one of: ${field.options.join(', ')}`
    }

    if (isNumeric(field.type)) {
      const complaint = checkNumber(field, single)
      if (complaint !== null) {
        return complaint
      }
    }
  }

  return null
}

/**
 * Check a whole set of filled in values against the fields declared over them.
 *
 * The answer is keyed by field, so each complaint can be shown under the input that caused it. A field is
 * only ever given its first complaint, because a reader fixes them one at a time anyway.
 */
const validateValues = (fields: SchemeField[], values: Record<string, JsonValue>): Record<string, string> => {
  const problems: Record<string, string> = {}

  fields.forEach((field) => {
    const complaint = checkField(field, values[field.key])
    if (complaint !== null) {
      problems[field.key] = complaint
    }
  })

  return problems
}

export { asNumber, checkField, checkNumber, isFilled, validateValues }
