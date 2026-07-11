<template>
  <aside class="trace-panel" aria-label="SchAgent Agent 执行过程">
    <div class="panel-title trace-title">
      <span>执行轨迹</span>
      <span class="trace-status" :class="status">{{ statusText }}</span>
    </div>

    <div v-if="!steps.length && !toolCalls.length" class="empty-trace">
      等待任务输入
    </div>

    <section v-if="steps.length" class="trace-section">
      <h2>主要步骤</h2>
      <ol class="step-list">
        <li v-for="(step, index) in steps" :key="`${step}-${index}`">
          <span>{{ index + 1 }}</span>
          <p>{{ step }}</p>
        </li>
      </ol>
    </section>

    <section v-if="toolCalls.length" class="trace-section">
      <h2>工具调用</h2>
      <ToolCallCard
        v-for="(call, index) in toolCalls"
        :key="`${call.tool}-${index}`"
        :call="call"
      />
    </section>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import ToolCallCard from './ToolCallCard.vue'

const props = defineProps({
  steps: {
    type: Array,
    default: () => []
  },
  toolCalls: {
    type: Array,
    default: () => []
  },
  status: {
    type: String,
    default: 'idle'
  }
})

const statusText = computed(() => {
  const map = {
    idle: '就绪',
    running: '执行中',
    error: '异常',
    need_clarification: '待补充'
  }
  return map[props.status] || '就绪'
})
</script>
