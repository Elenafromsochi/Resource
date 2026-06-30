<script setup>
import { reactive, ref, onMounted, computed } from 'vue'
import { api, setToken } from './api.js'

// Адаптер авторизации передаётся точкой входа (сайт или мини-апп).
// Механизм приложения один и тот же — отличается только вход.
const props = defineProps({ auth: { type: Object, required: true } })

const profile = ref(null)
const error = ref('')
const tab = ref('create')

// --- форма входа (только для сайта) ---
const loginForm = reactive({ username: '', password: '', display_name: '', mode: 'login' })

async function doAuth() {
  error.value = ''
  try {
    const token = loginForm.mode === 'register'
      ? (await api.register({ username: loginForm.username, password: loginForm.password, display_name: loginForm.display_name })).access_token
      : (await api.login({ username: loginForm.username, password: loginForm.password })).access_token
    setToken(token)
    profile.value = await api.me()
  } catch (e) { error.value = e.message }
}

onMounted(async () => {
  try {
    const p = await props.auth.autoLogin()  // мини-апп логинится автоматически
    if (p) profile.value = p
  } catch (e) { error.value = e.message }
})

// --- справочник категорий ---
const categories = ref({})
onMounted(async () => { categories.value = await api.categories() })

// --- форма Даю/Прошу ---
const form = reactive({ side: 'give', category: 'time_skill', title: '', location: '', fields: {}, ideal_for: '' })
const clarify = ref([])
const currentFields = computed(() => categories.value[form.category]?.fields || [])

function setField(key, value) { form.fields[key] = value }

async function askAi() {
  const r = await api.clarify({ category: form.category, side: form.side, fields: form.fields })
  clarify.value = r.questions
}

async function submitListing() {
  error.value = ''
  try {
    const body = { category: form.category, title: form.title, location: form.location, fields: { ...form.fields } }
    if (form.side === 'give') { body.ideal_for = form.ideal_for; await api.createResource(body) }
    else await api.createNeed(body)
    form.title = ''; form.fields = {}; form.ideal_for = ''; clarify.value = []
    await loadFeed()
    tab.value = 'feed'
  } catch (e) { error.value = e.message }
}

// --- лента и подбор ---
const resources = ref([])
const needs = ref([])
async function loadFeed() {
  resources.value = await api.listResources()
  needs.value = await api.listNeeds()
}
onMounted(loadFeed)

const matches = ref([])
const matchSource = ref(null)
async function findForNeed(need) {
  matchSource.value = need
  matches.value = await api.matchesForNeed(need.id)
}
function resourceById(id) { return resources.value.find(r => r.id === id) }

// --- сделка ---
const deal = ref(null)
const draft = ref('')
async function openDeal(resource) {
  deal.value = await api.createDeal({ resource_id: resource.id, counterparty_id: profile.value.id })
  tab.value = 'deal'
}
async function send() {
  if (!draft.value.trim()) return
  deal.value = await api.sendMessage(deal.value.id, draft.value)
  draft.value = ''
}
async function signDeal() { deal.value = await api.sign(deal.value.id) }
const completion = ref(null)
async function completeDeal() { completion.value = await api.complete(deal.value.id); deal.value = completion.value.deal }
const reviewForm = reactive({ situation: '', task: '', action: '', result: '', rating: 5 })
async function submitReview() {
  const r = await api.review(completion.value.act_id, { ...reviewForm })
  error.value = `Отзыв сохранён. Капитал доверия партнёра: ${r.subject_trust_capital}`
}
</script>

