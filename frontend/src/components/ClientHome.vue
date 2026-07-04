<script setup>
import { computed } from 'vue'
import { store, actions, clientPlan, activeClient, groupColor, dayISO } from '../store.js'
import { relativeDay, human } from '../format.js'

const client = computed(() => activeClient())
const plan = computed(() => clientPlan(store.activeClientId))
const today = dayISO(0)

const next = computed(() =>
  plan.value.filter(s => s.status === 'planned' && s.date >= today)[0] || null
)

const stats = computed(() => {
  const done = plan.value.filter(s => s.status === 'done').length
  const planned = plan.value.filter(s => s.status === 'planned').length
  const total = done + plan.value.filter(s => s.status === 'skipped').length
  const rate = total ? Math.round((done / total) * 100) : 0
  return { done, planned, rate }
})

const avgRating = computed(() => {
  const fb = plan.value.filter(s => s.feedback).map(s => s.feedback.rating)
  if (!fb.length) return '—'
  return (fb.reduce((a, b) => a + b, 0) / fb.length).toFixed(1)
})
</script>

<template>
  <div>
    <div class="card" style="background: linear-gradient(135deg,#7c3aed,#8b5cf6); color:#fff; border:none;">
      <div style="font-size:13px; opacity:.85;">Привет, {{ client.name.split(' ')[0] }}! 👋</div>
      <div style="font-size:18px; font-weight:800; margin-top:2px;">Твой прогресс</div>
      <div style="display:flex; gap:18px; margin-top:14px;">
        <div><div style="font-size:22px; font-weight:800;">{{ stats.done }}</div><div style="font-size:11px; opacity:.85;">выполнено</div></div>
        <div><div style="font-size:22px; font-weight:800;">{{ stats.rate }}%</div><div style="font-size:11px; opacity:.85;">регулярность</div></div>
        <div><div style="font-size:22px; font-weight:800;">{{ avgRating }}</div><div style="font-size:11px; opacity:.85;">ср. оценка</div></div>
      </div>
    </div>

    <div class="section-title">Следующая тренировка</div>
    <div v-if="!next" class="empty"><div class="em">🎉</div><div class="et">Всё выполнено! Тренер добавит новые.</div></div>
    <div v-else class="card">
      <div class="flex-between" style="margin-bottom:10px;">
        <span class="pill-group" :style="{ background: groupColor(next.group) }">{{ next.group }}</span>
        <span class="badge planned">{{ relativeDay(next.date) }}, {{ next.time }}</span>
      </div>
      <div style="font-weight:800; font-size:16px;">{{ next.title }}</div>
      <div class="tiny" style="margin-top:2px;">{{ next.exercises.length }} упражнений · {{ human(next.date) }}</div>
      <div class="progress mt"><i :style="{ width: '0%' }"></i></div>
      <button class="btn purple mt" @click="actions.setTab('plan')">Открыть тренировку</button>
    </div>

    <div v-if="next && relativeDay(next.date) === 'Сегодня'" class="card pad-sm" style="border-color:var(--accent-2); background:#f5f3ff;">
      <div style="font-weight:700; font-size:13.5px; color:#6d28d9;">⏰ Напоминание: сегодня тренировка в {{ next.time }}. Не забудь воду 💧</div>
    </div>
  </div>
</template>
