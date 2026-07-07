<template>
  <details class="tool-card" open>
    <summary>
      <div class="tool-summary">
        <component :is="icon" :size="18" />
        <div>
          <strong>{{ call.label || call.tool }}</strong>
          <span>{{ call.tool }}</span>
        </div>
      </div>
      <span class="tool-status" :class="call.status">{{ statusText }}</span>
    </summary>

    <div class="tool-body">
      <div>
        <h3>输入参数</h3>
        <pre>{{ formatJson(call.input) }}</pre>
      </div>
      <div>
        <h3>返回结果</h3>
        <pre>{{ formatJson(call.output) }}</pre>
      </div>
    </div>
  </details>
</template>

<script setup>
import { computed } from 'vue'
import { Calculator, CalendarDays, CloudSun, FileSearch, MapPinned, Wrench } from 'lucide-vue-next'

const props = defineProps({
  call: {
    type: Object,
    required: true
  }
})

const icon = computed(() => {
  if (props.call.tool?.includes('course') || props.call.tool?.includes('schedule')) return CalendarDays
  if (props.call.tool?.includes('weather')) return CloudSun
  if (props.call.tool?.includes('route') || props.call.tool?.includes('location')) return MapPinned
  if (props.call.tool?.includes('file')) return FileSearch
  if (props.call.tool?.includes('calculator')) return Calculator
  return Wrench
})

const statusText = computed(() => {
  const map = {
    success: '成功',
    failed: '失败',
    running: '执行中',
    fallback: '已降级'
  }
  return map[props.call.status] || props.call.status || '未知'
})

function formatJson(value) {
  return JSON.stringify(value ?? {}, null, 2)
}
</script>
