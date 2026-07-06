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

// --- личный кабинет ---
const form = reactive({
  full_name: '', occupation: '', city: '', about: '',
  skills: [], interests: [], goals: '', contacts: '', answers: {},
})
function fill(data) { Object.keys(form).forEach(k => { if (k in data) form[k] = data[k] }) }

async function loadProfile() {
  try {
    profile.value = await api.getProfile()
    fill(profile.value)
  } catch (e) {
    // Протухший/битый вход → показываем окно входа, а не пустой экран.
    logout()
    error.value = 'Пожалуйста, войдите снова.'
  }
}
onMounted(() => { if (loggedIn.value) loadProfile() })

async function save() {
  error.value = ''
  try { profile.value = await api.saveProfile({ ...form }); fill(profile.value) }
  catch (e) { error.value = e.message }
}

// --- ИИ-помощник ---
const story = ref('')
const questions = ref([])
const provider = ref('')
const busy = ref(false)
async function runAssist() {
  error.value = ''; busy.value = true
  try {
    const r = await api.assist(story.value)
    fill(r.draft)          // черновик подставляется в форму — его можно поправить
    questions.value = r.questions
    provider.value = r.provider
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}

// поля списком (skills/interests) редактируем через строку с запятыми
const skillsText = computed({
  get: () => form.skills.join(', '),
  set: (v) => { form.skills = v.split(',').map(s => s.trim()).filter(Boolean) },
})
const interestsText = computed({
  get: () => form.interests.join(', '),
  set: (v) => { form.interests = v.split(',').map(s => s.trim()).filter(Boolean) },
})
const completeness = computed(() => Math.round((profile.value?.completeness || 0) * 100))

// --- голосовой ввод (Web Speech API, встроен в браузер) ---
const SR = window.SpeechRecognition || window.webkitSpeechRecognition
const voiceSupported = !!SR
const listeningField = ref('')  // какое поле сейчас записывается

function listen(key, appendText) {
  if (!SR) {
    error.value = 'Голосовой ввод не поддерживается в этом браузере (лучше всего — Chrome).'
    return
  }
  const rec = new SR()
  rec.lang = 'ru-RU'
  rec.interimResults = false
  rec.maxAlternatives = 1
  listeningField.value = key
  rec.onresult = (e) => appendText(e.results[0][0].transcript)
  rec.onerror = () => { error.value = 'Не удалось распознать речь. Разрешите доступ к микрофону и попробуйте ещё раз.' }
  rec.onend = () => { if (listeningField.value === key) listeningField.value = '' }
  try { rec.start() } catch (_) { listeningField.value = '' }
}

function appendStory(t) { story.value = story.value ? story.value + ' ' + t : t }
function appendAnswer(id, t) { form.answers[id] = form.answers[id] ? form.answers[id] + ' ' + t : t }

// --- вопросы про ресурсы ---
const resourceQuestions = ref([])
onMounted(async () => {
  try {
    resourceQuestions.value = (await api.getQuestions()).questions
    // гарантируем, что у каждого вопроса есть поле для ответа
    for (const q of resourceQuestions.value) {
      if (!(q.id in form.answers)) form.answers[q.id] = ''
    }
  } catch (_) { /* вопросы не критичны для входа */ }
})
</script>

<template>
  <div class="wrap">
    <header><h1>Ресурс</h1><button v-if="loggedIn" class="ghost" @click="logout">Выйти</button></header>
    <p v-if="error" class="err">{{ error }}</p>

    <!-- Регистрация / вход -->
    <section v-if="!loggedIn" class="card">
      <h2>{{ auth.mode === 'register' ? 'Регистрация' : 'Вход' }}</h2>
      <input v-model="auth.email" type="email" placeholder="Email" />
      <input v-model="auth.password" type="password" placeholder="Пароль (от 6 символов)" />
      <button class="primary" @click="submitAuth">
        {{ auth.mode === 'register' ? 'Зарегистрироваться' : 'Войти' }}
      </button>
      <a href="#" @click.prevent="auth.mode = auth.mode === 'login' ? 'register' : 'login'">
        {{ auth.mode === 'login' ? 'Создать аккаунт' : 'У меня уже есть аккаунт' }}
      </a>
    </section>

    <!-- Личный кабинет -->
    <template v-else-if="profile">
      <p class="me">{{ profile.email }} · заполнено {{ completeness }}%</p>
      <div class="bar"><span :style="{ width: completeness + '%' }"></span></div>

      <!-- ИИ-помощник -->
      <section class="card ai">
        <h2>✨ Заполнить с помощью ИИ</h2>
        <p class="hint">Расскажите о себе в свободной форме — помощник разложит по полям.</p>
        <textarea v-model="story" rows="4"
          placeholder="Например: Меня зовут Анна, живу в Сочи, работаю дизайнером. Умею вёрстка, фотография. Увлекаюсь спортом. Ищу новые проекты."></textarea>
        <div class="row">
          <button class="primary" :disabled="busy || !story.trim()" @click="runAssist">
            {{ busy ? 'Думаю…' : 'Разобрать рассказ' }}
          </button>
          <button v-if="voiceSupported" class="mic" :class="{ rec: listeningField === 'story' }"
            @click="listen('story', appendStory)">
            🎤 {{ listeningField === 'story' ? 'Слушаю…' : 'Голосом' }}
          </button>
        </div>
        <p v-if="!voiceSupported" class="hint">🎤 Чтобы надиктовать голосом: нажмите на поле ввода, затем на значок микрофона на клавиатуре (встроенная диктовка iPhone/iPad — бесплатно).</p>
        <span v-if="provider" class="prov">провайдер: {{ provider === 'claude' ? 'Claude' : 'офлайн' }}</span>
        <div v-if="questions.length" class="q">
          <p>Чтобы профиль был полнее, уточните:</p>
          <ul>
            <li v-for="q in questions" :key="q.field">
              {{ q.question }}
              <em v-if="q.examples.length">(например: {{ q.examples.join(', ') }})</em>
            </li>
          </ul>
        </div>
      </section>

      <!-- Вопросы про ресурсы -->
      <section v-if="resourceQuestions.length" class="card">
        <h2>Вопросы про ресурсы</h2>
        <p class="hint">Ответьте на вопросы — текстом или голосом. Ответы сохранятся в профиле.</p>
        <div v-for="q in resourceQuestions" :key="q.id" class="qitem">
          <label>{{ q.text }}</label>
          <textarea v-model="form.answers[q.id]" rows="2" :placeholder="(q.examples || []).join(', ')"></textarea>
          <button v-if="voiceSupported" class="mic" :class="{ rec: listeningField === q.id }"
            @click="listen(q.id, t => appendAnswer(q.id, t))">
            🎤 {{ listeningField === q.id ? 'Слушаю…' : 'Ответить голосом' }}
          </button>
        </div>
        <button class="primary" @click="save">Сохранить ответы</button>
      </section>

      <!-- Поля профиля (редактируемые) -->
      <section class="card">
        <h2>Профиль</h2>
        <label>Имя</label><input v-model="form.full_name" />
        <label>Род занятий</label><input v-model="form.occupation" />
        <label>Город</label><input v-model="form.city" />
        <label>Навыки (через запятую)</label><input v-model="skillsText" />
        <label>Интересы (через запятую)</label><input v-model="interestsText" />
        <label>Что вы ищете</label><input v-model="form.goals" />
        <label>О себе</label><textarea v-model="form.about" rows="3"></textarea>
        <label>Контакты</label><input v-model="form.contacts" />
        <button class="primary" @click="save">Сохранить</button>
      </section>
    </template>
  </div>
</template>

<style>
body { margin: 0; background: #f6f7fb; }
.wrap { max-width: 640px; margin: 0 auto; padding: 16px; font-family: system-ui, sans-serif; color: #222; }
header { display: flex; align-items: center; justify-content: space-between; }
.card { background: #fff; border: 1px solid #e6e6ef; border-radius: 14px; padding: 18px; margin-top: 14px; }
.card.ai { border-color: #cdd9ff; background: #f7f9ff; }
h1 { margin: 0; } h2 { margin-top: 0; }
label { display: block; font-size: 12px; color: #777; margin-top: 10px; }
input, textarea { display: block; width: 100%; padding: 9px; margin-top: 4px; box-sizing: border-box;
  border: 1px solid #ccc; border-radius: 8px; font: inherit; }
button { padding: 9px 14px; margin-top: 12px; cursor: pointer; border: 1px solid #ccc;
  border-radius: 8px; background: #fff; }
button.primary { background: #2f6bff; color: #fff; border-color: #2f6bff; }
button.primary:disabled { opacity: .5; cursor: default; }
button.ghost { margin: 0; background: transparent; border: none; color: #888; }
a { display: inline-block; margin-top: 12px; margin-left: 12px; color: #2f6bff; }
.err { color: #c33; }
.me { color: #666; font-size: 14px; margin-bottom: 4px; }
.bar { height: 8px; background: #e6e6ef; border-radius: 6px; overflow: hidden; }
.bar span { display: block; height: 100%; background: #2f6bff; transition: width .3s; }
.hint { color: #777; font-size: 14px; }
.prov { font-size: 12px; color: #999; margin-left: 10px; }
.q { font-size: 14px; } .q em { color: #888; }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.mic { background: #fff; border: 1px solid #2f6bff; color: #2f6bff; }
.mic.rec { background: #ffe8e8; border-color: #e23; color: #c22; }
.qitem { margin-top: 12px; }
.qitem label { font-size: 14px; color: #333; }
</style>
