<script setup>
import { ref, computed } from 'vue'
import { store, actions, clientPlan, groupColor, dayISO } from '../store.js'
import { relativeDay, human } from '../format.js'
import ExerciseList from './ExerciseList.vue'

const plan = computed(() => clientPlan(store.activeClientId))
const today = dayISO(0)
const upcoming = computed(() => plan.value.filter(s => s.status === 'planned'))
const history = computed(() => plan.value.filter(s => s.status !== 'planned').reverse())

const openId = ref(upcoming.value.length ? upcoming.value[0].id : null)
function toggle(id) { openId.value = openId.value === id ? null : id }

function progress(s) {
  const done = s.exercises.filter(e => e.done).length
  return Math.round((done / s.exercises.length) * 100)
}

// --- модалка отзыва ---
const fbFor = ref(null)
const fb = ref({ rating: 5, difficulty: 'В самый раз', energy: 'Бодрость', note: '' })
const difficulties = ['Легко', 'В самый раз', 'Тяжеловато', 'Тяжело']
const energies = ['Отлично', 'Бодрость', 'Норма', 'Устала']

function openFeedback(s) {
  fbFor.value = s
  fb.value = { rating: 5, difficulty: 'В самый раз', energy: 'Бодрость', note: '' }
}
function submitFeedback() {
  actions.completeSession(store.activeClientId, fbFor.value.id, { ...fb.value })
  fbFor.value = null
}
</script>

<template>
  <div>
    <div class="section-title">Мои тренировки</div>
    <div v-if="!upcoming.length" class="empty"><div class="em">✅</div><div class="et">Нет активных тренировок</div></div>

    <div v-for="s in upcoming" :key="s.id" class="card">
      <div class="flex-between" @click="toggle(s.id)" style="cursor:pointer;">
        <div>
          <span class="pill-group" :style="{ background: groupColor(s.group) }">{{ s.group }}</span>
          <span style="margin-left:8px; font-weight:800; font-size:15px;">{{ s.title.replace('Тренировка · ', '') }}</span>
          <div class="tiny" style="margin-top:3px;">{{ relativeDay(s.date) }} · {{ s.time }} · {{ human(s.date) }}</div>
        </div>
        <span class="tiny">{{ openId === s.id ? '▴' : '▾' }}</span>
      </div>

      <template v-if="openId === s.id">
        <div class="progress mt" style="margin-bottom:12px;"><i :style="{ width: progress(s) + '%' }"></i></div>
        <ExerciseList
          :exercises="s.exercises"
          interactive
          @toggle="idx => actions.toggleExercise(store.activeClientId, s.id, idx)"
        />
        <button class="btn purple mt" @click="openFeedback(s)">Завершить и оставить отзыв</button>
        <button class="btn ghost sm mt" style="width:100%;" @click="actions.markSkipped(store.activeClientId, s.id)">Пропустить тренировку</button>
      </template>
    </div>

    <div class="section-title mt">История</div>
    <div v-if="!history.length" class="empty"><div class="em">📚</div><div class="et">Ещё нет завершённых</div></div>
    <div v-for="s in history" :key="s.id" class="card pad-sm">
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

    <!-- модалка отзыва -->
    <div v-if="fbFor" class="modal-overlay" @click.self="fbFor = null">
      <div class="modal-sheet">
        <div class="notif-head">
          <b>Как прошла тренировка?</b>
          <button class="n-x" @click="fbFor = null">✕</button>
        </div>
        <div class="notif-body">
          <div class="field">
            <label>Оценка</label>
            <div style="font-size:30px; letter-spacing:6px; cursor:pointer;">
              <span v-for="n in 5" :key="n" @click="fb.rating = n" :style="{ color: n <= fb.rating ? '#f59e0b' : '#e2e8f0' }">★</span>
            </div>
          </div>
          <div class="field">
            <label>Нагрузка</label>
            <div class="fb-tags">
              <span v-for="d in difficulties" :key="d" class="tag" :style="d === fb.difficulty ? 'background:var(--accent-2); color:#fff; border-color:var(--accent-2);' : 'cursor:pointer'" @click="fb.difficulty = d">{{ d }}</span>
            </div>
          </div>
          <div class="field">
            <label>Самочувствие</label>
            <div class="fb-tags">
              <span v-for="e in energies" :key="e" class="tag" :style="e === fb.energy ? 'background:var(--accent-2); color:#fff; border-color:var(--accent-2);' : 'cursor:pointer'" @click="fb.energy = e">{{ e }}</span>
            </div>
          </div>
          <div class="field">
            <label>Комментарий тренеру</label>
            <textarea v-model="fb.note" placeholder="Что понравилось, что было тяжело…"></textarea>
          </div>
          <button class="btn purple" @click="submitFeedback">Отправить отзыв тренеру</button>
        </div>
      </div>
    </div>
  </div>
</template>