<template>
  <div class="wrap">
    <h1>Ресурс <span class="badge">{{ auth.kind === 'miniapp' ? 'Mini App' : 'сайт' }}</span></h1>
    <p v-if="error" class="err">{{ error }}</p>

    <!-- Вход (сайт). Мини-апп логинится сам. -->
    <section v-if="!profile" class="card">
      <h2>Вход</h2>
      <template v-if="auth.kind === 'web'">
        <input v-model="loginForm.username" placeholder="Логин" />
        <input v-model="loginForm.password" type="password" placeholder="Пароль" />
        <input v-if="loginForm.mode === 'register'" v-model="loginForm.display_name" placeholder="Имя" />
        <button @click="doAuth">{{ loginForm.mode === 'register' ? 'Зарегистрироваться' : 'Войти' }}</button>
        <a href="#" @click.prevent="loginForm.mode = loginForm.mode === 'login' ? 'register' : 'login'">
          {{ loginForm.mode === 'login' ? 'Создать аккаунт' : 'У меня есть аккаунт' }}
        </a>
      </template>
      <p v-else>Авторизация через Telegram…</p>
    </section>

    <template v-else>
      <p class="me">{{ profile.display_name }} · уровень {{ profile.level }} · доверие {{ profile.trust_capital }}
        · даю {{ profile.give_count }} / прошу {{ profile.ask_count }}</p>

      <nav class="tabs">
        <button :class="{ on: tab==='create' }" @click="tab='create'">Создать</button>
        <button :class="{ on: tab==='feed' }" @click="tab='feed'; loadFeed()">Лента и подбор</button>
        <button :class="{ on: tab==='deal' }" @click="tab='deal'" :disabled="!deal">Сделка</button>
      </nav>

      <!-- 1. Форма Даю/Прошу с ИИ-вопросами -->
      <section v-if="tab==='create'" class="card">
        <div class="seg">
          <button :class="{ on: form.side==='give' }" @click="form.side='give'">Даю (ресурс)</button>
          <button :class="{ on: form.side==='ask' }" @click="form.side='ask'">Прошу (потребность)</button>
        </div>
        <select v-model="form.category">
          <option v-for="(c, key) in categories" :key="key" :value="key">{{ c.label }}</option>
        </select>
        <input v-model="form.title" placeholder="Коротко: что именно" />
        <input v-model="form.location" placeholder="Локация (или «удалённо»)" />
        <div v-for="f in currentFields" :key="f.key" class="field">
          <label>{{ f.label }}</label>
          <input :value="form.fields[f.key] || ''" @input="setField(f.key, $event.target.value)"
                 :placeholder="f.match === 'terms' ? 'gift,barter,money' : ''" />
        </div>
        <input v-if="form.side==='give'" v-model="form.ideal_for" placeholder="Кому идеально подойдёт" />
        <div class="row">
          <button @click="askAi">Спросить ИИ</button>
          <button class="primary" @click="submitListing">Опубликовать</button>
        </div>
        <div v-if="clarify.length" class="ai">
          <p>ИИ уточняет:</p>
          <div v-for="q in clarify" :key="q.field" class="qa">
            <span>{{ q.question }}</span>
            <button v-for="opt in q.options" :key="opt" class="chip" @click="setField(q.field, opt)">{{ opt }}</button>
          </div>
        </div>
      </section>

      <!-- 2. Лента + зеркальный мэтчинг -->
      <section v-if="tab==='feed'" class="card">
        <h3>Мои потребности → подбор ресурсов</h3>
        <ul>
          <li v-for="n in needs.filter(n => n.owner_id === profile.id)" :key="n.id">
            {{ n.title }} <button @click="findForNeed(n)">Найти ресурсы</button>
          </li>
        </ul>
        <div v-if="matchSource">
          <h4>Совпадения для «{{ matchSource.title }}» (порог 40%)</h4>
          <ul>
            <li v-for="m in matches" :key="m.resource_id">
              <b :class="{ hit: m.is_match }">{{ m.score }}%</b>
              {{ resourceById(m.resource_id)?.title || m.resource_id }}
              <button v-if="resourceById(m.resource_id)" @click="openDeal(resourceById(m.resource_id))">Открыть сделку</button>
            </li>
          </ul>
        </div>
        <h3>Все ресурсы</h3>
        <ul>
          <li v-for="r in resources" :key="r.id">{{ r.title }} ({{ categories[r.category]?.label }})
            <button @click="openDeal(r)">Сделка</button></li>
        </ul>
      </section>

      <!-- 3. Чат сделки + Человеческий договор -->
      <section v-if="tab==='deal' && deal" class="card deal">
        <div class="chat">
          <h3>Чат сделки</h3>
          <div class="msgs">
            <p v-for="m in deal.messages" :key="m.id" :class="m.role">
              <b>{{ m.role === 'user' ? 'Вы' : m.role.replace('bot_', 'бот: ') }}:</b> {{ m.text }}
            </p>
          </div>
          <div class="row">
            <input v-model="draft" placeholder="Суть: ..." @keyup.enter="send" />
            <button @click="send">→</button>
          </div>
        </div>
        <div class="contract">
          <h3>Человеческий договор</h3>
          <p class="prog">Заполнено: {{ Math.round(deal.contract_completeness * 100) }}%
            <span v-if="deal.signed_by_all">· подписан ✔</span></p>
          <ul>
            <li v-for="(v, k) in deal.contract.fields" :key="k"><b>{{ k }}:</b> {{ v || '—' }}</li>
          </ul>
          <button @click="signDeal" :disabled="deal.contract_completeness < 1">Подписать</button>
          <button class="primary" @click="completeDeal" :disabled="deal.status !== 'signed'">Завершить</button>

          <div v-if="completion" class="review">
            <h4>Отзыв по STAR</h4>
            <input v-model="reviewForm.situation" placeholder="Ситуация" />
            <input v-model="reviewForm.task" placeholder="Задача" />
            <input v-model="reviewForm.action" placeholder="Действие" />
            <input v-model="reviewForm.result" placeholder="Результат" />
            <input v-model.number="reviewForm.rating" type="number" min="1" max="5" />
            <button @click="submitReview">Отправить отзыв</button>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style>
.wrap { max-width: 760px; margin: 0 auto; padding: 16px; font-family: system-ui, sans-serif; }
h1 { display: flex; align-items: center; gap: 8px; }
.badge { font-size: 12px; background: #eef; padding: 2px 8px; border-radius: 10px; }
.card { border: 1px solid #ddd; border-radius: 12px; padding: 16px; margin-top: 12px; }
input, select { display: block; width: 100%; padding: 8px; margin: 6px 0; box-sizing: border-box; }
button { padding: 8px 12px; margin: 4px 4px 4px 0; cursor: pointer; border: 1px solid #ccc; border-radius: 8px; background: #fff; }
button.on, button.primary { background: #2b6; color: #fff; border-color: #2b6; }
button.primary { background: #16c; border-color: #16c; }
.tabs button, .seg button { margin-right: 6px; }
.chip { font-size: 12px; background: #f3f3f7; }
.row { display: flex; gap: 8px; }
.row input { flex: 1; }
.err { color: #c33; }
.me { color: #555; font-size: 14px; }
.field label { font-size: 12px; color: #666; }
.qa { margin: 8px 0; }
.deal { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.msgs { max-height: 320px; overflow: auto; font-size: 14px; }
.msgs .bot_resurs { color: #16c; } .msgs .bot_mediator { color: #b60; }
.prog b, .hit { color: #2b6; } b.hit { font-weight: 700; }
@media (max-width: 640px) { .deal { grid-template-columns: 1fr; } }
</style>
