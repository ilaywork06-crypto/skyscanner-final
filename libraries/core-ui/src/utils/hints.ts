/**
 * The explanations the forms of the client repeat, kept in one place so that they are worded the same everywhere.
 */

/**
 * Why a box that collects several values needs a key press between them.
 *
 * A combo box holds one value at a time while it is being typed and only turns it into a chip once the value
 * is finished. Nothing on screen says so, so a user who types three values separated by nothing but a glance
 * saves one, and finds out on the next form that the other two were never there. Saying it beside the box is
 * cheaper than teaching it once per user.
 */
const ENTER_TO_ADD_HINT =
  'Type a value and press Enter to add it. Each value becomes its own chip, and anything still being typed ' +
  'when the form is saved is not kept.'

export { ENTER_TO_ADD_HINT }
