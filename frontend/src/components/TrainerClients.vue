<script setup>
import { ref, computed } from 'vue'
import { store, actions, clientPlan, activeClient, groupColor, dayISO } from '../store.js'
import { relativeDay, human } from '../format.js'
import ExerciseList from './ExerciseList.vue'

const client = computed(() => activeClient())
const plan = computed(() => clientPlan(store.activeClientId))

const upcoming = computed(() => plan.value.filter(s => s.status === 'planned'))
const past = computed(() => plan.value.filter(s => s.status !== 'planned').reverse())

// форма добавления тренировки
const showForm = ref(false)
const form = ref({ group: 'Ноги', date: dayISO(1), time: '10:00' })
const groups = store.library.map(g => g.group)

function addSession() {
  actions.addSession(store.activeClientId, { ...form.value })
  showForm.value = false
  form.value = { group: 'Ноги', date: dayISO(1), time: '10:00' }
}

const expanded = ref(null)
function toggleExpand(id) { expanded.value = expanded.value === id ? null : id }

function stats(cid) {
  const p = clientPlan(cid)
  return {
    done: p.filter(s => s.status === 'done').length,
    planned: p.filter(s => s.status === 'planned').length,
  }
}
</script>

<template>
  <div>
    <!-- выбор клиента -->
    <div class="section-title">Клиенты</div>
    <div
      v-for="c in store.clients"
      :key="c.id"
      class="card pad-sm"
      :style="{ borderColor: c.id === store.activeClientId ? 'var(--accent)' : 'var(--border)', cursor: 'pointer' }"
      @click="actions.setActiveClient(c.id)"
    >
      <div class="flex-between">
        <div style="display:flex; align-items:center; gap:10px;">
          <div style="font-size:26px;">{{ c.avatar }}</div>
          <div>
            <div style="font-weight:700; font-size:14px;">{{ c.name }}</div>
            <div class="tiny">{{ c.goal }} · {{ c.level }}</div>
          </div>
        </div>
        <div style="text-align:right;">
          <div class="tiny">✅ {{ stats(c.id).done }} · 📅 {{ stats(c.id).planned }}</div>
        </div>
      </div>
    </div>

    <!-- план выбранного клиента -->
    <div class="flex-between mt" style="margin-bottom:10px;">
      <div class="section-title mb0">План: {{ client.name }}</div>
      <button class="btn accent sm" @click="showForm = !showForm">＋ Тренировка</button>
    </div>

    <div v-if="showForm" class="card">
      <div class="field">
        <label>Тип тренировки</label>
        <select v-model="form.group">
          <option v-for="g in groups" :key="g" :value="g">{{ g }}</option>
        </select>
      </div>
      <div class="row2">
        <div class="field"><label>Дата</label><input type="date" v-model="form.date" /></div>
        <div class="field"><label>Время</label><input type="time" v-model="form.time" /></div>
      </div>
      <div class="tiny" style="margin-bottom:10px;">
        Упражнения подставятся из шаблона «{{ form.group }}» (данные из плана клиента).
      </div>
      <button class="btn accent" @click="addSession">Добавить в план</button>
    </div>

    <div class="section-title mt">Запланировано</div>
    <div v-if="!upcoming.length" class="empty"><div class="em">📝</div><div class="et">Нет запланированных — добавьте тренировку</div></div>
    <div v-for="s in upcoming" :key="s.id" class="card">
      <div class="flex-between" @click="toggleExpand(s.id)" style="cursor:pointer;">
        <div>
          <span class="pill-group" :style="{ background: groupColor(s.group) }">{{ s.group }}</span>
          <span style="margin-left:8px; font-weight:700; font-size:14px;">{{ relativeDay(s.date) }}</span>
        </div>
        <span class="tiny">{{ human(s.date) }} · {{ s.time }} ▾</span>
      </div>
      <template v-if="expanded === s.id">
        <div class="mt"><ExerciseList :exercises="s.exercises" /></div>
        <button class="btn danger sm mt" @click="actions.removeSession(store.activeClientId, s.id)">Удалить тренировку</button>
      </template>
    </div>

    <div class="section-title mt">История</div>
    <div v-if="!past.length" class="empty"><div class="em">📚</div><div class="et">История пуста</div></div>
    <div v-for="s in past" :key="s.id" class="card pad-sm">
      <div class="flex-between">
        <div>
          <span class="pill-group" :style="{ background: groupColor(s.group) }">{{ s.group }}</span>
          <span style="margin-left:8px; font-weight:700; font-size:13.5px;">{{ human(s.date) }}</span>
        </div>
        <span class="badge" :class="s.status">{{ s.status === 'done' ? 'Выполнено' : 'Пропущено' }}</span>
      </div>
      <div v-if="s.feedback" class="fb-note">
        <div class="stars">{{ '★'.repeat(s.feedback.rating) }}<span style="color:#e2e8f0">{{ '★'.repeat(5 - s.feedback.rating) }}</span></div>
        «{{ s.feedback.note }}»
      </div>
    </div>
  </div>
</template>
