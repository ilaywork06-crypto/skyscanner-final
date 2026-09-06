/**
 * The shared axios client, holding the base address of the API and turning failures into readable messages.
 */

import axios, { type AxiosError, type AxiosInstance } from 'axios'

interface ApiErrorBody {
  detail?: string | { msg?: string }[]
  error?: string
}

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '/api'
const REQUEST_TIMEOUT_MS = 60000

const client: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
})

/**
 * Read the message the service put into a failed answer, falling back to the transport message.
 *
 * A validation failure arrives as a list of complaints rather than as one sentence, so the sentences are
 * joined instead of the whole list being rendered as "[object Object]" the way a plain cast would leave it.
 */
const readErrorMessage = (error: AxiosError<ApiErrorBody>): string => {
  const body = error.response?.data
  const detail = body?.detail

  if (typeof detail === 'string' && detail.length > 0) {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item.msg ?? '').filter((message) => message.length > 0)
    if (messages.length > 0) {
      return messages.join('; ')
    }
  }

  if (typeof body?.error === 'string' && body.error.length > 0) {
    return body.error
  }

  return error.message.length > 0 ? error.message : 'The request could not be completed'
}

client.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorBody>) => Promise.reject(new Error(readErrorMessage(error))),
)

export type { ApiErrorBody }
export { API_BASE_URL, client }
