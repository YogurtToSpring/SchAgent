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
  return mergeArtifacts(props.artifacts, inferFileArtifactsFromText(props.content))
})

function normalizeMarkdownText(text) {
  return String(text || '')
    .replace(/\r\n/g, '\n')
    .replace(/\\n/g, '\n')
    .replace(/\\t/g, '  ')
    .trim()
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

function inferFileArtifactsFromText(text = '') {
  return extractFileNames(text).map(name => ({
    type: 'file',
    title: '生成文件',
    name,
    path: name,
    url: buildFileDownloadUrl(name)
  }))
}

function extractFileNames(text = '') {
  const source = String(text || '')
  const extensionPattern = /\.(?:pdf|md|docx?|xlsx?|pptx?|csv|txt|html?|json)/gi
  const names = []
  let match = extensionPattern.exec(source)
  while (match) {
    const end = match.index + match[0].length
    const start = findFileNameStart(source, match.index)
    const name = cleanFileName(source.slice(start, end))
    if (name && !names.includes(name)) {
      names.push(name)
    }
    match = extensionPattern.exec(source)
  }
  return names
}

function findFileNameStart(source, extensionIndex) {
  const separators = new Set([
    ' ', '\n', '\t', '\r', '"', "'", '`', '<', '>', '，', '。', '；', '、',
    '：', ':', '（', '(', '【', '[', '《', '/'
  ])
  let index = extensionIndex - 1
  while (index >= 0 && !separators.has(source[index])) {
    index -= 1
  }
  return index + 1
}

function cleanFileName(name = '') {
  const cleaned = String(name)
    .replace(/^[/\\]+/, '')
    .replace(/[，。；、：:）)】\]》>]+$/g, '')
    .trim()
  if (!cleaned || cleaned.startsWith('.')) return ''
  return cleaned
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
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8080'
  return `${apiBaseUrl}/api/files/${encodeURIComponent(fileName)}`
}
</script>
