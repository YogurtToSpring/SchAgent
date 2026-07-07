<template>
  <div class="result-renderer">
    <div class="markdown-body" v-html="safeHtml"></div>

    <section
      v-for="(artifact, index) in artifacts"
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
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

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

function normalizeMarkdownText(text) {
  return String(text || '')
    .replace(/\r\n/g, '\n')
    .replace(/\\n/g, '\n')
    .replace(/\\t/g, '  ')
    .trim()
}
</script>
