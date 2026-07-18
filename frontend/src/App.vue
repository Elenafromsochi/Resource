<script setup>
import { reactive, ref, onMounted, computed, nextTick, watch } from 'vue'
import { api, getToken, setToken, yandexLoginUrl } from './api.js'

const error = ref('')
const notice = ref('')
const profile = ref(null)
const loggedIn = ref(!!getToken())
const tab = ref('resources')  // resources | needs | match | track | profile
const yandexLogin = ref(false)  // показывать ли кнопку «Войти через Яндекс»

// --- вход / регистрация ---
const auth = reactive({ email: '', password: '', mode: 'login' })
async function submitAuth() {
  error.value = ''
  try {
    const fn = auth.mode === 'register' ? api.register : api.login
    const { access_token } = await fn({ email: auth.email, password: auth.password })
    setToken(access_token); loggedIn.value = true; await loadProfile()
  } catch (e) { error.value = e.message }
}
function loginWithYandex() { window.location.href = yandexLoginUrl }
function logout() { setToken(null); loggedIn.value = false; profile.value = null }

// Возврат после входа через Яндекс: токен (или ошибка) приходит в адресе.
function pickUpOAuthResult() {
  const p = new URLSearchParams(window.location.search)
  const token = p.get('token'); const authError = p.get('auth_error')
  if (token) { setToken(token); loggedIn.value = true }
  if (authError) error.value = 'Не удалось войти через Яндекс. Попробуйте ещё раз или войдите по почте.'
  if (token || authError) window.history.replaceState({}, '', window.location.pathname)
}

// --- профиль ---
const form = reactive({
  full_name: '', avatar: '', occupation: '', city: '', about: '',
  skills: [], interests: [], goals: '', contacts: '', answers: {}, resources: [],
})
function fill(data) { Object.keys(form).forEach(k => { if (k in data && data[k] != null) form[k] = data[k] }) }
async function loadProfile() {
  try { profile.value = await api.getProfile(); fill(profile.value) }
  catch (e) { logout(); error.value = 'Пожалуйста, войдите снова.' }
}
onMounted(async () => {
  pickUpOAuthResult()
  try { yandexLogin.value = (await api.getConfig()).yandex_login } catch { /* не критично */ }
  if (loggedIn.value) loadProfile()
})
async function save() {
  error.value = ''
  try { profile.value = await api.saveProfile({ ...form }); fill(profile.value) }
  catch (e) { error.value = e.message }
}

// --- ИИ-помощник ---
// Помощник-«выявитель» временно скрыт: вернём позже на YandexGPT, поверх базы Даю/Прошу.
const showAssistant = false
const story = ref(''); const suggestions = ref([]); const busy = ref(false); const provider = ref('')
const providerLabel = computed(() => ({ yandex: 'YandexGPT', claude: 'Claude' })[provider.value] || 'офлайн')
async function runAssist() {
  error.value = ''; busy.value = true
  try {
    const r = await api.assist(story.value)
    provider.value = r.provider
    for (const k of ['full_name', 'occupation', 'city']) if (r.draft[k]) form[k] = r.draft[k]
    const s = [...(r.draft.skills || []), ...(r.draft.interests || [])]
    if (r.draft.occupation) s.unshift(r.draft.occupation)
    suggestions.value = [...new Set(s)].slice(0, 8)
  } catch (e) { error.value = e.message } finally { busy.value = false }
}

// --- голосовой ввод ---
const SR = window.SpeechRecognition || window.webkitSpeechRecognition
const voiceSupported = !!SR
const listeningField = ref('')
let activeRec = null
let voiceStop = false
// Непрерывная запись: паузы не прерывают, останавливается только вручную
// (повторным нажатием 🎤). На паузах авто-возобновляется.
function listen(key, appendText) {
  if (listeningField.value === key) { voiceStop = true; if (activeRec) activeRec.stop(); return }
  if (!SR) { error.value = 'На iPhone/iPad нажмите 🎤 на клавиатуре. В Chrome работает эта кнопка.'; return }
  voiceStop = false
  listeningField.value = key
  const begin = () => {
    const rec = new SR()
    rec.lang = 'ru-RU'; rec.interimResults = false; rec.continuous = true; rec.maxAlternatives = 1
    activeRec = rec
    rec.onresult = (e) => {
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) appendText(e.results[i][0].transcript)
      }
    }
    rec.onerror = (ev) => {
      if (ev.error === 'not-allowed' || ev.error === 'service-not-allowed') {
        error.value = 'Разрешите доступ к микрофону.'; voiceStop = true
      }
    }
    rec.onend = () => {
      if (voiceStop) { listeningField.value = ''; activeRec = null }
      else begin()
    }
    try { rec.start() } catch (_) { }
  }
  begin()
}
function appendStory(t) { story.value = story.value ? story.value + ' ' + t : t }

// --- КОНФИГ КАТЕГОРИЙ (поля под каждую, зеркально для Даю/Прошу) ---
const CATS = {
  time_skill: { label: 'Время / Навык / Услуга', icon: '🛠', give: [
    { key: 'level', q: 'Уровень', options: ['Новичок', 'Уверенный любитель', 'Профи'] },
    { key: 'volume', q: 'Сколько времени / регулярность', options: ['Разово 1–2 ч', '1–2 ч/нед', '3–5 ч/нед', 'Ежедневно по графику', 'По договорённости'] },
    { key: 'when', q: 'Когда', options: ['Будни', 'Выходные', 'Гибко'] },
    { key: 'terms', q: 'Условия', options: ['Дар', 'За баллы', 'Обмен', 'Деньги'] },
    { key: 'where', q: 'Где', options: ['У меня', 'У тебя', 'Онлайн'] },
  ], ask: [
    { key: 'level', q: 'Мин. уровень исполнителя', options: ['Новичок', 'Уверенный любитель', 'Профи'] },
    { key: 'volume', q: 'Сколько времени нужно', options: ['Разово 1–2 ч', '1–2 ч/нед', '3–5 ч/нед', 'Ежедневно', 'По договорённости'] },
    { key: 'urgency', q: 'Срочность', options: ['1–2 дня', 'Неделя', 'Не срочно', 'Регулярно'] },
    { key: 'terms', q: 'Условия', options: ['Приму в дар', 'За баллы', 'Обмен', 'Куплю'] },
    { key: 'where', q: 'Где нужно', options: ['У меня', 'У тебя', 'Онлайн'] },
  ] },
  thing: { label: 'Вещь / Товар', icon: '📦', give: [
    { key: 'condition', q: 'Состояние', options: ['Новое', 'Б/у как новое', 'Отличное', 'Хорошее', 'С дефектами', 'На ремонт'] },
    { key: 'terms', q: 'Условия', options: ['Дар', 'Аренда за баллы', 'Аренда за деньги', 'Обмен', 'Продам'] },
    { key: 'where', q: 'Откуда забрать (город/район)', type: 'text' },
  ], ask: [
    { key: 'condition', q: 'Мин. приемлемое состояние', options: ['Любое', 'Хорошее', 'Отличное', 'Новое'] },
    { key: 'terms', q: 'Условия', options: ['Дар', 'Аренда', 'Обмен', 'Куплю'] },
    { key: 'where', q: 'Район', type: 'text' },
  ] },
  space: { label: 'Пространство / Место', icon: '🏠', give: [
    { key: 'purpose', q: 'Для чего подходит', options: ['Хранение', 'Работа/учёба', 'Мероприятие', 'Проживание'] },
    { key: 'capacity', q: 'Площадь / вместимость', type: 'text' },
    { key: 'terms', q: 'Условия', options: ['Обмен', 'За баллы', 'Аренда за баллы', 'Аренда за деньги', 'Деньги'] },
    { key: 'schedule', q: 'График', options: ['Разово', 'Регулярно', 'Длительно', 'Навсегда'] },
  ], ask: [
    { key: 'purpose', q: 'Цель', options: ['Хранение', 'Работа/учёба', 'Мероприятие', 'Проживание'] },
    { key: 'capacity', q: 'Нужные характеристики', type: 'text', hint: 'площадь + свет/интернет/ключ…' },
    { key: 'terms', q: 'Условия', options: ['Обмен', 'За баллы', 'Аренда', 'Деньги'] },
    { key: 'schedule', q: 'График', options: ['Разово', 'Регулярно', 'Длительно', 'Навсегда'] },
  ] },
  knowledge: { label: 'Знание / Опыт', icon: '📚', give: [
    { key: 'topic', q: 'Сфера / тема', type: 'text' },
    { key: 'format', q: 'Формат', options: ['Краткий ответ', 'Консультация до 60 мин', 'Менторство', 'Записанные уроки'] },
    { key: 'channel', q: 'Способ', options: ['Текст', 'Видео', 'Встреча', 'Телефон'] },
    { key: 'terms', q: 'Условия', options: ['Обмен', 'За баллы', 'Деньги'] },
  ], ask: [
    { key: 'topic', q: 'Сфера / тема', type: 'text' },
    { key: 'format', q: 'Формат', options: ['Краткий ответ', 'Консультация до 60 мин', 'Менторство', 'Записанные уроки'] },
    { key: 'channel', q: 'Способ', options: ['Текст', 'Видео', 'Встреча', 'Телефон'] },
    { key: 'terms', q: 'Условия', options: ['Обмен', 'За баллы', 'Куплю'] },
  ] },
}
const CAT_KEYS = Object.keys(CATS)
function catLabel(c) { return CATS[c]?.label || c }

