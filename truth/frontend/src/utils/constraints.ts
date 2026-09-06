/**
 * Checking a filled in assumption against the restrictions its schemas declare, before it is sent.
 *
 * The service enforces its own rules and has the last word; this is here so that a mistake is caught while
 * the form is still open and beside the field that caused it, rather than coming back as one sentence about
 * a form that has already been dismissed.
 */

import type { JsonValue } from '@truth-platform/core-ui'

import type { SchemeConstraint, SchemeField } from '@/models/scheme'

/** What a value has to fail before it is called empty, which is the same test the create form uses. */
const isFilled = (value: JsonValue): boolean => {
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
 * Render one value as the text a length or a pattern is measured against.
 */
const asText = (value: JsonValue): string => (typeof value === 'string' ? value : JSON.stringify(value) ?? '')

/**
 * Read the number a comparison is made against, or nothing when either side is not a number.
 */
const asNumber = (value: JsonValue): number | null => {
  const parsed = typeof value === 'number' ? value : Number(asText(value))

  return Number.isNaN(parsed) ? null : parsed
}

/**
 * Test one value against one restriction, answering the complaint or nothing at all.
 *
 * A restriction whose rule nobody here recognises never complains: the service knows what it means and this
 * client does not, so refusing to send the form over it would be refusing on a guess.
 */
const checkConstraint = (constraint: SchemeConstraint, value: JsonValue, label: string): string | null => {
  const stated = constraint.message

  switch (constraint.rule) {
    case 'required':
      return isFilled(value) ? null : stated ?? `${label} is required`
    case 'min': {
      const bound = asNumber(constraint.value)
      const number = asNumber(value)

      return bound === null || number === null || number >= bound ? null : stated ?? `${label} must be at least ${bound}`
    }
    case 'max': {
      const bound = asNumber(constraint.value)
      const number = asNumber(value)

      return bound === null || number === null || number <= bound ? null : stated ?? `${label} must be at most ${bound}`
    }
    case 'min_length': {
      const bound = asNumber(constraint.value)

      return bound === null || !isFilled(value) || asText(value).length >= bound
        ? null
        : stated ?? `${label} must be at least ${bound} characters`
    }
    case 'max_length': {
      const bound = asNumber(constraint.value)

      return bound === null || !isFilled(value) || asText(value).length <= bound
        ? null
        : stated ?? `${label} must be at most ${bound} characters`
    }
    case 'pattern': {
      if (!isFilled(value) || typeof constraint.value !== 'string') {
        return null
      }

      /*
       * The pattern was written by whoever declared the schema, so it may well not compile here - a Python
       * flavour that JavaScript does not share, or simply a typo. A pattern that cannot be read lets the
       * value through rather than failing every value it is put against.
       */
      try {
        return new RegExp(constraint.value).test(asText(value)) ? null : stated ?? `${label} is not in the expected format`
      } catch {
        return null
      }
    }
    case 'one_of': {
      if (!isFilled(value)) {
        return null
      }
      const allowed = Array.isArray(constraint.value) ? constraint.value.map((item) => asText(item)) : []
      if (allowed.length === 0) {
        return null
      }
      const given = Array.isArray(value) ? value.map((item) => asText(item)) : [asText(value)]

      return given.every((item) => allowed.includes(item))
        ? null
        : stated ?? `${label} must be one of: ${allowed.join(', ')}`
    }
    default:
      return null
  }
}

/**
 * Check a whole set of filled in values against the fields and the restrictions declared over them.
 *
 * The answer is keyed by field, so each complaint can be shown under the input that caused it. A field is
 * only ever given its first complaint, because a reader fixes them one at a time anyway.
 */
const validateValues = (
  fields: SchemeField[],
  constraints: SchemeConstraint[],
  values: Record<string, JsonValue>,
): Record<string, string> => {
  const problems: Record<string, string> = {}

  fields.forEach((field) => {
    if (field.required && !isFilled(values[field.key] ?? null)) {
      problems[field.key] = `${field.label} is required`
    }
  })

  constraints.forEach((constraint) => {
    if (constraint.field.length === 0 || problems[constraint.field] !== undefined) {
      return
    }

    const field = fields.find((candidate) => candidate.key === constraint.field)
    const complaint = checkConstraint(
      constraint,
      values[constraint.field] ?? null,
      field?.label ?? constraint.field,
    )

    if (complaint !== null) {
      problems[constraint.field] = complaint
    }
  })

  return problems
}

export { asNumber, asText, checkConstraint, isFilled, validateValues }
