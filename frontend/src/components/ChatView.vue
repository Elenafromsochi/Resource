<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { store, actions, clientMessages, activeClient } from '../store.js'
import { msgTime } from '../format.js'

const draft = ref('')
const listEl = ref(null)

const me = computed(() => store.role) // 'trainer' | 'client'
const clientId = computed(() => store.activeClientId)
const partner = computed(() =>
  store.role === 'trainer' ? activeClient() : store.trainer
)
const messages = computed(() => clientMessages(clientId.value))

function scrollDown() {
  nextTick(() => {
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  })
}

function send() {
  actions.sendMessage(clientId.value, me.value, draft.value)
  draft.value = ''
  scrollDown()
}

function markRead() {
  actions.markMessagesRead(clientId.value, me.value)
}

onMounted(() => { markRead(); scrollDown() })
watch([clientId, () => store.role], () => { markRead(); scrollDown() })
watch(() => messages.value.length, scrollDown)
</script>

<template>
  <div class="chat-wrap" style="height: calc(100vh - 320px); min-height: 380px;">
    <div class="card pad-sm flex-between" style="margin-bottom:12px;">
      <div style="display:flex; align-items:center; gap:10px;">
        <div style="font-size:26px;">{{ partner.avatar }}</div>
        <div>
          <div style="font-weight:700; font-size:14px;">{{ partner.name }}</div>
          <div class="tiny">{{ me === 'trainer' ? 'Клиент' : partner.title }}</div>
        </div>
      </div>
      <span class="tiny">● онлайн</span>
    </div>

    <div ref="listEl" class="chat-list">
      <div
        v-for="m in messages"
        :key="m.id"
        class="msg"
        :class="{
          mine: m.from === me,
          theirs: m.from !== me,
          purple: m.from === me && me === 'client',
        }"
      >
        {{ m.text }}
        <span class="t">{{ msgTime(m.at) }}</span>
      </div>
      <div v-if="!messages.length" class="empty"><div class="em">💬</div><div class="et">Пока сообщений нет</div></div>
    </div>

    <div class="chat-input">
      <input v-model="draft" placeholder="Сообщение…" @keyup.enter="send" />
      <button :class="{ purple: me === 'client' }" @click="send">➤</button>
    </div>
  </div>
</template>
