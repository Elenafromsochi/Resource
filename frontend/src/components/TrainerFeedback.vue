<script setup>
import { computed, onMounted } from 'vue'
import { store, actions, clientPlan } from '../store.js'
import { human, relativeDay } from '../format.js'

// Все отзывы клиентов, новые — сверху и подсвечены.
const items = computed(() => {
  const arr = []
  for (const c of store.clients) {
    for (const s of clientPlan(c.id)) {
      if (s.status === 'done' && s.feedback) {
        arr.push({ session: s, client: c })
      }
    }
  }
  return arr.sort((a, b) => (b.session.feedback.at || '').localeCompare(a.session.feedback.at || ''))
})

const newCount = computed(() => items.value.filter(i => !i.session.seenByTrainer).length)

function markAllSeen() {
  for (const i of items.value) {
    if (!i.session.seenByTrainer) actions.markFeedbackSeen(i.client.id, i.session.id)
  }
}
</script>

<template>
  <div>
    <div class="flex-between" style="margin-bottom:10px;">
      <div class="section-title mb0">Отзывы клиентов</div>
      <button v-if="newCount" class="btn ghost sm" @click="markAllSeen">Прочитать всё ({{ newCount }})</button>
    </div>

    <div v-if="!items.length" class="empty"><div class="em">⭐</div><div class="et">Отзывов пока нет</div></div>

    <div
      v-for="i in items"
      :key="i.session.id"
      class="card"
      :style="!i.session.seenByTrainer ? 'border-color: var(--accent); background: var(--accent-soft);' : ''"
      @click="actions.markFeedbackSeen(i.client.id, i.session.id)"
    >
      <div class="flex-between">
        <div style="display:flex; align-items:center; gap:10px;">
          <div style="font-size:24px;">{{ i.client.avatar }}</div>
          <div>
            <div style="font-weight:700; font-size:14px;">
              {{ i.client.name }}
              <span v-if="!i.session.seenByTrainer" style="color:var(--accent); font-size:11px;">● новый</span>
            </div>
            <div class="tiny">{{ i.session.title }} · {{ human(i.session.date) }}</div>
          </div>
        </div>
        <div class="stars">{{ '★'.repeat(i.session.feedback.rating) }}<span style="color:#e2e8f0">{{ '★'.repeat(5 - i.session.feedback.rating) }}</span></div>
      </div>

      <div v-if="i.session.feedback.note" class="fb-note">«{{ i.session.feedback.note }}»</div>

      <div class="fb-tags">
        <span class="tag">Нагрузка: {{ i.session.feedback.difficulty }}</span>
        <span class="tag">Самочувствие: {{ i.session.feedback.energy }}</span>
      </div>
    </div>
  </div>
</template>
