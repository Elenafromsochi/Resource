<script setup>
import { ref, computed } from 'vue'
import { store, clientPlan, activeClient, groupColor, dayISO } from '../store.js'
import { MONTHS, human, relativeDay } from '../format.js'
import ExerciseList from './ExerciseList.vue'

// Тренер видит календарь по всем клиентам, клиент — только свой.
const cursor = ref(new Date())
cursor.value.setDate(1)

const monthLabel = computed(() => `${MONTHS[cursor.value.getMonth()]} ${cursor.value.getFullYear()}`)

function shift(n) {
  const d = new Date(cursor.value)
  d.setMonth(d.getMonth() + n)
  cursor.value = d
}

// собираем все сессии в зоне видимости
const sessions = computed(() => {
  if (store.role === 'client') {
    return clientPlan(store.activeClientId).map(s => ({ ...s, clientId: store.activeClientId }))
  }
  const all = []
  for (const c of store.clients) {
    for (const s of clientPlan(c.id)) all.push({ ...s, clientId: c.id, clientName: c.name })
  }
  return all
})

const todayIso = dayISO(0)
const selected = ref(todayIso)

// матрица дней месяца (недели с понедельника)
const cells = computed(() => {
  const y = cursor.value.getFullYear()
  const m = cursor.value.getMonth()
  const first = new Date(y, m, 1)
  let startDow = first.getDay() // 0=вс
  startDow = (startDow + 6) % 7 // делаем пн=0
  const daysInMonth = new Date(y, m + 1, 0).getDate()
  const arr = []
  for (let i = 0; i < startDow; i++) arr.push(null)
  for (let d = 1; d <= daysInMonth; d++) {
    const iso = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    arr.push(iso)
  }
  return arr
})

function daySessions(iso) {
  return sessions.value.filter(s => s.date === iso)
}
const dowLabels = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']

const selectedSessions = computed(() =>
  daySessions(selected.value).sort((a, b) => a.time.localeCompare(b.time))
)

function clientNameOf(cid) {
  return (store.clients.find(c => c.id === cid) || {}).name || ''
}
</script>

<template>
  <div>
    <div class="card">
      <div class="cal-head">
        <span class="mon">{{ monthLabel }}</span>
        <div class="cal-nav">
          <button @click="shift(-1)">‹</button>
          <button @click="shift(1)">›</button>
        </div>
      </div>
      <div class="cal-grid" style="margin-bottom:6px;">
        <div v-for="d in dowLabels" :key="d" class="cal-dow">{{ d }}</div>
      </div>
      <div class="cal-grid">
        <template v-for="(iso, i) in cells" :key="i">
          <div v-if="!iso" class="cal-cell empty"></div>
          <div
            v-else
            class="cal-cell"
            :class="{ today: iso === todayIso, selected: iso === selected }"
            @click="selected = iso"
          >
            {{ Number(iso.slice(8)) }}
            <div class="cal-dots">
              <i
                v-for="(s, j) in daySessions(iso).slice(0,3)"
                :key="j"
                :style="{ background: s.status === 'done' ? '#16a34a' : s.status === 'skipped' ? '#ef4444' : groupColor(s.group) }"
              ></i>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div class="section-title">{{ relativeDay(selected) }} · {{ human(selected) }}</div>

    <div v-if="!selectedSessions.length" class="empty">
      <div class="em">🗓️</div>
      <div class="et">На этот день тренировок нет</div>
    </div>

    <div v-for="s in selectedSessions" :key="s.id" class="card">
      <div class="flex-between" style="margin-bottom:8px;">
        <div>
          <span class="pill-group" :style="{ background: groupColor(s.group) }">{{ s.group }}</span>
          <span style="margin-left:8px; font-weight:700;">{{ s.time }}</span>
        </div>
        <span class="badge" :class="s.status">
          {{ s.status === 'done' ? 'Выполнено' : s.status === 'skipped' ? 'Пропущено' : 'Запланировано' }}
        </span>
      </div>
      <div v-if="store.role === 'trainer'" class="tiny" style="margin-bottom:8px;">👤 {{ s.clientName || clientNameOf(s.clientId) }}</div>
      <ExerciseList :exercises="s.exercises" />
    </div>
  </div>
</template>
