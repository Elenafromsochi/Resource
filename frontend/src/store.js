// Хранилище прототипа «Ресурс · Тренер».
// Всё живёт в браузере (localStorage), чтобы демо переживало перезагрузку.
// Реального сервера нет — это визуальный прототип.
import { reactive, watch } from 'vue'

const STORAGE_KEY = 'fittrainer_v2'

// --- helpers для дат ---------------------------------------------------------
const DAY = 86400000
export function dayISO(offsetDays = 0) {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  d.setTime(d.getTime() + offsetDays * DAY)
  return d.toISOString().slice(0, 10)
}
export function nowTs() {
  return new Date().toISOString()
}
export function uid(prefix = 'id') {
  return prefix + '_' + Math.random().toString(36).slice(2, 9)
}

// --- библиотека упражнений (из фото клиента) ---------------------------------
const LIBRARY = [
  {
    group: 'Ноги',
    color: '#22c55e',
    exercises: [
      { name: 'Присед от степа с касанием пола (сзади/сбоку/спереди)', scheme: '10×3', combo: 'ротация таза в наклоне 30×3' },
      { name: 'Латеральный присед, 6 кг', scheme: '15×3', combo: 'статика в приседе 30 сек ×3' },
      { name: 'Румынская тяга, 30 кг', scheme: '18-16-14', combo: '' },
      { name: 'Сгибание ног лёжа + разгибание ног сидя', scheme: '15×3', combo: '' },
      { name: 'Боковая планка в динамике', scheme: '16×3', combo: '' },
    ],
  },
  {
    group: 'Верх',
    color: '#3b82f6',
    exercises: [
      { name: 'Наружное вращение плеча + тяга к груди в кроссовере', scheme: '15×3', combo: '' },
      { name: 'Подтягивания в гравитроне', scheme: '12×3', combo: '' },
      { name: 'Тяга к тазу в наклоне с грифом', scheme: '12×3', combo: '' },
      { name: 'Сгибание рук с жимом вверх', scheme: '12×3', combo: '' },
      { name: 'Отведение рук в стороны', scheme: '15×3', combo: '' },
    ],
  },
  {
    group: 'Общая',
    color: '#f59e0b',
    exercises: [
      { name: 'Тяга к груди стоя в кроссовере', scheme: '15×3', combo: '' },
      { name: 'Пуловер + жим вверх', scheme: '12×3', combo: '' },
      { name: 'Жим ногами + статика в стульчике', scheme: '15×3', combo: 'статика 30 сек ×3' },
      { name: 'Ягодичный мост, 30 кг + отведение бедра в тренажёре', scheme: '15×3', combo: '' },
      { name: 'Собака мордой вниз + стол', scheme: '20×4', combo: '' },
    ],
  },
]

export function groupColor(group) {
  return (LIBRARY.find(g => g.group === group) || {}).color || '#64748b'
}

function makeSession(group, offsetDays, time, status, feedback = null) {
  const tpl = LIBRARY.find(g => g.group === group)
  return {
    id: uid('s'),
    date: dayISO(offsetDays),
    time,
    group,
    title: 'Тренировка · ' + group,
    exercises: tpl.exercises.map(e => ({ ...e, done: status === 'done' })),
    status, // planned | done | skipped
    feedback,
    seenByTrainer: status !== 'done',
  }
}

