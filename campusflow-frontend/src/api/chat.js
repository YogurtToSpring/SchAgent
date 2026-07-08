import axios from 'axios'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8080'
const useMock = import.meta.env.VITE_USE_MOCK === 'true'

export async function sendMessage(payload) {
  if (useMock) {
    return mockChatResponse(payload)
  }

  const { data } = await axios.post(`${apiBaseUrl}/api/chat`, payload, {
    timeout: 30000
  })
  return normalizeChatResponse(data)
}

export async function sendMessageStream(payload, handlers = {}) {
  if (useMock) {
    return streamMockResponse(payload, handlers)
  }

  try {
    return await requestStream(payload, handlers)
  } catch (error) {
    const response = await sendMessage(payload)
    const split = splitReasoning(response.answer || '')
    response.answer = split.answer
    response.reasoning = split.reasoning
    handlers.onReasoning?.(split.reasoning)
    handlers.onToken?.(split.answer)
    handlers.onDone?.(response)
    return response
  }
}

async function requestStream(payload, handlers) {
  const response = await fetch(`${apiBaseUrl}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })

  if (!response.ok || !response.body) {
    throw new Error(`流式接口返回 ${response.status}`)
  }

  const result = {
    session_id: payload.session_id,
    status: 'success',
    answer: '',
    reasoning: '',
    steps: [],
    tool_calls: [],
    artifacts: [],
    files: []
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let currentEvent = ''
  let dataLines = []

  function flushEvent() {
    if (!currentEvent || !dataLines.length) return
    const eventName = currentEvent
    const rawData = dataLines.join('\n')
    currentEvent = ''
    dataLines = []

    let data
    try {
      data = JSON.parse(rawData)
    } catch {
      return
    }
    applyStreamEvent(eventName, data, result, handlers)
  }

  function readLine(line) {
    if (!line.trim()) {
      flushEvent()
      return
    }
    if (line.startsWith('event:')) {
      if (currentEvent && dataLines.length) flushEvent()
      currentEvent = line.slice(6).trim()
      return
    }
    if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart())
      flushEvent()
    }
  }

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split(/\r?\n/)
    buffer = lines.pop() || ''
    for (const line of lines) readLine(line)
  }

  buffer += decoder.decode()
  if (buffer) readLine(buffer)
  flushEvent()

  const split = splitReasoning(result.answer)
  if (split.reasoning) {
    result.reasoning = result.reasoning
      ? `${result.reasoning}\n${split.reasoning}`.trim()
      : split.reasoning
    result.answer = split.answer
  }

  result.artifacts = mergeArtifacts(result.artifacts, inferFileArtifactsFromText(result.answer))
  result.artifacts = mergeArtifacts(result.artifacts, filesToArtifacts(result.files))
  handlers.onDone?.(result)
  return result
}

function applyStreamEvent(eventName, data, result, handlers) {
  if (eventName === 'status') {
    const step = data.message || ''
    if (step && !result.steps.includes(step)) {
      result.steps.push(step)
      handlers.onStep?.(step, data)
    }
    return
  }

  if (eventName === 'token') {
    const content = data.content || ''
    if (!content) return
    if (data.phase === 'reasoning') {
      result.reasoning += content
      handlers.onReasoning?.(content, data)
      return
    }
    result.answer += content
    handlers.onToken?.(content, data)
    return
  }

  if (eventName === 'tool_call') {
    const call = {
      tool: data.name || 'unknown',
      label: toolLabel(data.name),
      status: 'running',
      input: data.args || {},
      output: null
    }
    result.tool_calls.push(call)
    handlers.onToolCall?.(call, data)
    return
  }

  if (eventName === 'tool_result') {
    const call = [...result.tool_calls].reverse().find(item => item.tool === data.name && item.output == null)
    if (call) {
      call.status = data.success === false ? 'failed' : 'success'
      call.output = data.result || ''
      handlers.onToolResult?.(call, data)
    }
    const inferredArtifacts = inferFileArtifactsFromText(data.result || '')
    if (inferredArtifacts.length) {
      result.artifacts = mergeArtifacts(result.artifacts, inferredArtifacts)
      result.files = mergeFiles(result.files, inferredArtifacts.map(artifactToFile))
      for (const artifact of inferredArtifacts) {
        handlers.onFileReady?.(artifact, data)
      }
    }
    return
  }

  if (eventName === 'file_ready') {
    const file = normalizeFile(data)
    if (!file.name) return
    result.files.push(file)
    const artifact = fileToArtifact(file)
    result.artifacts = mergeArtifacts(result.artifacts, [artifact])
    handlers.onFileReady?.(artifact, data)
    return
  }

  if (eventName === 'error') {
    result.status = 'failed'
    result.answer = data.message || '智能体执行失败。'
    handlers.onError?.(result.answer, data)
    return
  }

  if (eventName === 'done') {
    result.session_id = data.session_id || result.session_id
    if (Array.isArray(data.files)) {
      result.files = data.files.map(normalizeFile).filter(file => file.name)
      result.artifacts = mergeArtifacts(result.artifacts, filesToArtifacts(result.files))
    }
    if (data.error && result.status === 'success') {
      result.status = 'failed'
    }
  }
}

function normalizeChatResponse(response) {
  const normalized = {
    ...response,
    artifacts: Array.isArray(response.artifacts) ? response.artifacts : [],
    files: Array.isArray(response.files) ? response.files.map(normalizeFile).filter(file => file.name) : []
  }
  normalized.artifacts = mergeArtifacts(normalized.artifacts, inferFileArtifactsFromText(normalized.answer || ''))
  normalized.artifacts = mergeArtifacts(
    normalized.artifacts,
    inferFileArtifactsFromText((normalized.tool_calls || []).map(call => call.output || '').join('\n'))
  )
  normalized.artifacts = mergeArtifacts(normalized.artifacts, filesToArtifacts(normalized.files))
  return normalized
}

function normalizeFile(file = {}) {
  const name = file.name || file.file_name || file.filename || file.path || ''
  const path = file.path || name
  const downloadUrl = file.url || file.download_url || file.downloadUrl || buildFileDownloadUrl(name)
  return {
    name,
    path,
    size: file.size || 0,
    size_formatted: file.size_formatted || file.sizeFormatted || formatFileSize(file.size || 0),
    modified_at: file.modified_at || file.modifiedAt || '',
    url: normalizeFileUrl(downloadUrl)
  }
}

function filesToArtifacts(files = []) {
  return files.map(fileToArtifact)
}

function inferFileArtifactsFromText(text = '') {
  return extractFileNames(text).map(name => fileToArtifact(normalizeFile({ name, path: name })))
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

function artifactToFile(artifact = {}) {
  return normalizeFile({
    name: artifact.name,
    path: artifact.path,
    size: artifact.size,
    size_formatted: artifact.size_formatted,
    modified_at: artifact.modified_at,
    url: artifact.url
  })
}

function fileToArtifact(file) {
  return {
    type: 'file',
    title: '生成文件',
    name: file.name,
    path: file.path,
    size: file.size,
    size_formatted: file.size_formatted,
    modified_at: file.modified_at,
    url: file.url || buildFileDownloadUrl(file.name)
  }
}

function mergeArtifacts(current = [], next = []) {
  const merged = [...current]
  for (const artifact of next) {
    const key = artifactKey(artifact)
    const exists = merged.some(item => artifactKey(item) === key)
    if (!exists) merged.push(artifact)
  }
  return merged
}

function mergeFiles(current = [], next = []) {
  const merged = [...current]
  for (const file of next) {
    if (!file.name) continue
    const exists = merged.some(item => item.name === file.name || item.path === file.path)
    if (!exists) merged.push(file)
  }
  return merged
}

function artifactKey(artifact = {}) {
  if (artifact.type === 'file') return `file:${artifact.name || artifact.path || artifact.url}`
  return `${artifact.type}:${artifact.title || ''}:${JSON.stringify(artifact.columns || [])}`
}

function buildFileDownloadUrl(fileName) {
  if (!fileName) return ''
  return `${apiBaseUrl}/api/files/${encodeURIComponent(fileName)}`
}

function normalizeFileUrl(url) {
  if (!url) return ''
  if (/^https?:\/\//i.test(url)) return url
  if (url.startsWith('/')) return `${apiBaseUrl}${url}`
  return `${apiBaseUrl}/${url.replace(/^\/+/, '')}`
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

function splitReasoning(text) {
  const normalized = normalizeMarkdownText(text)
  const thinkMatch = normalized.match(/<think>([\s\S]*?)<\/think>/i)
  if (thinkMatch) {
    return {
      reasoning: thinkMatch[1].trim(),
      answer: normalized.replace(thinkMatch[0], '').trim()
    }
  }

  const answerMarker = normalized.match(/(?:^|\n)(?:正式回复|最终回答|答案)[:：]/)
  const reasoningMarker = normalized.match(/(?:^|\n)(?:思考过程|思考|推理过程|Reasoning)[:：]/i)
  if (reasoningMarker && answerMarker && reasoningMarker.index < answerMarker.index) {
    return {
      reasoning: normalized.slice(reasoningMarker.index, answerMarker.index).replace(/^(思考过程|思考|推理过程|Reasoning)[:：]/i, '').trim(),
      answer: normalized.slice(answerMarker.index).replace(/^(正式回复|最终回答|答案)[:：]/, '').trim()
    }
  }

  return {
    reasoning: '',
    answer: normalized
  }
}

function normalizeMarkdownText(text) {
  return String(text || '')
    .replace(/\r\n/g, '\n')
    .replace(/\\n/g, '\n')
    .trim()
}

async function streamMockResponse(payload, handlers) {
  const response = await mockChatResponse(payload)
  const reasoning = '根据当前用户角色、课表数据和问题意图，判断需要查询课程与天气信息。'
  handlers.onStep?.('正在分析问题')
  for (const chunk of chunkText(reasoning, 8)) {
    handlers.onReasoning?.(chunk, { phase: 'reasoning' })
    await wait(20)
  }
  for (const step of response.steps || []) {
    handlers.onStep?.(step)
    await wait(40)
  }
  for (const call of response.tool_calls || []) {
    handlers.onToolCall?.({ ...call, status: 'running', output: null })
    await wait(80)
    handlers.onToolResult?.(call)
  }
  for (const chunk of chunkText(response.answer || '', 8)) {
    handlers.onToken?.(chunk, { phase: 'responding' })
    await wait(20)
  }
  handlers.onDone?.({ ...response, reasoning })
  return { ...response, reasoning }
}

function chunkText(text, size) {
  const chunks = []
  for (let index = 0; index < text.length; index += size) {
    chunks.push(text.slice(index, index + size))
  }
  return chunks
}

function toolLabel(name = '') {
  const labels = {
    get_weather: '天气查询',
    calculator: '数学计算',
    get_current_time: '时间查询',
    list_files: '文件列表',
    read_file: '读取文件',
    write_file: '写入文件',
    save_memory: '保存记忆',
    recall_memory: '读取记忆',
    markdown_to_html: 'Markdown转HTML',
    markdown_to_pdf: 'Markdown转PDF'
  }
  return labels[name] || name || '工具调用'
}

async function mockChatResponse({ session_id, message, user_context, platform_context }) {
  await wait(650)

  const text = message.trim()
  const sessionId = session_id || `mock-${Date.now()}`
  const role = user_context?.role || 'student'

  if (needsDate(text)) {
    return {
      session_id: sessionId,
      status: 'need_clarification',
      answer: '我还需要知道你想查询哪一天。可以直接回复“今天”“明天”或具体日期。',
      missing_fields: ['date'],
      steps: ['识别任务：课程查询', '发现缺少必要条件：日期'],
      tool_calls: [],
      artifacts: []
    }
  }

  if (role === 'teacher' && (text.includes('班') || text.includes('冲突') || text.includes('提醒'))) {
    return teacherClassResponse(sessionId, platform_context)
  }

  if (text.includes('学习计划') || text.includes('复习') || text.includes('考试')) {
    return studyPlanResponse(sessionId)
  }

  if (text.includes('骑车') || text.includes('天气') || text.includes('出门')) {
    return commuteResponse(sessionId)
  }

  return courseResponse(sessionId)
}

function teacherClassResponse(sessionId, platformContext = {}) {
  const targetClass = platformContext.classes?.find(item => item.name.includes('软件工程1班')) ||
    platformContext.classes?.[0] || {
      id: 'class-se-1',
      name: '软件工程1班'
    }
  const courses = (platformContext.courses || []).filter(item => item.classId === targetClass.id)

  return {
    session_id: sessionId,
    status: 'success',
    answer:
      `已按教师权限查询 **${targetClass.name}** 的课表。当前未发现明显时间冲突；如果需要，我可以继续生成班级课程提醒。`,
    steps: [
      '识别任务：班级课表查询 / 冲突检查',
      '校验当前用户角色：教师管理员',
      '调用班级查询工具',
      '调用班级课表查询工具',
      '调用课表冲突检测工具',
      '生成面向教师的处理建议'
    ],
    tool_calls: [
      {
        tool: 'class_query',
        label: '班级查询',
        status: 'success',
        input: {
          class_name: targetClass.name
        },
        output: {
          class_id: targetClass.id,
          class_name: targetClass.name
        }
      },
      {
        tool: 'class_schedule_query',
        label: '班级课表查询',
        status: 'success',
        input: {
          class_id: targetClass.id,
          range: '本周'
        },
        output: {
          course_count: courses.length,
          courses: courses.map(item => `${item.weekday} ${item.startTime}-${item.endTime} ${item.courseName}`)
        }
      },
      {
        tool: 'schedule_conflict_check',
        label: '课表冲突检测',
        status: 'success',
        input: {
          class_id: targetClass.id
        },
        output: {
          has_conflict: false,
          message: '未发现同一时间段重复课程'
        }
      }
    ],
    artifacts: [
      {
        type: 'table',
        title: `${targetClass.name}课表摘要`,
        columns: ['星期', '时间', '课程', '地点'],
        rows: courses.map(item => [
          item.weekday,
          `${item.startTime}-${item.endTime}`,
          item.courseName,
          item.location
        ])
      }
    ]
  }
}

function courseResponse(sessionId) {
  return {
    session_id: sessionId,
    status: 'success',
    answer:
      '明天上午有 **高等数学**，时间是 08:00-09:40，地点在三教302。建议 07:40 从宿舍出发，留出到教室和课前准备时间。',
    steps: [
      '识别任务：查询明天上午课程',
      '调用课程查询工具',
      '整理课程时间、地点和教师信息',
      '生成最终回答'
    ],
    tool_calls: [
      {
        tool: 'course_query',
        label: '课程查询',
        status: 'success',
        input: {
          date: '明天',
          time_range: '上午'
        },
        output: {
          course_name: '高等数学',
          time: '08:00-09:40',
          location: '三教302',
          teacher: '王老师'
        }
      }
    ],
    artifacts: [
      {
        type: 'table',
        title: '明日课程安排',
        columns: ['课程', '时间', '地点', '教师'],
        rows: [['高等数学', '08:00-09:40', '三教302', '王老师']]
      }
    ]
  }
}

function commuteResponse(sessionId) {
  return {
    session_id: sessionId,
    status: 'success',
    answer:
      '明天上午有 **高等数学**，天气为小雨，宿舍到三教步行约 12 分钟、骑车约 5 分钟。综合天气和路面情况，建议步行，07:40 出门更稳妥。',
    steps: [
      '识别任务：课程查询 + 天气查询 + 出行建议',
      '调用课程查询工具',
      '调用天气查询工具',
      '调用地点距离工具',
      '综合课程、天气和距离生成建议'
    ],
    tool_calls: [
      {
        tool: 'course_query',
        label: '课程查询',
        status: 'success',
        input: {
          date: '明天',
          time_range: '上午'
        },
        output: {
          course_name: '高等数学',
          time: '08:00-09:40',
          location: '三教302'
        }
      },
      {
        tool: 'weather_query',
        label: '天气查询',
        status: 'success',
        input: {
          date: '明天'
        },
        output: {
          weather: '小雨',
          temperature: '23-28℃',
          wind: '东北风 2 级'
        }
      },
      {
        tool: 'campus_route',
        label: '地点距离',
        status: 'success',
        input: {
          from: '宿舍1号楼',
          to: '三教'
        },
        output: {
          walking_minutes: 12,
          biking_minutes: 5,
          distance: '800米'
        }
      }
    ],
    artifacts: [
      {
        type: 'table',
        title: '出行判断',
        columns: ['项目', '结果'],
        rows: [
          ['课程', '高等数学 08:00-09:40'],
          ['地点', '三教302'],
          ['天气', '小雨，23-28℃'],
          ['建议', '不建议骑车，建议步行'],
          ['出门时间', '07:40']
        ]
      }
    ]
  }
}

function studyPlanResponse(sessionId) {
  return {
    session_id: sessionId,
    status: 'success',
    answer:
      '我根据课表、考试时间和资料重点生成了一个三天复习安排。今天建议先完成数据库第一轮复习，再处理高数作业。',
    steps: [
      '识别任务：学习规划',
      '查询近期课程和空闲时间',
      '查询考试与作业截止时间',
      '检索数据库复习资料',
      '计算任务优先级并生成计划'
    ],
    tool_calls: [
      {
        tool: 'schedule_query',
        label: '空闲时间查询',
        status: 'success',
        input: {
          range: '未来3天'
        },
        output: {
          free_slots: ['今天 19:00-21:00', '明天 15:00-17:00', '后天 20:00-21:30']
        }
      },
      {
        tool: 'deadline_query',
        label: '截止时间查询',
        status: 'success',
        input: {
          courses: ['数据库', '高等数学']
        },
        output: {
          database_exam: '下周三',
          math_homework: '本周五 23:59'
        }
      },
      {
        tool: 'file_search',
        label: '资料检索',
        status: 'success',
        input: {
          keyword: '数据库 重点'
        },
        output: {
          materials: ['事务与并发控制.md', 'SQL查询练习.md', '范式与ER图.md']
        }
      }
    ],
    artifacts: [
      {
        type: 'table',
        title: '三天复习计划',
        columns: ['时间', '任务', '原因'],
        rows: [
          ['今天 19:00-20:20', '数据库：事务与并发控制', '考试优先级最高'],
          ['今天 20:20-21:00', '高数作业', '截止时间较近'],
          ['明天 15:00-17:00', '数据库：SQL练习', '需要连续练习'],
          ['后天 20:00-21:30', '数据库：范式与ER图', '补齐薄弱章节']
        ]
      }
    ]
  }
}

function needsDate(text) {
  const asksSchedule = text.includes('有没有课') || text.includes('课表') || text.includes('课程')
  const hasDate =
    text.includes('今天') ||
    text.includes('明天') ||
    text.includes('后天') ||
    /\d{4}[-/年]\d{1,2}[-/月]\d{1,2}/.test(text)
  return asksSchedule && !hasDate
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
