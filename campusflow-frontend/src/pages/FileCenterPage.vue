<template>
  <section class="file-center-page module-page">
    <section class="module-toolbar content-panel">
      <div>
        <h2>文件中心</h2>
        <p>{{ visibleFiles.length }} 个文件</p>
      </div>
      <button class="ghost-action" type="button" @click="$emit('refresh-files')">刷新文件</button>
    </section>

    <section class="module-grid two-columns">
      <aside class="content-panel side-filter">
        <button
          v-for="source in sources"
          :key="source"
          type="button"
          :class="{ active: activeSource === source }"
          @click="activeSource = source"
        >
          <span>{{ source }}</span>
          <strong>{{ countBySource(source) }}</strong>
        </button>
      </aside>

      <section class="content-panel file-list">
        <article v-for="file in visibleFiles" :key="file.id || file.name" class="file-row">
          <div>
            <strong>{{ file.name }}</strong>
            <span>{{ file.type }} · {{ file.source }} · {{ file.size_formatted || '未知大小' }}</span>
          </div>
          <a v-if="file.url" class="download-action" :href="file.url" :download="file.name">下载</a>
          <button v-else class="ghost-action" type="button" disabled>待同步</button>
        </article>
      </section>
    </section>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  files: {
    type: Array,
    required: true
  }
})

defineEmits(['refresh-files'])

const activeSource = ref('全部文件')

const sources = computed(() => ['全部文件', ...new Set(props.files.map(item => item.source || '其他'))])

const visibleFiles = computed(() => {
  if (activeSource.value === '全部文件') return props.files
  return props.files.filter(item => item.source === activeSource.value)
})

function countBySource(source) {
  if (source === '全部文件') return props.files.length
  return props.files.filter(item => item.source === source).length
}
</script>
