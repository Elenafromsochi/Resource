<script setup>
import { computed } from 'vue'
import { store, actions, clientPlan, clientMessages, groupColor } from '../store.js'
import { dayISO } from '../store.js'
import { relativeDay, human } from '../format.js'

const today = dayISO(0)

const stats = computed(() => {
  let planned = 0, done = 0, feedback = 0, unread = 0
  for (const c of store.clients) {
    for (const s of clientPlan(c.id)) {
      if (s.status === 'planned') planned++
      if (s.status === 'done') done++
      if (s.status === 'done' && s.feedback && !s.seenByTrainer) feedback++
    }
    unread += clientMessages(c.id).filter(m => m.from === 'client' && !m.read).length
  }
  return { clients: store.clients.length, planned, done, feedback, unread }
})

// ближайшие тренировки (все клиенты), сегодня и дальше
const upcoming = computed(() => {
  const arr = []
  for (const c of store.clients) {
    for (const s of clientPlan(c.id)) {
      if (s.status === 'planned' && s.date >= today) arr.push({ ...s, client: c })
    }
  }
  return arr.sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time)).slice(0, 5)
})

// последние отзывы
const latestFeedback = computed(() => {
  const arr = []
  for (const c of store.clients) {
    for (const s of clientPlan(c.id)) {
      if (s.status === 'done' && s.feedback) arr.push({ ...s, client: c })
    }
  }
  return arr.sort((a, b) => (b.feedback.at || '').localeCompare(a.feedback.at || '')).slice(0, 3)
})

function openClient(c, tab) {
  actions.setActiveClient(c.id)
  actions.setTab(tab)
}
</script>

<template>
  <div>
    <div class="stat-row">
      <div class="stat"><div class="num">{{ stats.clients }}</div><div class="lbl">Клиентов</div></div>
      <div class="stat"><div class="num">{{ stats.planned }}</div><div class="lbl">Запланировано</div></div>
      <div class="stat"><div class="num" style="color:var(--accent)">{{ stats.done }}</div><div class="lbl">Выполнено</div></div>
    </div>

    <div v-if="stats.feedback || stats.unread" class="card pad-sm" style="border-color: var(--accent); background: var(--accent-soft);">
      <div style="font-weight:700; font-size:13.5px; color:#166534;">
        🔔 {{ stats.feedback }} новых отзыв(ов), {{ stats.unread }} непрочит. сообщений
      </div>
    </div>

    <div class="section-title">Ближайшие тренировки</div>
    <div v-if="!upcoming.length" class="empty"><div class="em">📅</div><div class="et">Нет запланированных тренировок</div></div>
    <div
      v-for="s in upcoming"
      :key="s.id"
      class="session"
      @click="openClient(s.client, 'clients')"
      style="cursor:pointer;"
    >
      <div class="daybox">
        <div class="d">{{ Number(s.date.slice(8)) }}</div>
        <div class="m">{{ human(s.date).split(' ')[1] }}</div>
      </div>
      <div class="body">
        <div class="title">{{ s.client.avatar }} {{ s.client.name }}</div>
        <div class="meta">
          <span class="pill-group" :style="{ background: groupColor(s.group) }">{{ s.group }}</span>
          · {{ relativeDay(s.date) }}, {{ s.time }}
        </div>
      </div>
    </div>

    <div class="section-title mt">Последние отзывы</div>
    <div v-if="!latestFeedback.length" class="empty"><div class="em">⭐</div><div class="et">Отзывов пока нет</div></div>
    <div
      v-for="s in latestFeedback"
      :key="s.id"
      class="card pad-sm"
      @click="openClient(s.client, 'feedback')"
      style="cursor:pointer;"
    >
      <div class="flex-between">
        <div style="font-weight:700; font-size:13.5px;">{{ s.client.avatar }} {{ s.client.name }}</div>
        <div class="stars">{{ '★'.repeat(s.feedback.rating) }}<span style="color:#e2e8f0">{{ '★'.repeat(5 - s.feedback.rating) }}</span></div>
      </div>
      <div class="tiny" style="margin-top:2px;">{{ s.title }}</div>
      <div v-if="s.feedback.note" class="fb-note">«{{ s.feedback.note }}»</div>
    </div>
  </div>
</template>