// --- мастер (пошагово, с учётом категории) ---
const wiz = reactive({ open: false, type: 'give', step: 0, draft: emptyDraft(), editId: null })
function emptyDraft() { return { category: '', title: '', description: '', impact: '', fields: {}, ideal: '', term: '', customDate: '', amount_money: '', amount_points: '' } }
function startWizard(type, presetTitle = '') {
  wiz.type = type; wiz.step = 0; wiz.draft = emptyDraft(); wiz.editId = null
  extractQuestions.value = []; extractProvider.value = ''
  if (presetTitle) wiz.draft.title = presetTitle
  wiz.open = true
}
// «Рассказать»: наговорил одним текстом → ИИ разложил по карточке (открывается мастер прифилленным).
const tell = reactive({ open: false, type: 'give', text: '', photo: null, busy: false })
const extractQuestions = ref([])
const extractProvider = ref('')
const clarification = reactive({ open: false, questionPairs: [], answers: {}, busy: false, currentDraft: null })
// Новая система Intake (две независимые модели)
const intake = reactive({ open: false, type: 'give', state: null, currentQuestion: null, questionIndex: 0, questions: [], answers: {}, busy: false })
function openTell(type) { tell.type = type; tell.text = ''; tell.photo = null; tell.open = true; extractQuestions.value = [] }
function handlePhotoUpload(e) { const file = e.target.files?.[0]; if (file) { const r = new FileReader(); r.onload = ev => tell.photo = ev.target.result; r.readAsDataURL(file) } }
async function runExtract() {
  tell.busy = true; error.value = ''
  try {
    const d = await api.extract(tell.text, tell.type)
    extractProvider.value = d.provider
    wiz.type = tell.type; wiz.editId = null
    wiz.draft = {
      category: d.category || '', title: d.title || '', description: d.description || '',
      impact: d.impact || '', fields: { ...(d.fields || {}) }, ideal: d.ideal || '',
      term: '', customDate: '', amount_money: d.amount_money || d.amount || '', amount_points: d.amount_points || '',
    }
    wiz.step = wiz.draft.category ? 1 : 0
    extractQuestions.value = d.questions || []

    // Если есть уточняющие вопросы — показываем их отдельно перед мастером
    if (d.questions && d.questions.length > 0 && d.questions_map) {
      // Строим пары (field, question) из questions_map
      clarification.questionPairs = Object.entries(d.questions_map).map(([field, question]) => ({ field, question }))
      clarification.answers = {}
      clarification.currentDraft = { ...wiz.draft, questions_map: d.questions_map || {}, provider: extractProvider.value }
      clarification.open = true
      tell.open = false
    } else {
      wiz.open = true; tell.open = false
    }
  } catch (e) { error.value = e.message } finally { tell.busy = false }
}
async function submitClarifications() {
  clarification.busy = true; error.value = ''
  try {
    const updated = await api.clarify(clarification.currentDraft, clarification.answers)
    // Обновляем черновик с уточнениями
    wiz.draft = {
      category: updated.category || '', title: updated.title || '', description: updated.description || '',
      impact: updated.impact || '', fields: { ...(updated.fields || {}) }, ideal: updated.ideal || '',
      term: '', customDate: '', amount_money: updated.amount_money || '', amount_points: updated.amount_points || '',
    }
    extractQuestions.value = updated.questions || []
    clarification.open = false
    wiz.open = true
  } catch (e) { error.value = e.message } finally { clarification.busy = false }
}

// Новая система Intake
async function runIntakeExtract() {
  tell.busy = true; error.value = ''
  try {
    const state = await api.extractIntake(tell.text, null)
    intake.state = state
    intake.type = tell.type
    intake.answers = {}
    intake.questionIndex = 0

    // Получаем первую волну вопросов
    const clarifyResult = await api.clarifyIntake(state)
    intake.questions = clarifyResult.questions || []

    if (clarifyResult.stop_reason === 'ready_to_search') {
      // Достаточно данных, открываем редактор или поиск
      loadCardFromIntake()
    } else if (intake.questions.length > 0) {
      // Показываем первый вопрос
      intake.currentQuestion = intake.questions[0]
      intake.open = true
      tell.open = false
    } else {
      // Нет вопросов и не готово к поиску — откроем редактор
      loadCardFromIntake()
    }
  } catch (e) { error.value = e.message } finally { tell.busy = false }
}

