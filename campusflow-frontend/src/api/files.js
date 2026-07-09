import axios from 'axios'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

export async function listAgentFiles() {
  const { data } = await axios.get(`${apiBaseUrl}/api/files`, {
    timeout: 12000
  })
  const files = Array.isArray(data?.files) ? data.files : []
  return files.map(file => ({
    id: `agent-${file.name}`,
    name: file.name,
    type: fileType(file.name),
    source: '助手生成',
    size: file.size || 0,
    size_formatted: file.size_formatted || formatFileSize(file.size || 0),
    createdAt: file.modified_at || 'Agent 工作区',
    url: normalizeUrl(file.url || `/api/files/${encodeURIComponent(file.name)}`)
  }))
}

function normalizeUrl(url) {
  if (!url) return ''
  if (/^https?:\/\//i.test(url)) return url
  if (url.startsWith('/')) return `${apiBaseUrl}${url}`
  return `${apiBaseUrl}/${url.replace(/^\/+/, '')}`
}

function fileType(name = '') {
  const ext = name.split('.').pop()?.toUpperCase()
  return ext || 'FILE'
}

function formatFileSize(size) {
  const numericSize = Number(size || 0)
  if (!numericSize) return ''
  const units = ['B', 'KB', 'MB', 'GB']
  let value = numericSize
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`
}
