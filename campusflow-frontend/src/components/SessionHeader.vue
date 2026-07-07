<template>
  <header class="session-header">
    <div class="brand">
      <div class="brand-mark">CF</div>
      <div>
        <h1>CampusFlow</h1>
        <p>校园学习生活调度智能体</p>
      </div>
    </div>

    <div class="header-actions">
      <span class="session-pill">
        {{ sessionId ? `会话 ${shortSessionId}` : '未建立会话' }}
      </span>
      <span class="status-pill" :class="{ running: loading }">
        {{ loading ? '执行中' : '就绪' }}
      </span>
      <button class="icon-button text-button" type="button" @click="$emit('new-session')">
        <RefreshCcw :size="17" />
        新建会话
      </button>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { RefreshCcw } from 'lucide-vue-next'

const props = defineProps({
  sessionId: {
    type: String,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['new-session'])

const shortSessionId = computed(() => props.sessionId?.slice(-8))
</script>
