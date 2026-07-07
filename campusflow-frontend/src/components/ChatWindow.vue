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
import { computed, nextTick, ref, watch } from 'vue'
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
const lastMessageFingerprint = computed(() => {
  const last = props.messages[props.messages.length - 1]
  return `${props.messages.length}:${last?.content || ''}:${last?.reasoning || ''}:${last?.streamingStatus || ''}:${last?.isStreaming || false}`
})

watch(
  () => [lastMessageFingerprint.value, props.loading],
  async () => {
    await nextTick()
    if (windowRef.value) {
      windowRef.value.scrollTop = windowRef.value.scrollHeight
    }
  }
)
</script>
