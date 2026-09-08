/**
 * The shared axios client, holding the base address of the gateway and turning failures into readable messages.
 */

import axios, { type AxiosError, type AxiosInstance } from 'axios'

interface ApiErrorBody {
  detail?: string
  error?: string
  details?: Record<string, string>
}

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '/api'
const REQUEST_TIMEOUT_MS = 60000
const UPLOAD_TIMEOUT_MS = 600000

const client: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
})

/**
 * Read the message the backend put into a failed answer, falling back to the transport message.
 */
const readErrorMessage = (error: AxiosError<ApiErrorBody>): string => {
  const body = error.response?.data
  if (body !== undefined && typeof body.detail === 'string' && body.detail.length > 0) {
    return body.detail
  }

  return error.message.length > 0 ? error.message : 'The request could not be completed'
}

client.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorBody>) => Promise.reject(new Error(readErrorMessage(error))),
)

export type { ApiErrorBody }
export { API_BASE_URL, UPLOAD_TIMEOUT_MS, client }
