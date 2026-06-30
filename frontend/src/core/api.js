// Общий API-клиент. Один и тот же для сайта и для мини-аппа —
// механизм идентичен, меняется только способ получения токена.

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

let token = null
export function setToken(t) { token = t }
export function getToken() { return token }

async function request(method, path, body) {
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${BASE}/api${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || `HTTP ${res.status}`)
  }
  return res.status === 204 ? null : res.json()
}

export const api = {
  // auth
  register: (b) => request('POST', '/auth/register', b),
  login: (b) => request('POST', '/auth/login', b),
  telegram: (init_data) => request('POST', '/auth/telegram', { init_data }),
  me: () => request('GET', '/auth/me'),
  // listings
  categories: () => request('GET', '/categories'),
  clarify: (b) => request('POST', '/ai/clarify', b),
  createResource: (b) => request('POST', '/resources', b),
  listResources: (mine = false) => request('GET', `/resources?mine=${mine}`),
  createNeed: (b) => request('POST', '/needs', b),
  listNeeds: (mine = false) => request('GET', `/needs?mine=${mine}`),
  // matching
  matchesForNeed: (id) => request('GET', `/matches/for-need/${id}`),
  matchesForResource: (id) => request('GET', `/matches/for-resource/${id}`),
  // deals
  createDeal: (b) => request('POST', '/deals', b),
  getDeal: (id) => request('GET', `/deals/${id}`),
  sendMessage: (id, text) => request('POST', `/deals/${id}/messages`, { text }),
  updateContract: (id, updates) => request('PATCH', `/deals/${id}/contract`, { updates }),
  sign: (id) => request('POST', `/deals/${id}/sign`),
  complete: (id) => request('POST', `/deals/${id}/complete`),
  review: (actId, b) => request('POST', `/deals/acts/${actId}/review`, b),
}
