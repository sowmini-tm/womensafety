import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export default api

// Attach access token from localStorage to requests
api.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
  } catch (e) {
    // ignore
  }
  return config
})

// --- 401 handling: one shared refresh attempt, no infinite retry loops ---

// Single-flight promise so concurrent 401s trigger exactly one refresh call.
let refreshPromise: Promise<string | null> | null = null

function clearSessionAndRedirect() {
  try {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  } catch (e) {
    // ignore
  }
  window.location.assign('/login')
}

async function requestNewAccessToken(): Promise<string | null> {
  let refreshToken: string | null = null
  try {
    refreshToken = localStorage.getItem('refresh_token')
  } catch (e) {
    // ignore
  }
  if (!refreshToken) return null
  // Plain axios instance: bypasses the interceptors below so a failing
  // refresh call can never recurse into itself.
  const res = await axios.post(`${api.defaults.baseURL ?? ''}/auth/refresh`, {
    refresh_token: refreshToken,
  })
  const data = res.data as { access_token?: string; refresh_token?: string }
  if (!data.access_token) return null
  try {
    localStorage.setItem('access_token', data.access_token)
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token)
    }
  } catch (e) {
    // ignore
  }
  return data.access_token
}

api.interceptors.response.use(
  (response) => response,
  async (error: any) => {
    const config = error?.config ?? {}
    const status = error?.response?.status
    const url: string = config?.url ?? ''
    const isAuthCall =
      url.includes('/auth/login') || url.includes('/auth/register') || url.includes('/auth/refresh')
    // Never retry auth calls themselves, non-401 errors, or requests that were
    // already retried once after a refresh.
    if (status !== 401 || config._retry || isAuthCall) {
      throw error
    }
    config._retry = true
    try {
      refreshPromise = refreshPromise ?? requestNewAccessToken()
      const accessToken = await refreshPromise.finally(() => {
        refreshPromise = null
      })
      if (!accessToken) {
        clearSessionAndRedirect()
        throw error
      }
      config.headers = { ...config.headers, Authorization: `Bearer ${accessToken}` }
      return api(config)
    } catch (e) {
      clearSessionAndRedirect()
      throw e
    }
  },
)
