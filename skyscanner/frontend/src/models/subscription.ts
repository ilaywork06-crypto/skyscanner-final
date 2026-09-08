/**
 * The payloads of the mail subscriptions that tell a user when something new reaches an industry or an event.
 */

type SubscriptionTrigger = 'event_created' | 'event_updated' | 'entity_added' | 'entity_parsed'

interface Subscription {
  id: string
  owner: string
  email: string
  industry: string | null
  event_id: string | null
  event_type_key: string | null
  triggers: SubscriptionTrigger[]
  active: boolean
  created_at: string
  last_notified_at: string | null
}

interface SubscriptionCreateRequest {
  email: string
  industry: string | null
  event_id: string | null
  event_type_key: string | null
  triggers: SubscriptionTrigger[]
}

export type { Subscription, SubscriptionCreateRequest, SubscriptionTrigger }
