/**
 * Every call around the mail subscriptions that make a user hear about an industry or a single event.
 */

import type { Subscription, SubscriptionCreateRequest } from '@/models/subscription'
import { client } from '@/requests/client'

const SUBSCRIPTIONS_PATH = '/subscriptions'

/**
 * Read every subscription of the caller.
 */
const listSubscriptions = async (): Promise<Subscription[]> => {
  const response = await client.get<Subscription[]>(SUBSCRIPTIONS_PATH)

  return response.data
}

/**
 * Start following an industry, an event type or a single event.
 */
const createSubscription = async (request: SubscriptionCreateRequest): Promise<Subscription> => {
  const response = await client.post<Subscription>(SUBSCRIPTIONS_PATH, request)

  return response.data
}

/**
 * Stop following a target the caller follows.
 */
const deleteSubscription = async (subscriptionId: string): Promise<void> => {
  await client.delete(`${SUBSCRIPTIONS_PATH}/${subscriptionId}`)
}

export { createSubscription, deleteSubscription, listSubscriptions }
