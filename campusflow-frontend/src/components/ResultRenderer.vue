<template>
  <div class="result-renderer">
    <div class="markdown-body" v-html="safeHtml"></div>

    <section
      v-for="(artifact, index) in renderedArtifacts"
      :key="`${artifact.type}-${index}`"
      class="artifact"
    >
      <h3>{{ artifact.title }}</h3>
      <div v-if="artifact.type === 'table'" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th v-for="column in artifact.columns" :key="column">{{ column }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in artifact.rows" :key="rowIndex">
              <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="artifact.type === 'file'" class="download-artifact">
        <div class="download-meta">
          <Download :size="20" />
          <div>
            <strong>{{ artifact.name || artifact.title || '生成文件' }}</strong>
            <span>{{ fileMeta(artifact) }}</span>
          </div>
        </div>
        <a
          v-if="artifact.url"
          class="download-action"
          :href="artifact.url"
          :download="artifact.name || true"
          target="_blank"
          rel="noopener"
        >
          <Download :size="16" />
          下载
        </a>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { Download } from 'lucide-vue-next'

const props = defineProps({
  content: {
    type: String,
    default: ''
  },
  artifacts: {
    type: Array,
    default: () => []
  }
})

marked.setOptions({
  breaks: true,
  gfm: true,
  async: false
})

const safeHtml = computed(() => {
  return DOMPurify.sanitize(marked.parse(normalizeMarkdownText(props.content)))
})

const renderedArtifacts = computed(() => {
  return props.artifacts
})

function normalizeMarkdownText(text) {
  return String(text || '')
    .replace(/\r\n/g, '\n')
    .replace(/\\n/g, '\n')
    .replace(/\\t/g, '  ')
}

function fileMeta(file) {
  return [file.size_formatted, formatDate(file.modified_at)].filter(Boolean).join(' · ') || '可下载文件'
}

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function mergeArtifacts(current = [], next = []) {
  const merged = [...current]
  for (const artifact of next) {
    const key = artifact.type === 'file' ? `file:${artifact.name || artifact.path}` : `${artifact.type}:${artifact.title || ''}`
    const exists = merged.some(item => {
      const itemKey = item.type === 'file' ? `file:${item.name || item.path}` : `${item.type}:${item.title || ''}`
      return itemKey === key
    })
    if (!exists) merged.push(artifact)
  }
  return merged
}

function buildFileDownloadUrl(fileName) {
  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
  return `${apiBaseUrl}/api/files/${encodeURIComponent(fileName)}`
}
</script>