function seed() {
  const trainer = {
    id: 'trainer',
    name: 'Анна Ковалёва',
    title: 'Персональный фитнес-тренер',
    avatar: '🏋️‍♀️',
  }

  const clients = [
    { id: 'c1', name: 'Мария Соколова', avatar: '🙋‍♀️', goal: 'Тонус и осанка', level: 'Средний', since: dayISO(-64), phone: '+7 900 111-22-33' },
    { id: 'c2', name: 'Ольга Петрова', avatar: '💃', goal: 'Похудение', level: 'Начинающий', since: dayISO(-30), phone: '+7 900 222-33-44' },
    { id: 'c3', name: 'Ирина Волкова', avatar: '🧘‍♀️', goal: 'Сила и выносливость', level: 'Продвинутый', since: dayISO(-120), phone: '+7 900 333-44-55' },
  ]

  const plans = {
    c1: [
      makeSession('Ноги', -6, '10:00', 'done', { rating: 5, difficulty: 'В самый раз', energy: 'Бодрость', note: 'Приседы от степа — топ! Колено не болело.', at: nowTs() }),
      makeSession('Верх', -3, '10:00', 'done', { rating: 4, difficulty: 'Тяжеловато', energy: 'Норма', note: 'Подтягивания в гравитроне даются с трудом, к концу руки отваливались.', at: nowTs() }),
      makeSession('Общая', -1, '10:00', 'skipped', null),
      makeSession('Ноги', 1, '10:00', 'planned', null),
      makeSession('Верх', 4, '10:00', 'planned', null),
      makeSession('Общая', 6, '18:30', 'planned', null),
    ],
    c2: [
      makeSession('Общая', -5, '19:00', 'done', { rating: 3, difficulty: 'Тяжело', energy: 'Устала', note: 'Жим ногами — тяжело, статику в стульчике почти не удержала.', at: nowTs() }),
      makeSession('Ноги', 2, '19:00', 'planned', null),
      makeSession('Общая', 5, '19:00', 'planned', null),
    ],
    c3: [
      makeSession('Верх', -2, '08:00', 'done', { rating: 5, difficulty: 'Легко', energy: 'Отлично', note: 'Готова к увеличению веса на тяге к тазу.', at: nowTs() }),
      makeSession('Ноги', 0, '08:00', 'planned', null),
      makeSession('Верх', 3, '08:00', 'planned', null),
    ],
  }

  const messages = {
    c1: [
      { id: uid('m'), from: 'trainer', text: 'Мария, привет! Завтра тренировка на ноги в 10:00. Возьми ролик для разминки 🙌', at: nowTs(), read: true },
      { id: uid('m'), from: 'client', text: 'Привет! Поняла, буду 💪', at: nowTs(), read: true },
      { id: uid('m'), from: 'client', text: 'После прошлой немного тянет заднюю поверхность бедра, это нормально?', at: nowTs(), read: false },
    ],
    c2: [
      { id: uid('m'), from: 'trainer', text: 'Ольга, как самочувствие после общей тренировки?', at: nowTs(), read: true },
    ],
    c3: [
      { id: uid('m'), from: 'client', text: 'Анна, добавьте, пожалуйста, вес на румынскую тягу в следующий раз', at: nowTs(), read: false },
    ],
  }

  return {
    version: 2,
    role: 'trainer', // trainer | client
    activeClientId: 'c1',
    tab: 'dashboard',
    trainer,
    clients,
    library: LIBRARY,
    plans,
    messages,
    dismissedReminders: [],
  }
}

// --- загрузка / сохранение ---------------------------------------------------
function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const data = JSON.parse(raw)
      if (data && data.version === 2) return data
    }
  } catch (e) { /* игнорируем битый кеш */ }
  return seed()
}

export const store = reactive(load())

watch(store, () => {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(store)) } catch (e) {}
}, { deep: true })

// --- геттеры -----------------------------------------------------------------
export function activeClient() {
  return store.clients.find(c => c.id === store.activeClientId) || store.clients[0]
}
export function clientPlan(clientId) {
  return (store.plans[clientId] || []).slice().sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time))
}
export function clientMessages(clientId) {
  return store.messages[clientId] || []
}