async function submitIntakeAnswer() {
  intake.busy = true; error.value = ''
  try {
    const field = intake.currentQuestion.field
    let answer = intake.answers[field]
    if (!answer) throw new Error('Пожалуйста, ответьте на вопрос')

    // Преобразуем ответ в правильный формат для backend
    if (field === 'counter_value') {
      // counter_value должен быть список (может быть несколько вариантов)
      if (Array.isArray(answer)) {
        answer = answer.map(v => {
          const lower = v.toLowerCase()
          if (lower.includes('дар')) return 'gift'
          if (lower.includes('деньг')) return 'money'
          if (lower.includes('обмен')) return 'barter'
          if (lower.includes('балл')) return 'unit'
          return 'gift'
        })
      } else {
        // На случай если пришла одна строка
        answer = [answer.toLowerCase().includes('дар') ? 'gift' :
                  answer.toLowerCase().includes('деньг') ? 'money' :
                  answer.toLowerCase().includes('обмен') ? 'barter' :
                  answer.toLowerCase().includes('балл') ? 'unit' : 'gift']
      }
    } else if (field === 'object_level') {
      // object_level должен быть число
      answer = parseInt(answer) || null
    } else if (field === 'when_type') {
      // when_type преобразуем к нижнему регистру
      answer = answer.toLowerCase().includes('разово') ? 'once' :
               answer.toLowerCase().includes('периодич') ? 'period' :
               answer.toLowerCase().includes('регулярно') ? 'regular' : answer
    }

    // Обновляем state
    intake.state[field] = answer

    // Получаем следующую волну вопросов
    const clarifyResult = await api.clarifyIntake(intake.state)

    if (clarifyResult.stop_reason === 'ready_to_search') {
      loadCardFromIntake()
      intake.open = false
    } else if (clarifyResult.questions && clarifyResult.questions.length > 0) {
      // Показываем следующий вопрос
      intake.currentQuestion = clarifyResult.questions[0]
      intake.questions = clarifyResult.questions
      intake.questionIndex += 1
    } else {
      // Нет больше вопросов
      loadCardFromIntake()
      intake.open = false
    }
  } catch (e) { error.value = e.message } finally { intake.busy = false }
}

function isAnswerValid(answer) {
  if (!answer) return false
  if (Array.isArray(answer)) {
    return answer.length > 0  // Empty array is not valid
  }
  return true
}

function isSelected(variant) {
  const selected = intake.answers[intake.currentQuestion.field]
  if (Array.isArray(selected)) {
    return selected.includes(variant)
  }
  return false
}

function toggleCounterValue(variant) {
  // Инициализируем как пустой массив если нет
  if (!Array.isArray(intake.answers[intake.currentQuestion.field])) {
    intake.answers[intake.currentQuestion.field] = []
  }

  const selected = intake.answers[intake.currentQuestion.field]
  const index = selected.indexOf(variant)

  if (index > -1) {
    // Уже выбран — удаляем
    selected.splice(index, 1)
  } else {
    // Не выбран — добавляем
    selected.push(variant)
  }

  // Показываем уведомление если выбран обмен на потребности
  if (variant.includes('потребности') && index === -1) {
    if (activeAsks.length > 0) {
      notice.value = `Обмен включен. Ваши потребности: ${activeAsks.map(a => a.title).join(', ')}`
    } else {
      notice.value = 'Добавьте потребности, чтобы обмениваться ресурсами'
    }
  }
}

function selectIntakeVariant(variant) {
  intake.answers[intake.currentQuestion.field] = variant
}

function loadCardFromIntake() {
  // Загружаем карточку из intake state
  wiz.type = intake.type; wiz.editId = null
  wiz.draft = {
    category: intake.state.category || '',
    title: intake.state.object_text || '',
    description: intake.state.object_text || '',
    impact: '',
    fields: {
      level: intake.state.object_level,
      where: intake.state.where_geo || intake.state.where_mode
    },
    ideal: '',
    term: '',
    customDate: '',
    amount_money: '',
    amount_points: ''
  }
  wiz.step = wiz.draft.category ? 1 : 0
  wiz.open = true
}

function startEdit(r) {
  wiz.type = r.type; wiz.editId = r.id
  wiz.draft = {
    category: r.category || '', title: r.title || '', description: r.description || r.entry || '', impact: r.impact || '',
    fields: { ...(r.fields || {}) }, ideal: r.ideal || '', term: r.term || '', customDate: r.customDate || '',
    amount_money: r.amount_money || r.amount || '', amount_points: r.amount_points || '',
  }
  wiz.step = r.category ? 1 : 0  // категория уже выбрана — сразу к сути
  wiz.open = true
}
const wsteps = computed(() => {
  const t = wiz.type
  const base = [{ key: 'category', kind: 'category', q: 'К какой категории ближе?' }]
  if (!wiz.draft.category) return base
  const fields = CATS[wiz.draft.category][t]
  const descQ = t === 'give'
    ? 'Опишите подробнее (можно голосом)'
    : 'Опишите идеальную картину решения — как всё выглядит, когда задача решена? (можно голосом)'
  const steps = [
    ...base,
    { key: 'title', kind: 'text', q: 'Короткое название — существительным',
      hint: 'напр.: «Жильё у моря», «Массаж», «Консультация». Подробности — на след. шаге' },
    { key: 'description', kind: 'text', q: descQ },
  ]
  // Польза (impact) — только у потребности/проекта.
  if (t === 'ask') steps.push({ key: 'impact', kind: 'text',
    q: 'Какую пользу миру, сообществу, человеку или природе принесёт решение этой задачи?',
    hint: 'зачем это в большом смысле' })
  steps.push(...fields.map(f => ({ key: f.key, kind: f.key === 'terms' ? 'multiterms' : (f.type === 'text' ? 'text' : 'choice'), q: f.q, hint: f.key === 'terms' ? 'можно выбрать несколько; сумма — тут же' : f.hint, options: f.options || [], inFields: true })))
  // «Кому идеально» — только у ресурса.
  if (t === 'give') steps.push({ key: 'ideal', kind: 'text', q: 'Кому и в каких условиях этот ресурс идеально подойдёт?' })
  // Срок жизни потребности.
  if (t === 'ask') steps.push({ key: 'term', kind: 'term', q: 'На какой срок эта потребность?',
    options: ['Неделя', '2 недели', 'Месяц', 'Своя дата'] })
  return steps
})
const cur = computed(() => wsteps.value[wiz.step] || wsteps.value[0])
function curVal() {
  const s = cur.value
  if (s.kind === 'category') return wiz.draft.category
  if (s.key === 'important') return wiz.draft.important
  if (s.inFields) return wiz.draft.fields[s.key] || ''
  return wiz.draft[s.key] || ''
}
function setCur(val) {
  const s = cur.value
  if (s.kind === 'category') wiz.draft.category = val
  else if (s.inFields) wiz.draft.fields[s.key] = val
  else wiz.draft[s.key] = val
}
function toggleTerm(o) {
  const cur = wiz.draft.fields.terms
  const arr = Array.isArray(cur) ? cur.slice() : (cur ? [cur] : [])
  const i = arr.indexOf(o)
  if (i >= 0) arr.splice(i, 1); else arr.push(o)
  wiz.draft.fields.terms = arr
}
// Условия могут быть строкой (старые записи) или массивом (новые) — приводим к списку.
function termList(r) {
  const t = r.fields?.terms
  return Array.isArray(t) ? t : (t ? [t] : [])
}
// «У меня» подтягивает город из профиля (если он заполнен).
function pickOption(o) {
  if (cur.value.key === 'where' && o === 'У меня' && form.city) { setCur('У меня, ' + form.city); return }
  setCur(o)
}
// Выбраны ли платные условия — тогда прямо в окне условий спрашиваем сумму.
const moneySel = computed(() => termList(wiz.draft).some(t => /деньг|куп|прод/i.test(t)))
const pointsSel = computed(() => termList(wiz.draft).some(t => /балл/i.test(t)))
const canProceed = computed(() => {
  const s = cur.value
  if (s.kind === 'category') return !!wiz.draft.category
  if (s.key === 'title') return !!wiz.draft.title.trim()
  return true
})
function wizNext() { if (wiz.step < wsteps.value.length - 1) wiz.step++; else finishWizard() }
function wizBack() { if (wiz.step > 0) wiz.step--; else wiz.open = false }
function computeDeadline(d) {
  if (!d.term) return ''
  if (d.term === 'Своя дата') return d.customDate || ''
  const days = { 'Неделя': 7, '2 недели': 14, 'Месяц': 30 }[d.term] || 0
  const x = new Date(); x.setDate(x.getDate() + days)
  return x.toISOString().slice(0, 10)
}
function finishWizard() {
  const data = { type: wiz.type, ...JSON.parse(JSON.stringify(wiz.draft)) }
  if (wiz.type === 'ask') data.deadline = computeDeadline(wiz.draft)
  if (wiz.editId) {
    const i = form.resources.findIndex(x => x.id === wiz.editId)
    if (i >= 0) form.resources[i] = { ...form.resources[i], ...data, id: wiz.editId }
  } else {
    form.resources.push({ id: `${Date.now()}${Math.floor(Math.random() * 1000)}`, ...data })
  }
  wiz.open = false; wiz.editId = null; extractQuestions.value = []; extractProvider.value = ''; save()
  // Бартер: обмен требует описанных потребностей.
  const barter = termList({ fields: data.fields }).some(x => /обмен|бартер/i.test(x))
  if (barter) {
    if (asks.value.length === 0) {
      notice.value = 'Вы выбрали обмен — опишите, что хотите взамен (свою потребность).'
      tab.value = 'needs'
    } else {
      notice.value = 'Обмен: загляните в «Потребности» — вдруг появились новые.'
    }
  }
}
function removeItem(id) { form.resources = form.resources.filter(r => r.id !== id); save() }
const expanded = reactive({})
function toggle(id) { expanded[id] = !expanded[id] }
const gives = computed(() => form.resources.filter(r => r.type === 'give'))
const asks = computed(() => form.resources.filter(r => r.type === 'ask'))
// Срок жизни потребности: пока не вышел — в ленте; вышел — в архив (но остаётся для мэтча).
function todayISO() { return new Date().toISOString().slice(0, 10) }
function isArchived(r) { return !!(r.deadline && r.deadline < todayISO()) }
const activeAsks = computed(() => asks.value.filter(r => !isArchived(r)))
const archivedAsks = computed(() => asks.value.filter(r => isArchived(r)))
function fmtDate(iso) { return iso ? iso.split('-').reverse().slice(0, 2).join('.') : '' }
function itemFields(r) {
  const cfg = CATS[r.category]?.[r.type] || []
  return cfg.map(f => ({ key: f.key, label: f.q, value: r.fields?.[f.key] })).filter(x => x.value)
}
// Иконки параметров и условий — чтобы карточка читалась «глазами», а не текстом.
const FIELD_ICON = { level: '🎚', volume: '⏳', when: '📅', urgency: '⏰', where: '📍',
  condition: '🏷', purpose: '🎯', capacity: '📐', schedule: '🗓', topic: '📚', format: '🎓', channel: '💬', size: '📏', location: '🗺', target_level: '👥' }
