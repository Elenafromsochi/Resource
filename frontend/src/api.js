// API-клиент. Токен хранится в localStorage, чтобы сессия переживала перезагрузку.
// Пустая строка = тот же адрес, что и сайт (когда сервер сам отдаёт фронт).
// undefined (локальная разработка) = отдельный бэкенд на :8000.
const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

// Адрес перехода на вход через Яндекс (кнопка ведёт браузер сюда напрямую).
export const yandexLoginUrl = `${BASE}/api/auth/yandex/login`

export function getToken() { return localStorage.getItem('token') }
export function setToken(t) { t ? localStorage.setItem('token', t) : localStorage.removeItem('token') }

async function request(method, path, body) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${BASE}/api${path}`, {
    method, headers, body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    if (res.status === 401) setToken(null)  // сбрасываем протухший токен
    const detail = await res.json().catch(() => ({}))
    throw new Error(typeof detail.detail === 'string' ? detail.detail : `Ошибка ${res.status}`)
  }
  return res.status === 204 ? null : res.json()
}

export const api = {
  register: (b) => request('POST', '/auth/register', b),
  login: (b) => request('POST', '/auth/login', b),
  getProfile: () => request('GET', '/profile'),
  saveProfile: (b) => request('PUT', '/profile', b),
  assist: (text) => request('POST', '/profile/assist', { text }),
  extract: (text, kind) => request('POST', '/profile/extract', { text, kind }),
  clarify: (draft, clarifications) => request('POST', '/profile/clarify', { draft, clarifications }),
  getQuestions: () => request('GET', '/questions'),
  getConfig: () => request('GET', '/config'),
}
