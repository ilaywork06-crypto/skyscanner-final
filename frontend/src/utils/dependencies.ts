/**
 * The rules that decide whether a declared field applies to a form as it currently stands.
 *
 * The very same reading runs in the service, which is what makes the two agree: a field the client hides is
 * a field the service neither requires nor stores.
 */

import type { JsonValue } from '@/models/common'
import type { FieldDefinition, FieldDependency } from '@/models/field'

/**
 * Decide whether a value counts as filled in, which is what the presence operators test.
 */
const isFilled = (value: JsonValue | undefined): boolean => {
  if (value === null || value === undefined || value === '') {
    return false
  }

  return !Array.isArray(value) || value.length > 0
}

/**
 * Read the value a condition is tested against, looking at the form itself before its surroundings.
 *
 * A field of an entity may depend on a field of the event it hangs under, so a key the form itself does not
 * declare is looked up in the values of that event. The form wins whenever it holds the key at all, even
 * with nothing filled in, because a field of the form is the one the user is looking at.
 */
const resolveValue = (
  key: string,
  values: Record<string, JsonValue>,
  context?: Record<string, JsonValue>,
): JsonValue | undefined => (key in values ? values[key] : context?.[key])

/**
 * Test one condition against the value the field it points at currently holds.
 */
const dependencyHolds = (
  dependency: FieldDependency,
  values: Record<string, JsonValue>,
  context?: Record<string, JsonValue>,
): boolean => {
  const other = resolveValue(dependency.field, values, context)
  const filled = isFilled(other)

  switch (dependency.operator) {
    case 'has_value':
      return filled
    case 'is_empty':
      return !filled
    case 'not_equals':
      return !dependency.values.includes(other ?? null)
    default:
      /* Both equals and one of compare against the declared values; equals simply declares a single one. */
      return dependency.values.includes(other ?? null)
  }
}

/**
 * Decide whether every condition a field declared on the fields around it currently holds.
 */
const dependenciesHold = (
  dependencies: FieldDependency[],
  values: Record<string, JsonValue>,
  context?: Record<string, JsonValue>,
): boolean => dependencies.every((dependency) => dependencyHolds(dependency, values, context))

/**
 * Keep only the fields that apply to the form as it currently stands.
 *
 * The context carries the values of the object the form hangs under - the event of an entity - so that a
 * field which waits on an event field is shown and asked for once that event field holds the right value.
 */
const applicableFields = (
  fields: FieldDefinition[],
  values: Record<string, JsonValue>,
  context?: Record<string, JsonValue>,
): FieldDefinition[] => fields.filter((field) => dependenciesHold(field.depends_on ?? [], values, context))

export { applicableFields, dependenciesHold, dependencyHolds, isFilled }
