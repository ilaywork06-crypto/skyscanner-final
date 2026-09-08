/**
 * The feature flags of the web client - the switches that decide which of the built features users are offered.
 *
 * A flag lives here rather than beside the feature it hides, so that taking a feature out of reach or putting
 * it back is one line in one file instead of markup deleted or commented out across several. Nothing behind a
 * flag is removed: the components, the requests and the services they call stay exactly where they are.
 */

/**
 * Whether following an industry or an event is offered - the Subscriptions entry of the user menu, the bell
 * of an event page and the /subscriptions page itself, which redirects to the inventory while this is off.
 *
 * Subscriptions are an advanced feature that is not meant to be put in front of every user yet. The dialog,
 * `requests/subscriptions`, the endpoints of the events service and the whole notification service are
 * untouched and keep working, so setting this to true is all it takes to offer the feature again.
 */
const SUBSCRIPTIONS_ENABLED: boolean = false

export { SUBSCRIPTIONS_ENABLED }