// --- действия ----------------------------------------------------------------
export const actions = {
  setRole(role) {
    store.role = role
    store.tab = role === 'trainer' ? 'dashboard' : 'home'
  },
  setActiveClient(id) { store.activeClientId = id },
  setTab(tab) { store.tab = tab },

  // тренер: добавить тренировку в план клиента
  addSession(clientId, { group, date, time }) {
    const tpl = store.library.find(g => g.group === group)
    if (!store.plans[clientId]) store.plans[clientId] = []
    store.plans[clientId].push({
      id: uid('s'),
      date,
      time,
      group,
      title: 'Тренировка · ' + group,
      exercises: tpl.exercises.map(e => ({ ...e, done: false })),
      status: 'planned',
      feedback: null,
      seenByTrainer: true,
    })
  },
  removeSession(clientId, sessionId) {
    store.plans[clientId] = (store.plans[clientId] || []).filter(s => s.id !== sessionId)
  },
  updateSessionMeta(clientId, sessionId, patch) {
    const s = (store.plans[clientId] || []).find(x => x.id === sessionId)
    if (s) Object.assign(s, patch)
  },

  // клиент: отметить упражнение / завершить тренировку
  toggleExercise(clientId, sessionId, idx) {
    const s = (store.plans[clientId] || []).find(x => x.id === sessionId)
    if (s) s.exercises[idx].done = !s.exercises[idx].done
  },
  completeSession(clientId, sessionId, feedback) {
    const s = (store.plans[clientId] || []).find(x => x.id === sessionId)
    if (!s) return
    s.status = 'done'
    s.exercises.forEach(e => { e.done = true })
    s.feedback = { ...feedback, at: nowTs() }
    s.seenByTrainer = false // тренер увидит новый отзыв
  },
  markSkipped(clientId, sessionId) {
    const s = (store.plans[clientId] || []).find(x => x.id === sessionId)
    if (s) s.status = 'skipped'
  },
  markFeedbackSeen(clientId, sessionId) {
    const s = (store.plans[clientId] || []).find(x => x.id === sessionId)
    if (s) s.seenByTrainer = true
  },

  // чат
  sendMessage(clientId, from, text) {
    if (!text.trim()) return
    if (!store.messages[clientId]) store.messages[clientId] = []
    store.messages[clientId].push({ id: uid('m'), from, text: text.trim(), at: nowTs(), read: false })
  },
  markMessagesRead(clientId, reader) {
    // reader читает сообщения, отправленные другой стороной
    const other = reader === 'trainer' ? 'client' : 'trainer'
    ;(store.messages[clientId] || []).forEach(m => { if (m.from === other) m.read = true })
  },

  dismissReminder(id) {
    if (!store.dismissedReminders.includes(id)) store.dismissedReminders.push(id)
  },

  resetDemo() {
    const fresh = seed()
    Object.keys(store).forEach(k => { if (!(k in fresh)) delete store[k] })
    Object.assign(store, fresh)
  },
}

// --- напоминания / уведомления ----------------------------------------------
// Возвращает список для текущей роли.
export function reminders() {
  const out = []
  const today = dayISO(0)
  if (store.role === 'client') {
    const cid = store.activeClientId
    for (const s of clientPlan(cid)) {
      if (s.status !== 'planned') continue
      const diff = Math.round((new Date(s.date) - new Date(today)) / DAY)
      if (diff < 0 || diff > 2) continue
      const when = diff === 0 ? 'сегодня' : diff === 1 ? 'завтра' : 'послезавтра'
      out.push({
        id: 'rem_' + s.id,
        icon: '⏰',
        title: `Тренировка ${when} в ${s.time}`,
        body: s.title,
        kind: 'reminder',
      })
    }
    // непрочитанные сообщения от тренера
    const unread = clientMessages(cid).filter(m => m.from === 'trainer' && !m.read).length
    if (unread) out.push({ id: 'msg_' + cid, icon: '💬', title: `Новое сообщение от тренера`, body: `${unread} непрочитанных`, kind: 'chat' })
  } else {
    // тренер: новые отзывы + непрочитанные сообщения клиентов
    for (const c of store.clients) {
      for (const s of clientPlan(c.id)) {
        if (s.status === 'done' && s.feedback && !s.seenByTrainer) {
          out.push({
            id: 'fb_' + s.id,
            icon: '⭐',
            title: `Новый отзыв: ${c.name}`,
            body: `${s.title} · оценка ${s.feedback.rating}/5`,
            kind: 'feedback',
            clientId: c.id,
          })
        }
      }
      const unread = clientMessages(c.id).filter(m => m.from === 'client' && !m.read).length
      if (unread) out.push({ id: 'cmsg_' + c.id, icon: '💬', title: `Сообщение: ${c.name}`, body: `${unread} непрочитанных`, kind: 'chat', clientId: c.id })
    }
    // ближайшие тренировки на сегодня
    for (const c of store.clients) {
      for (const s of clientPlan(c.id)) {
        if (s.status === 'planned' && s.date === today) {
          out.push({ id: 'tsess_' + s.id, icon: '📅', title: `Сегодня в ${s.time}: ${c.name}`, body: s.title, kind: 'reminder', clientId: c.id })
        }
      }
    }
  }
  return out.filter(r => !store.dismissedReminders.includes(r.id))
}
