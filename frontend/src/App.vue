<script setup>
import { ref, computed } from 'vue'
import { store, actions, reminders, activeClient, clientMessages } from './store.js'

import TrainerDashboard from './components/TrainerDashboard.vue'
import TrainerClients from './components/TrainerClients.vue'
import TrainerFeedback from './components/TrainerFeedback.vue'
import ClientHome from './components/ClientHome.vue'
import ClientPlan from './components/ClientPlan.vue'
import CalendarView from './components/CalendarView.vue'
import ChatView from './components/ChatView.vue'

const showNotif = ref(false)

const reminderList = computed(() => reminders())

// заголовок/подпись в шапке
const header = computed(() => {
  if (store.role === 'trainer') {
    return { avatar: store.trainer.avatar, name: store.trainer.name, sub: store.trainer.title }
  }
  const c = activeClient()
  return { avatar: c.avatar, name: c.name, sub: c.goal + ' · ' + c.level }
})

// вкладки для роли
const trainerTabs = [
  { id: 'dashboard', ic: '🏠', label: 'Обзор' },
  { id: 'clients', ic: '👥', label: 'Клиенты' },
  { id: 'calendar', ic: '📅', label: 'Календарь' },
  { id: 'feedback', ic: '⭐', label: 'Отзывы' },
  { id: 'chat', ic: '💬', label: 'Чат' },
]
const clientTabs = [
  { id: 'home', ic: '🏠', label: 'Главная' },
  { id: 'plan', ic: '🏋️', label: 'План' },
  { id: 'calendar', ic: '📅', label: 'Календарь' },
  { id: 'chat', ic: '💬', label: 'Чат' },
]
const tabs = computed(() => (store.role === 'trainer' ? trainerTabs : clientTabs))

// точки-индикаторы на вкладках
function tabHasDot(id) {
  if (store.role === 'trainer') {
    if (id === 'feedback') return reminderList.value.some(r => r.kind === 'feedback')
    if (id === 'chat') return store.clients.some(c => clientMessages(c.id).some(m => m.from === 'client' && !m.read))
  } else {
    if (id === 'chat') return clientMessages(store.activeClientId).some(m => m.from === 'trainer' && !m.read)
  }
  return false
}

function onReminderClick(r) {
  showNotif.value = false
  if (r.kind === 'feedback') { if (r.clientId) actions.setActiveClient(r.clientId); actions.setTab('feedback') }
  else if (r.kind === 'chat') { if (r.clientId) actions.setActiveClient(r.clientId); actions.setTab('chat') }
  else if (r.kind === 'reminder') { if (r.clientId) actions.setActiveClient(r.clientId); actions.setTab(store.role === 'trainer' ? 'calendar' : 'plan') }
}

const currentComponent = computed(() => {
  const map = {
    dashboard: TrainerDashboard,
    clients: TrainerClients,
    feedback: TrainerFeedback,
    home: ClientHome,
    plan: ClientPlan,
    calendar: CalendarView,
    chat: ChatView,
  }
  return map[store.tab] || (store.role === 'trainer' ? TrainerDashboard : ClientHome)
})
</script>

<template>
  <div class="app-frame">
    <div class="phone">
      <!-- шапка -->
      <div class="topbar" :class="{ client: store.role === 'client' }">
        <div class="avatar">{{ header.avatar }}</div>
        <div class="who">
          <div class="name">{{ header.name }}</div>
          <div class="sub">{{ header.sub }}</div>
        </div>
        <button class="bell" @click="showNotif = true">
          🔔
          <span v-if="reminderList.length" class="dot">{{ reminderList.length }}</span>
        </button>
      </div>

      <!-- переключатель роли (демо) -->
      <div class="role-switch">
        <button :class="{ active: store.role === 'trainer' }" @click="actions.setRole('trainer')">🏋️‍♀️ Тренер</button>
        <button :class="{ active: store.role === 'client' }" @click="actions.setRole('client')">🙋 Клиент</button>
      </div>

      <!-- строка выбора клиента -->
      <div class="context-row">
        <span class="tiny" style="flex-shrink:0;">{{ store.role === 'trainer' ? 'Смотрю:' : 'Я вошёл как:' }}</span>
        <span
          v-for="c in store.clients"
          :key="c.id"
          class="chip"
          :class="{ active: c.id === store.activeClientId }"
          @click="actions.setActiveClient(c.id)"
        >{{ c.avatar }} {{ c.name.split(' ')[0] }}</span>
      </div>

      <!-- контент -->
      <div class="content">
        <component :is="currentComponent" />
      </div>

      <!-- нижняя навигация -->
      <div class="tabbar" :class="{ client: store.role === 'client' }">
        <button
          v-for="t in tabs"
          :key="t.id"
          :class="{ active: store.tab === t.id }"
          @click="actions.setTab(t.id)"
        >
          <span class="ic">{{ t.ic }}</span>
          <span>{{ t.label }}</span>
          <span v-if="tabHasDot(t.id)" class="tab-dot"></span>
        </button>
      </div>

      <!-- панель уведомлений -->
      <template v-if="showNotif">
        <div class="overlay" @click="showNotif = false"></div>
        <div class="notif-panel">
          <div class="notif-head">
            <b>Уведомления</b>
            <button class="n-x" @click="showNotif = false">✕</button>
          </div>
          <div class="notif-body">
            <div v-if="!reminderList.length" class="empty"><div class="em">🔕</div><div class="et">Новых уведомлений нет</div></div>
            <div v-for="r in reminderList" :key="r.id" class="notif">
              <div class="n-ic">{{ r.icon }}</div>
              <div class="n-body" @click="onReminderClick(r)" style="cursor:pointer;">
                <div class="n-title">{{ r.title }}</div>
                <div class="n-sub">{{ r.body }}</div>
              </div>
              <button class="n-x" @click="actions.dismissReminder(r.id)">✕</button>
            </div>
            <button class="btn ghost sm mt" style="width:100%;" @click="actions.resetDemo(); showNotif = false">↺ Сбросить демо-данные</button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
