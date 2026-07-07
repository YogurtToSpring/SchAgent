<template>
  <form class="chat-input" @submit.prevent="submit">
    <textarea
      v-model="text"
      :disabled="disabled"
      rows="1"
      placeholder="输入你的问题，例如：明天上午我有没有课？"
      @keydown.enter.exact.prevent="submit"
      @keydown.shift.enter.stop
    ></textarea>
    <button class="icon-button send-button" type="submit" :disabled="disabled || !text.trim()">
      <SendHorizontal :size="18" />
      发送
    </button>
  </form>
</template>

<script setup>
import { ref } from 'vue'
import { SendHorizontal } from 'lucide-vue-next'

defineProps({
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['send'])
const text = ref('')

function submit() {
  const value = text.value.trim()
  if (!value) return
  emit('send', value)
  text.value = ''
}
</script>
