import axios from 'axios'

// Backend address comes from frontend/.env (VITE_API_URL); localhost is only the development default.
export const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const TOKEN_KEY = 'access_token'
export const AUTH_EXPIRED_EVENT = 'auth:expired'

// The JWT lives in localStorage so the user stays logged in after a page refresh.
export const tokenStorage = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

const api = axios.create({ baseURL: API_URL, timeout: 15000 })

// Attach the token to every request automatically.
api.interceptors.request.use((config) => {
  const token = tokenStorage.get()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// If the server says our token is no longer valid, log the user out everywhere.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && tokenStorage.get()) {
      tokenStorage.clear()
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
    }
    return Promise.reject(error)
  },
)

/** Turn any Axios error into a short message that is safe to show to users. */
export function getErrorMessage(error) {
  if (error.response) {
    const detail = error.response.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((item) => item.msg).join('; ')
    return 'Something went wrong. Please try again.'
  }
  if (error.code === 'ECONNABORTED') return 'The server took too long to respond. Please try again.'
  return 'Cannot reach the server. Check that the backend is running.'
}

export const authApi = {
  register: (payload) => api.post('/api/auth/register', payload),
  login: (payload) => api.post('/api/auth/login', payload),
  me: () => api.get('/api/auth/me'),
}

export const urlApi = {
  create: (payload) => api.post('/api/urls', payload),
  list: () => api.get('/api/urls'),
  remove: (id) => api.delete(`/api/urls/${id}`),
}

export const analyticsApi = {
  get: (id, days) => api.get(`/api/analytics/${id}`, { params: { days } }),
  topUrls: (limit = 5) => api.get('/api/analytics/top-urls', { params: { limit } }),
}

export default api
