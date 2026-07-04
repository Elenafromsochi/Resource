<script setup>
const props = defineProps({
  exercises: { type: Array, required: true },
  interactive: { type: Boolean, default: false },
})
const emit = defineEmits(['toggle'])
</script>

<template>
  <div>
    <div
      v-for="(ex, i) in exercises"
      :key="i"
      class="exercise"
      :class="{ 'ex-done': ex.done }"
    >
      <div
        class="check"
        :class="{ on: ex.done }"
        :style="{ cursor: interactive ? 'pointer' : 'default' }"
        @click="interactive && emit('toggle', i)"
      >✓</div>
      <div style="flex:1; min-width:0;">
        <div class="ex-name">{{ ex.name }}</div>
        <div v-if="ex.combo" class="ex-combo">+ {{ ex.combo }}</div>
      </div>
      <span v-if="ex.scheme" class="scheme">{{ ex.scheme }}</span>
    </div>
  </div>
</template>