const CRITICAL_FIELDS = {
  time_skill: ['level', 'where'],
  thing: ['condition', 'where'],
  space: ['capacity', 'schedule'],
  knowledge: ['topic', 'format'],
}
function fieldIcon(k) { return FIELD_ICON[k] || '•' }
// Критические поля для саморезации (выделяются на карточке)
function criticalFields(r) {
  const critical = CRITICAL_FIELDS[r.category] || []
  return itemFields(r).filter(f => critical.includes(f.key))
}
// Прочие важные поля
function keyFields(r) { return itemFields(r).filter(f => f.key !== 'terms' && f.key !== 'where' && !CRITICAL_FIELDS[r.category]?.includes(f.key)) }
function termIcon(v) {
  const s = (v || '').toLowerCase()
  if (s.includes('дар') || s.includes('подар')) return '🎁'
  if (s.includes('обмен')) return '🔄'
  if (s.includes('балл')) return '⭐'
  if (s.includes('аренд')) return '📅'
  if (s.includes('деньг') || s.includes('куп') || s.includes('прод')) return '💰'
  return '🤝'
}
function importantLabels(r) {
  const cfg = CATS[r.category]?.[r.type] || []
  return (r.important || []).map(k => cfg.find(f => f.key === k)?.q).filter(Boolean)
}

// --- геймификация «глубины» ---
const CIRC = 2 * Math.PI * 52
const depth = computed(() => Math.min(100, form.resources.length * 20))
const ringDash = computed(() => `${(depth.value / 100) * CIRC} ${CIRC}`)
const depthLevel = computed(() => {
  const n = form.resources.length
  if (n === 0) return 'Начало пути'; if (n < 3) return 'Поверхность'
  if (n < 5) return 'Копаем глубже'; return 'Глубоко'
})
const initial = computed(() => (form.full_name || profile.value?.email || '?').trim()[0].toUpperCase())

// Поле мастера растёт под объём текста: сколько строк — столько и высота, видно сразу.
const wizField = ref(null)
function autogrow() {
  const el = wizField.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, window.innerHeight * 0.5) + 'px'
}
watch(() => [wiz.open, wiz.step], () => nextTick(autogrow))

// Фото профиля: выбор файла → уменьшаем до 160px → data URL в профиль.
const photoInput = ref(null)
function pickPhoto() { if (photoInput.value) photoInput.value.click() }
function onPhoto(e) {
  const file = e.target.files && e.target.files[0]
  if (!file) return
  if (!file.type.startsWith('image/')) { error.value = 'Для аватара выберите фото (видео пока не поддерживается).'; return }
  const img = new Image()
  img.onload = () => {
    const max = 160, scale = Math.min(1, max / Math.max(img.width, img.height))
    const c = document.createElement('canvas')
    c.width = Math.round(img.width * scale); c.height = Math.round(img.height * scale)
    c.getContext('2d').drawImage(img, 0, 0, c.width, c.height)
    form.avatar = c.toDataURL('image/jpeg', 0.82)
    save()
  }
  img.src = URL.createObjectURL(file)
}
</script>

