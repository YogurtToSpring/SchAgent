<template>
  <div ref="windowRef" class="chat-window">
    <MessageBubble
      v-for="message in messages"
      :key="message.id"
      :message="message"
      @quick-reply="$emit('quick-reply', $event)"
    />

    <div v-if="loading" class="assistant-thinking">
      <span></span>
      <span></span>
      <span></span>
      正在执行任务
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import MessageBubble from './MessageBubble.vue'

const props = defineProps({
  messages: {
    type: Array,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['quick-reply'])

const windowRef = ref(null)

watch(
  () => [props.messages.length, props.loading],
  async () => {
    await nextTick()
    if (windowRef.value) {
      windowRef.value.scrollTop = windowRef.value.scrollHeight
    }
  }
)
</script>
