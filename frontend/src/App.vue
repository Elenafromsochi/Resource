<script setup>
import { reactive, ref, onMounted, computed } from 'vue'
import { api, getToken, setToken } from './api.js'

const error = ref('')
const profile = ref(null)
const loggedIn = ref(!!getToken())

// --- вход / регистрация ---
const auth = reactive({ email: '', password: '', mode: 'login' })
async function submitAuth() {
  error.value = ''
  try {
    const fn = auth.mode === 'register' ? api.register : api.login
    const { access_token } = await fn({ email: auth.email, password: auth.password })
    setToken(access_token)
    loggedIn.value = true
    await loadProfile()
  } catch (e) { error.value = e.message }
}
function logout() { setToken(null); loggedIn.value = false; profile.value = null }

// --- профиль ---
const form = reactive({
  full_name: '', occupation: '', city: '', about: '',
  skills: [], interests: [], goals: '', contacts: '', answers: {}, resources: [],
})
function fill(data) {
  Object.keys(form).forEach(k => { if (k in data && data[k] != null) form[k] = data[k] })
}
async function loadProfile() {
  try { profile.value = await api.getProfile(); fill(profile.value) }
  catch (e) { logout(); error.value = 'Пожалуйста, войдите снова.' }
}
onMounted(() => { if (loggedIn.value) loadProfile() })
async function save() {
  error.value = ''
  try { profile.value = await api.saveProfile({ ...form }); fill(profile.value) }
  catch (e) { error.value = e.message }
}