<template>
  <div class="app">
    <p v-if="error" class="err">{{ error }}</p>
    <p v-if="notice" class="notice" @click="notice = ''">{{ notice }}</p>

    <!-- Вход -->
    <section v-if="!loggedIn" class="auth">
      <img class="logo" src="/icon.svg" alt="Ресурс" width="96" height="96" />
      <div class="brand">Ресурс</div>
      <p class="tag">синергия ресурсов и потребностей</p>
      <div class="card">
        <button v-if="yandexLogin" class="ya" @click="loginWithYandex">
          <span class="ya-ic">Я</span> Войти через Яндекс
        </button>
        <div v-if="yandexLogin" class="or"><span>или по почте</span></div>
        <div class="lbl">{{ auth.mode === 'register' ? 'Регистрация' : 'Вход' }}</div>
        <input v-model="auth.email" type="email" placeholder="Email" />
        <input v-model="auth.password" type="password" placeholder="Пароль (от 6 символов)" />
        <button class="gold" @click="submitAuth">{{ auth.mode === 'register' ? 'Создать аккаунт' : 'Войти' }}</button>
        <a href="#" @click.prevent="auth.mode = auth.mode === 'login' ? 'register' : 'login'">
          {{ auth.mode === 'login' ? 'Ещё нет аккаунта — зарегистрироваться' : 'У меня уже есть аккаунт' }}</a>
      </div>
    </section>

    <!-- Кабинет -->
    <template v-else-if="profile">
      <!-- ВКЛАДКА: РЕСУРСЫ -->
      <section v-if="tab === 'resources'" class="block">
        <div class="bhead"><span class="btitle">🤝 Ресурсы</span>
          <div class="bactions">
            <button class="add gold-add" @click="openTell('give')">🎤 Рассказать</button>
            <button class="add" @click="startWizard('give')">Вручную</button>
          </div>
        </div>
        <p v-if="!gives.length" class="empty">Пока пусто. Что готовы дать, обменять или продать?</p>
        <div v-for="r in gives" :key="r.id" class="infographic-card">
          <button class="xbtn" @click="removeItem(r.id)">✕</button>
          <div class="card-type">Ресурс</div>
          <div class="card-main">
            <div class="card-icon">{{ CATS[r.category]?.icon }}</div>
            <div class="card-title">{{ r.title }}</div>
            <div v-if="r.description" class="card-desc">{{ r.description }}</div>
          </div>
          <div class="card-critical">
            <div class="critical-grid">
              <template v-for="f in criticalFields(r)" :key="f.key">
                <div class="critical-param">
                  <span class="param-icon">{{ fieldIcon(f.key) }}</span>
                  <span class="param-value">{{ f.value }}</span>
                </div>
              </template>
            </div>
          </div>
          <div v-if="keyFields(r).length" class="card-params">
            <div class="param-grid">
              <template v-for="f in keyFields(r)" :key="f.key">
                <div class="param">
                  <span class="param-icon">{{ fieldIcon(f.key) }}</span>
                  <span class="param-value">{{ f.value }}</span>
                </div>
              </template>
            </div>
          </div>
          <div class="card-terms">
            <div class="term-label">Условия</div>
            <div class="term-list">
              <span v-if="termList(r).length" v-for="t in termList(r)" :key="t" class="term-badge">{{ termIcon(t) }} {{ t }}</span>
              <span v-else class="term-badge">—</span>
              <span v-if="r.amount_money" class="amount-badge">💰 {{ r.amount_money }} ₽</span>
              <span v-if="r.amount_points" class="amount-badge">⭐ {{ r.amount_points }}</span>
            </div>
          </div>
          <div v-if="r.fields?.where" class="card-location">
            <span class="loc-icon">📍</span>
            <span>{{ r.fields.where }}</span>
          </div>
          <div v-if="r.ideal" class="card-ideal">
            <span class="ideal-label">Идеально для</span>
            <span class="ideal-text">{{ r.ideal }}</span>
          </div>
          <div class="card-actions">
            <button class="action-btn" @click="startEdit(r)">✏️ Изменить</button>
          </div>
        </div>
      </section>

      <!-- ВКЛАДКА: ПОТРЕБНОСТИ -->
      <template v-if="tab === 'needs'">
        <section class="block">
          <div class="bhead"><span class="btitle">🙏 Потребности</span>
            <div class="bactions">
              <button class="add gold-add" @click="openTell('ask')">🎤 Рассказать</button>
              <button class="add" @click="startWizard('ask')">Вручную</button>
            </div>
          </div>
          <p v-if="!activeAsks.length" class="empty">Пока пусто. Что вам нужно, ищете или хотите купить?</p>
          <div v-for="r in activeAsks" :key="r.id" class="infographic-card">
            <button class="xbtn" @click="removeItem(r.id)">✕</button>
            <div class="card-type">Потребность</div>
            <div class="card-main">
              <div class="card-icon">{{ CATS[r.category]?.icon }}</div>
              <div class="card-title">{{ r.title }}</div>
              <div v-if="r.description" class="card-desc">{{ r.description }}</div>
            </div>
            <div class="card-critical">
              <div class="critical-grid">
                <template v-for="f in criticalFields(r)" :key="f.key">
                  <div class="critical-param">
                    <span class="param-icon">{{ fieldIcon(f.key) }}</span>
                    <span class="param-value">{{ f.value }}</span>
                  </div>
                </template>
              </div>
            </div>
            <div v-if="keyFields(r).length" class="card-params">
              <div class="param-grid">
                <template v-for="f in keyFields(r)" :key="f.key">
                  <div class="param">
                    <span class="param-icon">{{ fieldIcon(f.key) }}</span>
                    <span class="param-value">{{ f.value }}</span>
                  </div>
                </template>
              </div>
            </div>
            <div class="card-terms">
              <div class="term-label">Условия</div>
              <div class="term-list">
                <span v-if="termList(r).length" v-for="t in termList(r)" :key="t" class="term-badge">{{ termIcon(t) }} {{ t }}</span>
                <span v-else class="term-badge">—</span>
                <span v-if="r.amount_money" class="amount-badge">💰 {{ r.amount_money }} ₽</span>
                <span v-if="r.amount_points" class="amount-badge">⭐ {{ r.amount_points }}</span>
              </div>
            </div>
            <div v-if="r.fields?.where" class="card-location">
              <span class="loc-icon">📍</span>
              <span>{{ r.fields.where }}</span>
            </div>
            <div v-if="r.deadline" class="card-deadline">
              <span class="deadline-icon">⏳</span>
              <span>до {{ fmtDate(r.deadline) }}</span>
            </div>
            <div v-if="r.impact" class="card-impact">
              <span class="impact-label">Польза мира</span>
              <span class="impact-text">{{ r.impact }}</span>
            </div>
            <div class="card-actions">
              <button class="action-btn" @click="startEdit(r)">✏️ Изменить</button>
            </div>
          </div>
        </section>
        <section v-if="archivedAsks.length" class="block">
          <div class="bhead"><span class="btitle">🗄 Архив</span></div>
          <p class="empty">Срок вышел — не в общей ленте, но остаются для будущего мэтча.</p>
          <div v-for="r in archivedAsks" :key="r.id" class="infographic-card archived">
            <button class="xbtn" @click="removeItem(r.id)">✕</button>
            <div class="card-type">Потребность · архив</div>
            <div class="card-main">
              <div class="card-icon">{{ CATS[r.category]?.icon }}</div>
              <div class="card-title">{{ r.title }}</div>
            </div>
          </div>
        </section>
      </template>

      <!-- ВКЛАДКА: МЭТЧ -->
      <section v-if="tab === 'match'" class="block">
        <div class="bhead"><span class="btitle">🔗 Мэтч</span></div>
        <p class="empty">Здесь появятся совпадения между вашими потребностями и чужими ресурсами. Внутри мэтча — переговоры и договорённость. Оживёт вместе с мэтчингом.</p>
      </section>

      <!-- ВКЛАДКА: ТРЕК (история сделки после договорённости) -->
      <section v-if="tab === 'track'" class="block">
        <div class="bhead"><span class="btitle">📈 Трек</span></div>
        <p class="empty">История сделки после договорённости: сопровождение по треку, учёт передачи ресурсов и обратная связь. Здесь же — прогресс «найдено ресурсов» и вклад участников (КТУ). Скоро.</p>
      </section>

      <!-- ВКЛАДКА: ПРОФИЛЬ -->
      <template v-if="tab === 'profile'">
        <header class="head">
          <div class="avatar" @click="pickPhoto" title="Изменить фото">
            <img v-if="form.avatar" :src="form.avatar" alt="" />
            <span v-else>{{ initial }}</span>
          </div>
          <input ref="photoInput" type="file" accept="image/*" @change="onPhoto" style="display:none" />
          <div class="who">
            <div class="name">{{ form.full_name || profile.email }}</div>
            <div class="sub">глубина раскрытия · {{ depthLevel }}</div>
          </div>
          <div class="ring">
            <svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="52" class="rbg" />
              <circle cx="60" cy="60" r="52" class="rfg" :stroke-dasharray="ringDash" /></svg>
            <span>{{ depth }}%</span>
          </div>
        </header>
        <p class="phint">нажмите на фото, чтобы изменить</p>
        <section class="card">
          <div class="lbl">Обо мне</div>
          <input v-model="form.full_name" placeholder="Имя" />
          <input v-model="form.city" placeholder="Город (или «удалённо»)" />
          <input v-model="form.contacts" placeholder="Контакты (@ник, почта)" />
          <button class="ghost" @click="save">Сохранить</button>
        </section>
        <button class="exit" @click="logout">Выйти</button>
      </template>

      <!-- Нижняя навигация -->
      <nav class="tabbar">
        <button :class="{ on: tab === 'resources' }" @click="tab = 'resources'"><span>🤝</span>Ресурсы</button>
        <button :class="{ on: tab === 'needs' }" @click="tab = 'needs'"><span>🙏</span>Потребности</button>
        <button :class="{ on: tab === 'match' }" @click="tab = 'match'"><span>🔗</span>Мэтч</button>
        <button :class="{ on: tab === 'track' }" @click="tab = 'track'"><span>📈</span>Трек</button>
        <button :class="{ on: tab === 'profile' }" @click="tab = 'profile'"><span>👤</span>Профиль</button>
      </nav>
    </template>

    <!-- Рассказать: наговорил всё → ИИ разложит по карточке -->
    <div v-if="tell.open" class="overlay" @click.self="tell.open = false">
      <div class="wizard">
        <div class="wlbl">{{ tell.type === 'give' ? 'РЕСУРС' : 'ПОТРЕБНОСТЬ' }} · расскажите одним текстом</div>
        <h3>Расскажи, что ты предлагаешь (или ищешь)</h3>
        <p class="hint">Главное — опиши так, чтобы человек сразу понял, можно ли это ему использовать. Что это, где, сколько человек, какие условия — всё можно наговорить разом. Если чего-то важного не хватит, мы спросим.</p>

        <div class="tell-photo">
          <div v-if="!tell.photo" class="photo-placeholder">
            <input type="file" accept="image/*" @change="handlePhotoUpload" style="display: none" ref="photoInput" />
            <button class="ghost" @click="$refs.photoInput?.$el?.click?.() || document.querySelector('input[type=file]')?.click?.()">
              📷 Добавить фото
            </button>
          </div>
          <div v-else class="photo-preview">
            <img :src="tell.photo" />
            <button class="ghost" @click="tell.photo = null">✕ Удалить</button>
          </div>
        </div>

        <div class="row">
          <textarea class="wiz-text" v-model="tell.text" rows="4" placeholder="Например: крыша с видом на горы, подходит для йоги и обедов, вмещает до 10 человек. Или: я провожу хатха-йогу, опыт 5 лет, работаю с начинающими…"></textarea>
          <button v-if="voiceSupported" class="ghost mic" :class="{ rec: listeningField === 'tell' }" @click="listen('tell', t => tell.text = (tell.text ? tell.text + ' ' : '') + t)">{{ listeningField === 'tell' ? '⏹' : '🎤' }}</button>
        </div>
        <div class="wnav">
          <button class="ghost" @click="tell.open = false">Отмена</button>
          <button class="gold" :disabled="tell.busy || !tell.text.trim()" @click="runIntakeExtract">{{ tell.busy ? 'Создаю…' : 'Создать карточку' }}</button>
        </div>
      </div>
    </div>

    <!-- Уточнение критичных полей карточки -->
    <div v-if="clarification.open" class="overlay" @click.self="clarification.open = false">
      <div class="wizard">
        <div class="wlbl">Уточнение информации</div>
        <h3>ИИ хочет уточнить кое-что важное</h3>
        <div class="clarifications">
          <div v-for="(pair, idx) in clarification.questionPairs" :key="idx" class="clarification-item">
            <label>{{ pair.question }}</label>
            <input v-model="clarification.answers[pair.field]" type="text" :placeholder="`Ответ ${idx + 1}`" />
          </div>
        </div>
        <div class="wnav">
          <button class="ghost" @click="clarification.open = false">Пропустить</button>
          <button class="gold" :disabled="clarification.busy || !Object.values(clarification.answers).some(a => a)" @click="submitClarifications">{{ clarification.busy ? 'Обновляю…' : 'Готово' }}</button>
        </div>
      </div>
    </div>

    <!-- Новая система Intake (один вопрос за раз) -->
    <div v-if="intake.open" class="overlay" @click.self="intake.open = false">
      <div class="wizard">
        <div class="wlbl">{{ intake.questionIndex + 1 }} из {{ intake.questions.length }}</div>
        <h3>{{ intake.currentQuestion?.text }}</h3>
        <p v-if="intake.currentQuestion?.explanation" class="hint">{{ intake.currentQuestion.explanation }}</p>

        <!-- Варианты ответов -->
        <div v-if="intake.currentQuestion?.variants" class="opts">
          <!-- Множественный выбор для counter_value -->
          <template v-if="intake.currentQuestion.field === 'counter_value'">
            <button v-for="variant in intake.currentQuestion.variants" :key="variant" class="chip" :class="{ sel: isSelected(variant) }" @click="toggleCounterValue(variant)">✓ {{ variant }}</button>
          </template>
          <!-- Одиночный выбор для остальных -->
          <template v-else>
            <button v-for="variant in intake.currentQuestion.variants" :key="variant" class="chip" :class="{ sel: intake.answers[intake.currentQuestion.field] === variant }" @click="selectIntakeVariant(variant)">{{ variant }}</button>
          </template>
        </div>

        <!-- Текстовый ввод (если нет вариантов) -->
        <input v-else v-model="intake.answers[intake.currentQuestion?.field]" type="text" class="wiz-text" :placeholder="'Ответ...'" />

        <div class="wnav">
          <button class="ghost" @click="intake.open = false">Пропустить</button>
          <button class="gold" :disabled="intake.busy || !isAnswerValid(intake.answers[intake.currentQuestion?.field])" @click="submitIntakeAnswer">{{ intake.busy ? 'Обновляю…' : 'Дальше' }}</button>
        </div>
      </div>
    </div>

    <!-- Мастер -->
    <div v-if="wiz.open" class="overlay" @click.self="wiz.open = false">
      <div class="wizard">
        <div class="dots"><i v-for="(s, i) in wsteps" :key="i" :class="{ on: i <= wiz.step }" /></div>
        <div class="wlbl">{{ wiz.type === 'give' ? 'РЕСУРС' : 'ПОТРЕБНОСТЬ' }} · {{ wiz.editId ? 'правка' : 'шаг ' + (wiz.step + 1) + ' из ' + wsteps.length }}</div>
        <div v-if="extractProvider === 'yandex'" class="wlbl" style="color: var(--gold); margin-top: 2px">разобрал: YandexGPT ✓</div>
        <h3>{{ cur.q }}</h3>
        <p v-if="cur.hint" class="hint">{{ cur.hint }}</p>

        <!-- выбор категории -->
        <div v-if="cur.kind === 'category'" class="opts">
          <button v-for="c in CAT_KEYS" :key="c" class="chip big" :class="{ sel: wiz.draft.category === c }" @click="wiz.draft.category = c">{{ CATS[c].icon }} {{ CATS[c].label }}</button>
        </div>

        <!-- срок потребности -->
        <div v-else-if="cur.kind === 'term'">
          <div class="opts">
            <button v-for="o in cur.options" :key="o" class="chip" :class="{ sel: wiz.draft.term === o }" @click="wiz.draft.term = o">{{ o }}</button>
          </div>
          <input v-if="wiz.draft.term === 'Своя дата'" type="date" v-model="wiz.draft.customDate" />
        </div>

        <!-- условия: можно выбрать несколько; сумма — тут же -->
        <div v-else-if="cur.kind === 'multiterms'">
          <div class="opts">
            <button v-for="o in cur.options" :key="o" class="chip" :class="{ sel: termList(wiz.draft).includes(o) }" @click="toggleTerm(o)">{{ o }}</button>
          </div>
          <input v-if="moneySel" v-model="wiz.draft.amount_money" placeholder="За какие деньги? напр.: 5000 ₽ / договорная" />
          <input v-if="pointsSel" v-model="wiz.draft.amount_points" placeholder="За сколько баллов? напр.: 200" />
        </div>

        <!-- выбор варианта / текст -->
        <template v-else>
          <div v-if="cur.options && cur.options.length" class="opts">
            <button v-for="o in cur.options" :key="o" class="chip" :class="{ sel: curVal() === o }" @click="pickOption(o)">{{ o }}</button>
          </div>
          <div class="row">
            <textarea ref="wizField" class="wiz-text" :value="curVal()" @input="e => { setCur(e.target.value); autogrow() }" rows="2" :placeholder="cur.options && cur.options.length ? 'или впишите своё' : 'ваш ответ'"></textarea>
            <button v-if="voiceSupported" class="ghost mic" :class="{ rec: listeningField === 'wiz' }" @click="listen('wiz', t => { setCur((curVal() ? curVal() + ' ' : '') + t); nextTick(autogrow) })">{{ listeningField === 'wiz' ? '⏹' : '🎤' }}</button>
          </div>
        </template>

        <div class="wnav">
          <button class="ghost" @click="wizBack">{{ wiz.step === 0 ? 'Отмена' : '← Назад' }}</button>
          <button class="gold" :disabled="!canProceed" @click="wizNext">{{ wiz.step === wsteps.length - 1 ? 'Готово' : 'Далее →' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
:root { --bg: #000; --panel: #0d0d0f; --input: #0a0a0c; --gold: #d9b45b; --gold2: #f0d38a;
  --line: rgba(217,180,91,.28); --cream: #ece3cf; --muted: #8f876f; }
* { box-sizing: border-box; }
html, body { background: #000; }
body { margin: 0; min-height: 100vh;
  background-image: radial-gradient(1200px 500px at 50% -220px, rgba(217,180,91,.07), transparent 70%);
  color: var(--cream); font-family: system-ui, -apple-system, sans-serif; }
.app { max-width: 620px; margin: 0 auto; padding: 18px 16px 90px; }
h3 { font-family: Georgia, 'Times New Roman', serif; font-weight: 600; margin: 6px 0; color: var(--cream); font-size: 21px; }
.err { background: #2a1414; border: 1px solid #6b2b2b; color: #f2b8b8; padding: 10px 12px; border-radius: 10px; font-size: 14px; }
.notice { background: rgba(217,180,91,.12); border: 1px solid var(--line); color: var(--gold); padding: 10px 12px; border-radius: 10px; font-size: 14px; cursor: pointer; }
.auth { text-align: center; padding-top: 40px; }
.logo { width: 96px; height: 96px; border-radius: 22px; margin-bottom: 6px; }
.brand { font-family: Georgia, serif; font-size: 40px; letter-spacing: 1px;
  background: linear-gradient(180deg, var(--gold2), var(--gold)); -webkit-background-clip: text; background-clip: text; color: transparent; }
.tag { color: var(--muted); letter-spacing: 1px; margin-top: 4px; }
.card, .block { background: var(--panel); border: 1px solid var(--line); border-radius: 18px; }
.wizard { background: var(--panel); border: 2px solid rgba(217,180,91,.5); border-radius: 18px; }
.card { padding: 18px; margin-top: 16px; box-shadow: 0 0 40px rgba(0,0,0,.4); }
.card.ai { border-color: rgba(217,180,91,.4); background: linear-gradient(180deg, rgba(217,180,91,.06), var(--panel)); }
.lbl { text-transform: uppercase; letter-spacing: 2px; font-size: 11px; color: var(--muted); margin-bottom: 8px; }
.ya { width: 100%; display: flex; align-items: center; justify-content: center; gap: 10px;
  background: #fff; color: #1a1a1a; border: none; border-radius: 12px; padding: 13px;
  font-size: 16px; font-weight: 600; cursor: pointer; }
.ya-ic { display: grid; place-items: center; width: 24px; height: 24px; border-radius: 6px;
  background: #fc3f1d; color: #fff; font-family: Georgia, serif; font-weight: 700; font-size: 17px; }
.or { display: flex; align-items: center; gap: 10px; color: var(--muted); font-size: 12px; margin: 14px 0; }
.or::before, .or::after { content: ''; flex: 1; height: 1px; background: var(--line); }
.gold-t { color: var(--gold); }
.hint { color: var(--muted); font-size: 14px; margin: 6px 0; } .hint.sm { font-size: 12px; }
.head { display: flex; align-items: center; gap: 14px; padding: 6px 2px 10px; }
.avatar { width: 54px; height: 54px; border-radius: 50%; border: 1px solid var(--line); display: grid; place-items: center; font-family: Georgia, serif; font-size: 22px; color: var(--gold); overflow: hidden; cursor: pointer; }
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.roles { display: flex; gap: 6px; margin-top: 5px; flex-wrap: wrap; }
.rolebadge { font-size: 10px; letter-spacing: 1px; text-transform: uppercase; border: 1px solid var(--line); color: var(--muted); border-radius: 6px; padding: 2px 8px; }
.rolebadge.exp { border-color: var(--gold); color: var(--gold); }
.phint { text-align: center; color: var(--muted); font-size: 11px; margin: -2px 0 0; }
.who { flex: 1; } .name { font-family: Georgia, serif; font-size: 19px; }
.sub { color: var(--gold); font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; }
.ring { position: relative; width: 60px; height: 60px; }
.ring svg { transform: rotate(-90deg); width: 60px; height: 60px; }
.ring .rbg { fill: none; stroke: rgba(255,255,255,.06); stroke-width: 6; }
.ring .rfg { fill: none; stroke: var(--gold); stroke-width: 6; stroke-linecap: round; transition: stroke-dasharray .5s; }
.ring span { position: absolute; inset: 0; display: grid; place-items: center; font-size: 13px; color: var(--gold); }
.block { padding: 14px; margin-top: 16px; }
.bhead { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.btitle { font-family: Georgia, serif; font-size: 20px; }
.empty { color: var(--muted); font-size: 14px; }
.infographic-card { position: relative; padding: 18px; margin-top: 12px;
  border: 2px solid rgba(217,180,91,.65); border-radius: 16px;
  background: linear-gradient(135deg, rgba(217,180,91,.08), rgba(217,180,91,.03));
  box-shadow: 0 8px 24px rgba(0,0,0,.5); }
.infographic-card.archived { opacity: .5; }
.card-type { font-size: 9px; letter-spacing: 2px; text-transform: uppercase; color: var(--gold); opacity: .7; margin-bottom: 10px; }
.card-main { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.card-icon { font-size: 36px; line-height: 1; }
.card-title { font-family: Georgia, serif; font-size: 22px; font-weight: 600; color: #fff; line-height: 1.2; }
.card-desc { font-size: 13px; color: var(--cream); opacity: .85; line-height: 1.4; white-space: pre-wrap; }
.card-critical { margin: 12px 0 8px; padding: 10px; background: rgba(217,180,91,.12); border-radius: 10px; border: 1px solid rgba(217,180,91,.4); }
.critical-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.critical-param { display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: rgba(217,180,91,.15); border-radius: 8px; border-left: 3px solid var(--gold); }
.card-params { margin: 8px 0; }
.param-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 14px; }
.param { display: flex; align-items: center; gap: 8px; padding: 8px; background: rgba(217,180,91,.05); border-radius: 8px; border: 1px solid rgba(217,180,91,.2); opacity: .85; }
.param-icon { font-size: 18px; min-width: 20px; }
.param-value { font-size: 13px; color: var(--cream); }
.card-terms { margin: 12px 0; padding: 10px; background: rgba(217,180,91,.08); border-radius: 8px; border-left: 3px solid var(--gold); }
.term-label { font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--gold); opacity: .7; margin-bottom: 6px; }
.term-list { display: flex; flex-wrap: wrap; gap: 8px; }
.term-badge { display: inline-block; padding: 5px 10px; background: rgba(217,180,91,.15); border: 1px solid var(--gold); border-radius: 6px; font-size: 12px; color: var(--gold); }
.amount-badge { display: inline-block; padding: 5px 10px; background: rgba(217,180,91,.2); border: 1px solid var(--gold); border-radius: 6px; font-size: 12px; color: var(--gold); font-weight: 600; }
.card-location { display: flex; align-items: center; gap: 8px; margin: 10px 0; font-size: 13px; color: var(--cream); }
.loc-icon { font-size: 16px; }
.card-deadline { display: flex; align-items: center; gap: 8px; margin: 10px 0; font-size: 13px; color: var(--cream); }
.deadline-icon { font-size: 16px; }
.card-ideal { display: flex; flex-direction: column; gap: 4px; margin: 10px 0; padding: 10px; background: rgba(217,180,91,.06); border-radius: 8px; }
.ideal-label { font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--gold); opacity: .7; }
.ideal-text { font-size: 13px; color: var(--cream); }
.card-impact { display: flex; flex-direction: column; gap: 4px; margin: 10px 0; padding: 10px; background: rgba(217,180,91,.06); border-radius: 8px; }
.impact-label { font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--gold); opacity: .7; }
.impact-text { font-size: 13px; color: var(--cream); }
.card-actions { display: flex; gap: 10px; margin-top: 14px; }
.action-btn { background: transparent; border: 1px solid var(--gold); color: var(--gold); padding: 8px 12px; font-size: 12px;
  border-radius: 6px; cursor: pointer; transition: all .2s; }
.action-btn:hover { background: rgba(217,180,91,.1); }
.wiz-text { min-height: 52px; line-height: 1.4; resize: none; overflow: hidden; }
.row .mic { align-self: flex-start; }
.tabbar { position: fixed; left: 50%; transform: translateX(-50%); bottom: 0; width: 100%; max-width: 620px;
  display: flex; background: rgba(10,10,12,.96); border-top: 1px solid var(--line);
  -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px); z-index: 5; }
.tabbar button { flex: 1; background: none; border: none; margin: 0; padding: 9px 1px calc(9px + env(safe-area-inset-bottom));
  display: flex; flex-direction: column; align-items: center; gap: 3px; color: var(--muted); font-size: 9.5px; }
.tabbar button span { font-size: 18px; opacity: .5; }
.tabbar button.on { color: var(--gold); }
.tabbar button.on span { opacity: 1; }
.xbtn { position: absolute; top: 8px; right: 8px; background: none; border: none; color: var(--muted); font-size: 15px; cursor: pointer; }
input, textarea { display: block; width: 100%; padding: 11px; margin-top: 8px; background: var(--input); border: 1px solid rgba(217,180,91,.3); border-radius: 10px; color: var(--cream); font: inherit; }
input::placeholder, textarea::placeholder { color: #5f5947; }
button { cursor: pointer; border-radius: 10px; font: inherit; padding: 10px 16px; margin-top: 10px; }
.gold { background: linear-gradient(180deg, var(--gold2), var(--gold)); color: #241d09; border: none; font-weight: 600; }
.gold:disabled { opacity: .4; }
.ghost { background: transparent; border: 1px solid rgba(217,180,91,.3); color: var(--cream); }
.ghost.rec { border-color: #e23; color: #f77; }
.add { background: transparent; border: 1px solid var(--gold); color: var(--gold); padding: 6px 12px; margin: 0; font-size: 13px; }
.bactions { display: flex; gap: 8px; flex-wrap: wrap; }
.gold-add { background: linear-gradient(180deg, var(--gold2), var(--gold)); color: #241d09; border: none; font-weight: 600; }
.exit { display: block; margin: 20px auto 0; background: none; border: none; color: var(--muted); }
.row { display: flex; gap: 8px; align-items: center; } .row input { flex: 1; } .row .mic { margin-top: 8px; }
a { color: var(--gold); display: inline-block; margin-top: 12px; font-size: 14px; }
.chip { background: var(--input); border: 1px solid var(--line); color: var(--cream); padding: 7px 12px; margin: 6px 6px 0 0; font-size: 14px; }
.chip.sel { border-color: var(--gold); color: var(--gold); }
.chip.big { display: block; width: 100%; text-align: left; margin: 8px 0 0; padding: 12px 14px; }
.sugs { margin-top: 12px; }
.prov { font-size: 12px; color: var(--muted); align-self: center; }
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.7); display: grid; place-items: center; padding: 16px; z-index: 10; }
.wizard { width: 100%; max-width: 460px; padding: 22px; max-height: 92vh; overflow: auto; }
.dots { display: flex; gap: 5px; margin-bottom: 12px; }
.dots i { flex: 1; height: 3px; border-radius: 3px; background: rgba(255,255,255,.1); } .dots i.on { background: var(--gold); }
.wlbl { font-size: 11px; letter-spacing: 2px; color: var(--muted); }
.opts { margin: 6px 0; }
.wnav { display: flex; justify-content: space-between; margin-top: 14px; }
.tell-photo { margin: 12px 0; }
.photo-placeholder { text-align: center; padding: 12px; background: rgba(255,215,0,.05); border-radius: 8px; }
.photo-preview { position: relative; margin: 12px 0; }
.photo-preview img { max-width: 100%; max-height: 200px; border-radius: 8px; }
.photo-preview button { position: absolute; top: 4px; right: 4px; padding: 4px 8px; font-size: 12px; }
.clarifications { margin: 12px 0; display: flex; flex-direction: column; gap: 12px; }
.clarification-item { display: flex; flex-direction: column; gap: 4px; }
.clarification-item label { font-size: 13px; color: var(--gold); font-weight: 500; }
.clarification-item input { margin-top: 4px; }
</style>
