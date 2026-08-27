/**
 * Safe, human-readable API error extraction.
 *
 * FastAPI returns several error shapes:
 *   - { "detail": "some message" }            (HTTPException / string)
 *   - { "detail": [...] }                     (pydantic validation errors)
 *   - ordinary Error objects
 *   - Axios network errors (no response)
 *
 * This helper always returns a plain string — never an object/array — so callers
 * can safely render it without producing "[object Object]".
 */

type RawError = {
  response?: {
    data?: unknown
    status?: number
  }
  message?: string
  code?: string | number
} | null | undefined

/** Normalize pydantic validation detail arrays into readable messages. */
function detailToString(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') {
    const trimmed = detail.trim()
    return trimmed.length > 0 ? trimmed : fallback
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object') {
          const obj = item as { msg?: string; loc?: Array<string | number> }
          if (typeof obj.msg === 'string') return obj.msg
        }
        return ''
      })
      .filter((m) => m.length > 0)
    if (messages.length > 0) return messages[0]
    return fallback
  }

  if (detail && typeof detail === 'object') {
    return fallback
  }

  return fallback
}

/**
 * Convert any caught error into a user-friendly string.
 * Optional `fallback` is used when no useful message can be extracted.
 */
export function getErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
  const err = error as RawError

  // No error at all
  if (!error) return fallback

  // Axios error with a response body
  if (err?.response) {
    const data = err.response.data
    if (data && typeof data === 'object') {
      const obj = data as Record<string, unknown>
      if (typeof obj.detail !== 'undefined') {
        return detailToString(obj.detail, fallback)
      }
      if (typeof obj.message === 'string' && obj.message.trim()) {
        return obj.message.trim()
      }
      // Error pages like { "status": "error", "detail": "..." }
      if (typeof obj.error === 'string' && obj.error.trim()) {
        return obj.error.trim()
      }
    }
    if (typeof data === 'string' && data.trim()) {
      return data.trim()
    }
    // Fall back to a status-derived message when we have a status but no body text.
    if (err.response.status) {
      return `Request failed (${err.response.status})`
    }
    return fallback
  }

  // Network / timeout errors (no response)
  if (err?.code) {
    if (err.code === 'ECONNABORTED') return 'The request timed out. Please try again.'
    if (err.code === 'ERR_NETWORK') return 'Network error — could not reach the server. Check your connection.'
  }

  // Plain JS Error instances
  if (error instanceof Error) {
    const msg = error.message.trim()
    return msg.length > 0 ? msg : fallback
  }

  // Something else with a string representation we trust
  if (typeof error === 'string') {
    const trimmed = error.trim()
    return trimmed.length > 0 ? trimmed : fallback
  }

  return fallback
}

/** True when an error looks like a network/connectivity failure. */
export function isNetworkError(error: unknown): boolean {
  const err = error as RawError
  return Boolean(err && !err.response && (err.code === 'ERR_NETWORK' || err.code === 'ECONNABORTED'))
}
