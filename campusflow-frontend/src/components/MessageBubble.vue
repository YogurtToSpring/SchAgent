<template>
  <article class="message-row" :class="message.role">
    <div class="message-bubble" :class="[message.role, message.type]">
      <div class="message-meta">
        <span>{{ message.role === 'user' ? '我' : 'CampusFlow' }}</span>
        <time>{{ message.createdAt }}</time>
      </div>

      <div v-if="message.type === 'clarification'" class="clarification-banner">
        <AlertTriangle :size="17" />
        <span>需要补充信息</span>
      </div>

      <ResultRenderer :content="message.content" :artifacts="message.artifacts" />

      <div v-if="message.type === 'clarification'" class="clarification-actions">
        <button type="button" @click="$emit('quick-reply', '今天上午我有没有课？')">今天</button>
        <button type="button" @click="$emit('quick-reply', '明天上午我有没有课？')">明天</button>
        <button type="button" @click="$emit('quick-reply', '本周课表安排')">本周</button>
      </div>
    </div>
  </article>
</template>

<script setup>
import { AlertTriangle } from 'lucide-vue-next'
import ResultRenderer from './ResultRenderer.vue'

defineProps({
  message: {
    type: Object,
    required: true
  }
})

defineEmits(['quick-reply'])
</script>