// --- ИИ-помощник: выявляет ресурсы из рассказа ---
const story = ref('')
const suggestions = ref([])
const busy = ref(false)
async function runAssist() {
  error.value = ''; busy.value = true
  try {
    const r = await api.assist(story.value)
    for (const k of ['full_name', 'occupation', 'city']) if (r.draft[k]) form[k] = r.draft[k]
    const s = [...(r.draft.skills || []), ...(r.draft.interests || [])]
    if (r.draft.occupation) s.unshift(r.draft.occupation)
    suggestions.value = [...new Set(s)].slice(0, 8)
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}

// --- голосовой ввод ---
const SR = window.SpeechRecognition || window.webkitSpeechRecognition
const voiceSupported = !!SR
const listeningField = ref('')
function listen(key, appendText) {
  if (!SR) { error.value = 'На iPhone/iPad нажмите 🎤 на клавиатуре. В Chrome работает эта кнопка.'; return }
  const rec = new SR()
  rec.lang = 'ru-RU'; rec.interimResults = false; rec.maxAlternatives = 1
  listeningField.value = key
  rec.onresult = (e) => appendText(e.results[0][0].transcript)
  rec.onerror = () => { error.value = 'Не удалось распознать. Разрешите доступ к микрофону.' }
  rec.onend = () => { if (listeningField.value === key) listeningField.value = '' }
  try { rec.start() } catch (_) { listeningField.value = '' }
}
function appendStory(t) { story.value = story.value ? story.value + ' ' + t : t }

// --- мастер добавления ресурса/потребности ---
const WSTEPS = [
  { key: 'title', q: (t) => (t === 'give' ? 'Что вы готовы дать?' : 'Что вам нужно?'),
    hint: 'Навык, вещь, знание, время, пространство…', options: [] },
  { key: 'terms', q: () => 'На каких условиях?', options: ['Дар', 'Обмен', 'Аренда', 'Деньги', 'Консалтинг'] },
  { key: 'time', q: () => 'Сколько времени готовы уделять?', options: ['1–2 ч/нед', 'По выходным', 'По договорённости', 'Разово'] },
  { key: 'format', q: () => 'Как удобно взаимодействовать?', options: ['Онлайн', 'Лично', 'Переписка', 'Звонок'] },
  { key: 'ideal', q: (t) => (t === 'give' ? 'Кому и когда подойдёт идеально?' : 'В какой ситуации это нужно?'), options: [] },
]
const wiz = reactive({ open: false, type: 'give', step: 0, draft: {} })
function emptyDraft() { return { title: '', terms: '', time: '', format: '', ideal: '' } }
function startWizard(type, presetTitle = '') {
  wiz.type = type; wiz.step = 0; wiz.draft = emptyDraft()
  if (presetTitle) wiz.draft.title = presetTitle
  wiz.open = true
}
const curStep = computed(() => WSTEPS[wiz.step])
const curQuestion = computed(() => curStep.value.q(wiz.type))
function pick(val) { wiz.draft[curStep.value.key] = val }
const canProceed = computed(() => wiz.step !== 0 || !!wiz.draft.title.trim())
function wizNext() { if (wiz.step < WSTEPS.length - 1) wiz.step++; else finishWizard() }
function wizBack() { if (wiz.step > 0) wiz.step--; else wiz.open = false }
function finishWizard() {
  form.resources.push({ id: `${Date.now()}${Math.floor(Math.random() * 1000)}`, type: wiz.type, ...wiz.draft })
  wiz.open = false
  save()
}
function removeItem(id) { form.resources = form.resources.filter(r => r.id !== id); save() }
const gives = computed(() => form.resources.filter(r => r.type === 'give'))
const asks = computed(() => form.resources.filter(r => r.type === 'ask'))

// --- геймификация «глубины раскрытия» ---
const CIRC = 2 * Math.PI * 52
const depth = computed(() => Math.min(100, form.resources.length * 20))
const ringDash = computed(() => `${(depth.value / 100) * CIRC} ${CIRC}`)
const depthLevel = computed(() => {
  const n = form.resources.length
  if (n === 0) return 'Начало пути'
  if (n < 3) return 'Поверхность'
  if (n < 5) return 'Копаем глубже'
  return 'Глубоко'
})
const initial = computed(() => (form.full_name || profile.value?.email || '?').trim()[0].toUpperCase())
</script>

<template>
  <div class="app">
    <p v-if="error" class="err">{{ error }}</p>

    <!-- Вход -->
    <section v-if="!loggedIn" class="auth">
      <div class="brand">Ресурс</div>
      <p class="tag">синергия ресурсов и потребностей</p>
      <div class="card">
        <div class="lbl">{{ auth.mode === 'register' ? 'Регистрация' : 'Вход' }}</div>
        <input v-model="auth.email" type="email" placeholder="Email" />
        <input v-model="auth.password" type="password" placeholder="Пароль (от 6 символов)" />
        <button class="gold" @click="submitAuth">
          {{ auth.mode === 'register' ? 'Создать аккаунт' : 'Войти' }}
        </button>
        <a href="#" @click.prevent="auth.mode = auth.mode === 'login' ? 'register' : 'login'">
          {{ auth.mode === 'login' ? 'Ещё нет аккаунта — зарегистрироваться' : 'У меня уже есть аккаунт' }}
        </a>
      </div>
    </section>

    <!-- Кабинет -->
    <template v-else-if="profile">
      <header class="head">
        <div class="avatar">{{ initial }}</div>
        <div class="who">
          <div class="name">{{ form.full_name || profile.email }}</div>
          <div class="sub">глубина раскрытия · {{ depthLevel }}</div>
        </div>
        <div class="ring">
          <svg viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="52" class="rbg" />
            <circle cx="60" cy="60" r="52" class="rfg" :stroke-dasharray="ringDash" />
          </svg>
          <span>{{ depth }}%</span>
        </div>
      </header>

      <!-- ИИ-помощник -->
      <section class="card ai">
        <div class="lbl gold-t">✦ ИИ-помощник</div>
        <p class="hint">Расскажите, чем занимаетесь и что умеете — помощник поможет выявить ваши ресурсы.</p>
        <textarea v-model="story" rows="3" placeholder="Например: дизайнер, раньше преподавала английский, могу консультировать по маркетингу…"></textarea>
        <div class="row">
          <button class="gold" :disabled="busy || !story.trim()" @click="runAssist">
            {{ busy ? 'Думаю…' : 'Выявить ресурсы' }}
          </button>
          <button v-if="voiceSupported" class="ghost" :class="{ rec: listeningField === 'story' }"
            @click="listen('story', appendStory)">🎤 {{ listeningField === 'story' ? 'Слушаю…' : 'Голосом' }}</button>
        </div>
        <p v-if="!voiceSupported" class="hint sm">🎤 На iPhone/iPad диктовка — через микрофон на клавиатуре (бесплатно).</p>
        <div v-if="suggestions.length" class="sugs">
          <div class="lbl">Похоже, у вас есть ресурсы — добавим?</div>
          <button v-for="s in suggestions" :key="s" class="chip" @click="startWizard('give', s)">+ {{ s }}</button>
        </div>
      </section>

      <!-- Даю -->
      <section class="block">
        <div class="bhead"><span class="btitle">🤝 Даю</span>
          <button class="add" @click="startWizard('give')">+ Добавить</button></div>
        <p v-if="!gives.length" class="empty">Пока пусто. Добавьте, чем готовы поделиться.</p>
        <div v-for="r in gives" :key="r.id" class="rescard give">
          <button class="xbtn" @click="removeItem(r.id)">✕</button>
          <div class="rlbl">ДАЮ</div>
          <div class="rtitle">{{ r.title }}</div>
          <div class="rmeta">
            <span v-if="r.terms">🤝 {{ r.terms }}</span>
            <span v-if="r.time">⏳ {{ r.time }}</span>
            <span v-if="r.format">💬 {{ r.format }}</span>
          </div>
          <div v-if="r.ideal" class="rideal">✨ {{ r.ideal }}</div>
        </div>
      </section>

      <!-- Прошу -->
      <section class="block">
        <div class="bhead"><span class="btitle">🙏 Прошу</span>
          <button class="add" @click="startWizard('ask')">+ Добавить</button></div>
        <p v-if="!asks.length" class="empty">Пока пусто. Что вам сейчас нужно?</p>
        <div v-for="r in asks" :key="r.id" class="rescard ask">
          <button class="xbtn" @click="removeItem(r.id)">✕</button>
          <div class="rlbl ask-l">ПРОШУ</div>
          <div class="rtitle">{{ r.title }}</div>
          <div class="rmeta">
            <span v-if="r.terms">🤝 {{ r.terms }}</span>
            <span v-if="r.time">⏳ {{ r.time }}</span>
            <span v-if="r.format">💬 {{ r.format }}</span>
          </div>
          <div v-if="r.ideal" class="rideal">✨ {{ r.ideal }}</div>
        </div>
      </section>

      <!-- Обо мне -->
      <section class="card">
        <div class="lbl">Обо мне</div>
        <input v-model="form.full_name" placeholder="Имя" />
        <input v-model="form.city" placeholder="Город (или «удалённо»)" />
        <input v-model="form.contacts" placeholder="Контакты (@ник, почта)" />
        <button class="ghost" @click="save">Сохранить</button>
      </section>

      <button class="exit" @click="logout">Выйти</button>
    </template>

    <!-- Мастер (пошагово) -->
    <div v-if="wiz.open" class="overlay" @click.self="wiz.open = false">
      <div class="wizard">
        <div class="dots"><i v-for="(s, i) in WSTEPS" :key="i" :class="{ on: i <= wiz.step }" /></div>
        <div class="wlbl">{{ wiz.type === 'give' ? 'ДАЮ' : 'ПРОШУ' }} · шаг {{ wiz.step + 1 }} из {{ WSTEPS.length }}</div>
        <h3>{{ curQuestion }}</h3>
        <p v-if="curStep.hint" class="hint">{{ curStep.hint }}</p>
        <div v-if="curStep.options.length" class="opts">
          <button v-for="o in curStep.options" :key="o" class="chip"
            :class="{ sel: wiz.draft[curStep.key] === o }" @click="pick(o)">{{ o }}</button>
        </div>
        <div class="row">
          <input v-model="wiz.draft[curStep.key]" :placeholder="curStep.options.length ? 'или впишите своё' : 'ваш ответ'" />
          <button v-if="voiceSupported" class="ghost mic" :class="{ rec: listeningField === 'wiz' }"
            @click="listen('wiz', t => wiz.draft[curStep.key] = (wiz.draft[curStep.key] ? wiz.draft[curStep.key] + ' ' : '') + t)">🎤</button>
        </div>
        <div class="wnav">
          <button class="ghost" @click="wizBack">{{ wiz.step === 0 ? 'Отмена' : '← Назад' }}</button>
          <button class="gold" :disabled="!canProceed" @click="wizNext">
            {{ wiz.step === WSTEPS.length - 1 ? 'Готово' : 'Далее →' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
:root {
  --bg: #0a0a0c; --panel: #141219; --input: #0e0d12;
  --gold: #d9b45b; --gold2: #f0d38a; --line: rgba(217,180,91,.22);
  --cream: #ece3cf; --muted: #8f876f;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg);
  background-image: radial-gradient(1200px 500px at 50% -200px, rgba(217,180,91,.10), transparent 70%);
  color: var(--cream); font-family: system-ui, -apple-system, sans-serif; }
.app { max-width: 620px; margin: 0 auto; padding: 18px 16px 90px; }
h3 { font-family: Georgia, 'Times New Roman', serif; font-weight: 600; margin: 6px 0; color: var(--cream); font-size: 22px; }
.err { background: #2a1414; border: 1px solid #6b2b2b; color: #f2b8b8; padding: 10px 12px; border-radius: 10px; font-size: 14px; }

/* вход */
.auth { text-align: center; padding-top: 40px; }
.brand { font-family: Georgia, serif; font-size: 40px; letter-spacing: 1px;
  background: linear-gradient(180deg, var(--gold2), var(--gold)); -webkit-background-clip: text; background-clip: text; color: transparent; }
.tag { color: var(--muted); text-transform: lowercase; letter-spacing: 1px; margin-top: 4px; }

/* карточки */
.card, .block, .rescard, .wizard { background: var(--panel); border: 1px solid var(--line); border-radius: 18px; }
.card { padding: 18px; margin-top: 16px; box-shadow: 0 0 40px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.02); }
.card.ai { border-color: rgba(217,180,91,.4); background: linear-gradient(180deg, rgba(217,180,91,.06), var(--panel)); }
.lbl { text-transform: uppercase; letter-spacing: 2px; font-size: 11px; color: var(--muted); margin-bottom: 8px; }
.gold-t { color: var(--gold); }
.hint { color: var(--muted); font-size: 14px; margin: 6px 0; } .hint.sm { font-size: 12px; }

/* header */
.head { display: flex; align-items: center; gap: 14px; padding: 6px 2px 10px; }
.avatar { width: 54px; height: 54px; border-radius: 50%; border: 1px solid var(--line);
  display: grid; place-items: center; font-family: Georgia, serif; font-size: 22px; color: var(--gold); }
.who { flex: 1; }
.name { font-family: Georgia, serif; font-size: 19px; }
.sub { color: var(--gold); font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; }
.ring { position: relative; width: 60px; height: 60px; }
.ring svg { transform: rotate(-90deg); width: 60px; height: 60px; }
.ring .rbg { fill: none; stroke: rgba(255,255,255,.06); stroke-width: 6; }
.ring .rfg { fill: none; stroke: var(--gold); stroke-width: 6; stroke-linecap: round; transition: stroke-dasharray .5s; }
.ring span { position: absolute; inset: 0; display: grid; place-items: center; font-size: 13px; color: var(--gold); }

/* блоки Даю/Прошу */
.block { padding: 14px; margin-top: 16px; }
.bhead { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.btitle { font-family: Georgia, serif; font-size: 20px; }
.empty { color: var(--muted); font-size: 14px; }
.rescard { position: relative; padding: 14px 14px 12px; margin-top: 10px; }
.rescard.give { border-left: 3px solid var(--gold); }
.rescard.ask { border-left: 3px solid #6f9bd8; }
.rlbl { font-size: 10px; letter-spacing: 2px; color: var(--gold); } .rlbl.ask-l { color: #8fb4e8; }
.rtitle { font-size: 17px; margin: 3px 0 8px; }
.rmeta { display: flex; flex-wrap: wrap; gap: 10px; font-size: 13px; color: var(--cream); opacity: .85; }
.rideal { margin-top: 8px; font-size: 13px; color: var(--muted); }
.xbtn { position: absolute; top: 8px; right: 8px; background: none; border: none; color: var(--muted); font-size: 15px; cursor: pointer; }

/* кнопки/поля */
input, textarea { display: block; width: 100%; padding: 11px; margin-top: 8px; background: var(--input);
  border: 1px solid var(--line); border-radius: 10px; color: var(--cream); font: inherit; }
input::placeholder, textarea::placeholder { color: #5f5947; }
button { cursor: pointer; border-radius: 10px; font: inherit; padding: 10px 16px; margin-top: 10px; }
.gold { background: linear-gradient(180deg, var(--gold2), var(--gold)); color: #241d09; border: none; font-weight: 600; }
.gold:disabled { opacity: .4; }
.ghost { background: transparent; border: 1px solid var(--line); color: var(--cream); }
.ghost.rec { border-color: #e23; color: #f77; }
.add { background: transparent; border: 1px solid var(--gold); color: var(--gold); padding: 6px 12px; margin: 0; font-size: 13px; }
.exit { display: block; margin: 20px auto 0; background: none; border: none; color: var(--muted); }
.row { display: flex; gap: 8px; align-items: center; } .row input { flex: 1; } .row .mic { margin-top: 8px; }
a { color: var(--gold); display: inline-block; margin-top: 12px; font-size: 14px; }

/* чипы / подсказки */
.chip { background: var(--input); border: 1px solid var(--line); color: var(--cream); padding: 7px 12px; margin: 6px 6px 0 0; font-size: 14px; }
.chip.sel { border-color: var(--gold); color: var(--gold); }
.sugs { margin-top: 12px; }

/* мастер */
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.7); display: grid; place-items: center; padding: 16px; z-index: 10; }
.wizard { width: 100%; max-width: 460px; padding: 22px; }
.dots { display: flex; gap: 6px; margin-bottom: 12px; }
.dots i { flex: 1; height: 3px; border-radius: 3px; background: rgba(255,255,255,.1); }
.dots i.on { background: var(--gold); }
.wlbl { font-size: 11px; letter-spacing: 2px; color: var(--muted); }
.opts { margin: 6px 0; }
.wnav { display: flex; justify-content: space-between; margin-top: 14px; }
</style>
