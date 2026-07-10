<template>
  <section class="assistant-page">
    <aside class="assistant-sessions" aria-label="助手会话">
      <header class="assistant-session-header">
        <div>
          <span class="assistant-eyebrow">智能助手</span>
          <strong>会话</strong>
        </div>
        <button class="assistant-new-button" type="button" :disabled="loading" @click="startNewSession">
          <Plus :size="16" />
          新建
        </button>
      </header>

      <div class="assistant-session-list">
        <article
          v-for="session in sessions"
          :key="session.localId"
          class="assistant-session-item"
          :class="{ active: session.localId === activeLocalSessionId }"
          @click="switchSession(session.localId)"
        >
          <input
            class="session-title-input"
            :value="session.title"
            :disabled="loading && session.localId !== activeLocalSessionId"
            @click.stop
            @focus="switchSession(session.localId)"
            @input="renameSession(session.localId, $event.target.value)"
            @keydown.enter.prevent="$event.target.blur()"
          />
          <small>{{ sessionMeta(session) }}</small>
        </article>
      </div>

      <footer class="assistant-session-foot">
        <span>快捷问题会根据身份、课表和天气随机生成，执行过程默认收起。</span>
      </footer>
    </aside>

    <section class="assistant-conversation" aria-label="智能助手对话">
      <header class="assistant-conversation-header">
        <div class="conversation-title-group">
          <span class="assistant-eyebrow">CampusFlow Assistant</span>
          <input
            class="conversation-title-input"
            :value="currentSessionTitle"
            @input="renameSession(activeLocalSessionId, $event.target.value)"
            @keydown.enter.prevent="$event.target.blur()"
          />
          <p>{{ currentConversationSubtitle }}</p>
        </div>

        <div class="conversation-actions">
          <span class="status-pill" :class="currentStatus">{{ statusText }}</span>
        </div>
      </header>

      <div class="assistant-chat-body">
        <ChatWindow
          :messages="messages"
          :loading="loading"
          @quick-reply="sendQuickPrompt"
        />

        <div v-if="showStarterPrompts" class="starter-prompts" aria-label="快捷问题">
          <div class="starter-prompts-head">
            <span>可以这样问</span>
          </div>

          <div class="prompt-chip-list">
            <button
              v-for="item in quickPrompts"
              :key="item"
              class="prompt-chip"
              type="button"
              @click="sendQuickPrompt(item)"
            >
              {{ item }}
            </button>
          </div>
        </div>
      </div>

      <details
        v-if="steps.length || toolCalls.length || error"
        class="assistant-process"
        :open="traceOpen"
        @toggle="traceOpen = $event.target.open"
      >
        <summary>
          <span>执行过程</span>
          <small>{{ traceSummary }}</small>
        </summary>
        <ToolTrace
          :steps="steps"
          :tool-calls="toolCalls"
          :status="currentStatus"
        />
      </details>

      <div v-if="error" class="network-alert" role="alert">
        <div>
          <strong>连接失败</strong>
          <span>{{ error }}</span>
        </div>
        <button type="button" @click="retryLastMessage">重试</button>
      </div>

      <ChatInput :disabled="loading" @send="handleSend" />
    </section>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { Plus } from 'lucide-vue-next'
import { sendMessageStream } from '../api/chat'
import ChatInput from '../components/ChatInput.vue'
import ChatWindow from '../components/ChatWindow.vue'
import ToolTrace from '../components/ToolTrace.vue'

const props = defineProps({
  currentUser: {
    type: Object,
    required: true
  },
  classes: {
    type: Array,
    default: () => []
  },
  students: {
    type: Array,
    default: () => []
  },
  courses: {
    type: Array,
    default: () => []
  },
  weather: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['todo-updated'])

const DEFAULT_SESSION_TITLE = '新会话'
const MAX_SESSIONS = 18

const sessions = ref([])
const activeLocalSessionId = ref('')
const sessionId = ref(null)
const messages = ref([])
const steps = ref([])
const toolCalls = ref([])
const loading = ref(false)
const error = ref('')
const lastUserMessage = ref('')
const traceOpen = ref(false)

const quickPrompts = ref([])

const sessionStorageIdentity = computed(() => {
  const user = props.currentUser
  return [
    user.role,
    user.id || user.studentNo || user.teacherNo || user.username || user.name || 'anonymous'
  ].join(':')
})

const storageKey = computed(() => `campusflow.assistant.sessions.${sessionStorageIdentity.value}`)

const activeSession = computed(() => {
  return sessions.value.find(item => item.localId === activeLocalSessionId.value) || null
})

const currentSessionTitle = computed(() => activeSession.value?.title || DEFAULT_SESSION_TITLE)

const hasUserMessages = computed(() => messages.value.some(item => item.role === 'user'))

const showStarterPrompts = computed(() => !loading.value && !hasUserMessages.value)

const currentStatus = computed(() => {
  if (loading.value) return 'running'
  if (error.value) return 'error'
  const last = messages.value[messages.value.length - 1]
  return last?.type === 'clarification' ? 'need_clarification' : 'idle'
})

const statusText = computed(() => {
  const map = {
    idle: '就绪',
    running: '执行中',
    error: '异常',
    need_clarification: '待补充'
  }
  return map[currentStatus.value] || '就绪'
})

const traceSummary = computed(() => {
  if (error.value) return '出现异常，可重试'
  if (loading.value) return '正在理解任务并调用工具'
  if (toolCalls.value.length) return `已调用 ${toolCalls.value.length} 个工具`
  if (steps.value.length) return `记录 ${steps.value.length} 个步骤`
  return '暂无执行记录'
})

const currentConversationSubtitle = computed(() => {
  const parts = [roleLabel(props.currentUser.role), props.currentUser.name]
  if (sessionId.value) {
    parts.push(`智能体会话 ${shortId(sessionId.value)}`)
  } else {
    parts.push('本地新会话')
  }
  return parts.join(' · ')
})

watch(
  () => sessionStorageIdentity.value,
  () => {
    initializeSessions()
  },
  { immediate: true }
)

watch(
  () => [
    props.currentUser.role,
    props.classes.length,
    props.courses.length,
    props.weather.weather,
    props.weather.temperature
  ],
  () => {
    if (showStarterPrompts.value) {
      refreshQuickPrompts()
    }
  }
)

async function handleSend(text) {
  const content = text.trim()
  if (!content || loading.value) return

  error.value = ''
  lastUserMessage.value = content
  ensureActiveSessionTitle(content)

  messages.value.push(createMessage('user', 'normal', content))
  messages.value.push(createMessage('assistant', 'normal', '', {
    reasoning: '',
    artifacts: [],
    isStreaming: true,
    streamingStatus: '正在连接智能体...'
  }))
  const assistantIndex = messages.value.length - 1
  loading.value = true
  steps.value = ['正在连接智能体...']
  toolCalls.value = []
  saveCurrentSession()

  try {
    const finalResponse = await sendMessageStream(
      {
        session_id: sessionId.value,
        message: buildAgentMessage(content),
        user_context: buildUserContext(),
        platform_context: buildPlatformContext()
      },
      {
        onStep: step => {
          appendStep(step)
          patchAssistantMessage(assistantIndex, {
            streamingStatus: step || '正在生成回复...'
          })
        },
        onReasoning: chunk => {
          patchAssistantMessage(assistantIndex, current => ({
            reasoning: `${current.reasoning || ''}${chunk}`,
            streamingStatus: '正在生成正式回复...'
          }))
        },
        onToken: chunk => {
          patchAssistantMessage(assistantIndex, current => ({
            content: `${current.content || ''}${chunk}`,
            streamingStatus: ''
          }))
        },
        onToolCall: call => {
          toolCalls.value.push(call)
        },
        onToolResult: call => {
          const index = toolCalls.value.findIndex(
            item => item.tool === call.tool && item.output == null
          )
          if (index >= 0) {
            toolCalls.value[index] = { ...toolCalls.value[index], ...call }
          }
          if (isTodoTool(call.tool)) {
            emit('todo-updated')
          }
        },
        onFileReady: artifact => {
          patchAssistantMessage(assistantIndex, current => ({
            artifacts: mergeMessageArtifacts(current.artifacts || [], [artifact]),
            streamingStatus: '文件已生成，可下载'
          }))
        },
        onError: message => {
          patchAssistantMessage(assistantIndex, {
            content: message,
            isStreaming: false,
            streamingStatus: ''
          })
        },
        onDone: response => {
          sessionId.value = response.session_id
          if ((response.tool_calls || []).some(call => isTodoTool(call.tool || call.name))) {
            emit('todo-updated')
          }
          patchAssistantMessage(assistantIndex, current => ({
            type: response.status === 'need_clarification' ? 'clarification' : 'normal',
            artifacts: response.artifacts || [],
            missingFields: response.missing_fields || [],
            reasoning: current.reasoning || response.reasoning || '',
            content: response.answer || current.content || '',
            isStreaming: false,
            streamingStatus: ''
          }))
        }
      }
    )

    const finalMessage = messages.value[assistantIndex]
    if (!String(finalMessage.content || '').trim()) {
      if (finalResponse?.answer) {
        patchAssistantMessage(assistantIndex, {
          content: finalResponse.answer,
          isStreaming: false,
          streamingStatus: ''
        })
      } else if (String(finalMessage.reasoning || '').trim()) {
        patchAssistantMessage(assistantIndex, {
          content: '模型完成了思考，但没有返回正式回复。请换一种问法再试一次。',
          isStreaming: false,
          streamingStatus: ''
        })
      } else {
        patchAssistantMessage(assistantIndex, {
          content: '本次请求已经结束，但前端没有收到模型回复内容。请刷新页面后重试，或检查后端流式接口是否返回 token 事件。',
          isStreaming: false,
          streamingStatus: ''
        })
      }
    }
  } catch (err) {
    error.value = friendlyError(err)
    steps.value = ['请求后端失败，等待用户重试']
    patchAssistantMessage(assistantIndex, {
      content: error.value,
      isStreaming: false,
      streamingStatus: ''
    })
  } finally {
    loading.value = false
    saveCurrentSession()
  }
}

function sendQuickPrompt(text) {
  handleSend(text)
}

function retryLastMessage() {
  if (lastUserMessage.value) {
    handleSend(lastUserMessage.value)
  }
}

function startNewSession() {
  saveCurrentSession()
  const session = createLocalSession()
  sessions.value = [session, ...sessions.value].slice(0, MAX_SESSIONS)
  hydrateSession(session)
  refreshQuickPrompts()
  persistSessions()
}

function switchSession(localId) {
  if (loading.value || localId === activeLocalSessionId.value) return
  const nextSession = sessions.value.find(item => item.localId === localId)
  if (!nextSession) return
  saveCurrentSession()
  hydrateSession(nextSession)
  refreshQuickPrompts()
  persistSessions()
}

function renameSession(localId, title) {
  const session = sessions.value.find(item => item.localId === localId)
  if (!session) return
  session.title = title
  session.updatedAt = new Date().toISOString()
  persistSessions()
}

function initializeSessions() {
  const storedSessions = readStoredSessions()
  sessions.value = storedSessions.length
    ? storedSessions.map(normalizeSession)
    : [createLocalSession()]

  const storedActiveId = readActiveSessionId()
  const active = sessions.value.find(item => item.localId === storedActiveId) || sessions.value[0]
  hydrateSession(active)
  refreshQuickPrompts()
  persistSessions()
}

function refreshQuickPrompts() {
  quickPrompts.value = pickRandomItems(buildPromptCandidates(), 4)
}

function buildPromptCandidates() {
  const user = props.currentUser
  const visibleClassIds = getVisibleClassIds()
  const visibleClasses = props.classes.filter(item => visibleClassIds.includes(item.id))
  const currentClass = props.classes.find(item => item.id === user.classId)
  const primaryClassName = visibleClasses[0]?.name || currentClass?.name || '我的班级'
  const weatherText = [props.weather.city, props.weather.weather, props.weather.temperature]
    .filter(Boolean)
    .join(' ')
  const todayCourse = findCourseByOffset(0)
  const tomorrowCourse = findCourseByOffset(1)
  const randomCourse = pickRandomItems(getVisibleCourses(), 1)[0]
  const weatherQuestion = weatherText
    ? `结合${weatherText}，给我今天上课出行建议`
    : '结合今天的天气，给我上课出行建议'

  if (user.role === 'teacher' || user.role === 'admin') {
    return [
      `帮我看${primaryClassName}明天上午有哪些课`,
      `检查${primaryClassName}本周课表有没有冲突`,
      `给${primaryClassName}生成明天课程提醒`,
      `帮我汇总${primaryClassName}今天的课程安排`,
      `如果今天下雨，帮我写一段给${primaryClassName}学生的上课提醒`,
      `统计${primaryClassName}这周课程分布是否均衡`,
      `帮我找出${primaryClassName}最早的一节课`,
      `帮我整理${primaryClassName}今天需要注意的教室安排`,
      tomorrowCourse ? `明天${tomorrowCourse.courseName}课前需要提醒学生什么？` : `明天${primaryClassName}有没有课程安排？`,
      randomCourse ? `围绕${randomCourse.courseName}生成一条班级通知` : `帮我生成一条${primaryClassName}课程通知`
    ]
  }

  return [
    '今天我还有哪些课？',
    '明天上午我有没有课？',
    '帮我看看本周哪天课最多',
    weatherQuestion,
    `基于${primaryClassName}课表，帮我安排今天的学习计划`,
    '我下一节课是什么，在哪里上？',
    '帮我检查今天有没有连续课程',
    '如果我想复习两小时，今天适合安排在什么时候？',
    todayCourse ? `今天${todayCourse.courseName}上课前我需要准备什么？` : '今天没课的话，帮我安排自习计划',
    tomorrowCourse ? `明天${tomorrowCourse.courseName}之前我该怎么复习？` : '明天如果没课，帮我规划学习任务',
    randomCourse ? `帮我围绕${randomCourse.courseName}做一个复习计划` : '帮我生成一个通用学习计划'
  ]
}

function getVisibleCourses() {
  const visibleClassIds = getVisibleClassIds()
  return props.courses.filter(item => visibleClassIds.includes(item.classId))
}

function findCourseByOffset(dayOffset) {
  const targetDay = normalizeWeekdayIndex(new Date().getDay() + dayOffset)
  return getVisibleCourses()
    .filter(item => parseWeekday(item.weekday) === targetDay)
    .sort((left, right) => String(left.startTime || '').localeCompare(String(right.startTime || '')))[0]
}

function pickRandomItems(items, count) {
  const uniqueItems = [...new Set(items.filter(Boolean))]
  return uniqueItems
    .map(item => ({ item, sort: Math.random() }))
    .sort((left, right) => left.sort - right.sort)
    .slice(0, count)
    .map(entry => entry.item)
}

function createLocalSession(title = DEFAULT_SESSION_TITLE) {
  return {
    localId: createClientId(),
    title,
    agentSessionId: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    messages: [createWelcomeMessage()],
    steps: [],
    toolCalls: [],
    error: '',
    lastUserMessage: ''
  }
}

function normalizeSession(session) {
  const normalized = {
    localId: session.localId || createClientId(),
    title: session.title || DEFAULT_SESSION_TITLE,
    agentSessionId: session.agentSessionId || null,
    createdAt: session.createdAt || new Date().toISOString(),
    updatedAt: session.updatedAt || new Date().toISOString(),
    messages: Array.isArray(session.messages) && session.messages.length
      ? session.messages
      : [createWelcomeMessage()],
    steps: Array.isArray(session.steps) ? session.steps : [],
    toolCalls: Array.isArray(session.toolCalls) ? session.toolCalls : [],
    error: session.error || '',
    lastUserMessage: session.lastUserMessage || ''
  }

  return normalized
}

function hydrateSession(session) {
  activeLocalSessionId.value = session.localId
  sessionId.value = session.agentSessionId || null
  messages.value = cloneData(session.messages)
  steps.value = cloneData(session.steps)
  toolCalls.value = cloneData(session.toolCalls)
  error.value = session.error || ''
  lastUserMessage.value = session.lastUserMessage || ''
  traceOpen.value = false
}

function saveCurrentSession() {
  const session = activeSession.value
  if (!session) return
  session.agentSessionId = sessionId.value
  session.messages = cloneData(messages.value)
  session.steps = cloneData(steps.value)
  session.toolCalls = cloneData(toolCalls.value)
  session.error = error.value
  session.lastUserMessage = lastUserMessage.value
  session.updatedAt = new Date().toISOString()
  persistSessions()
}

function persistSessions() {
  try {
    localStorage.setItem(storageKey.value, JSON.stringify(sessions.value.slice(0, MAX_SESSIONS)))
    localStorage.setItem(`${storageKey.value}.active`, activeLocalSessionId.value)
  } catch {
    // localStorage 不可用时，会话仍在当前页面内可用。
  }
}

function readStoredSessions() {
  try {
    const raw = localStorage.getItem(storageKey.value)
    const parsed = JSON.parse(raw || '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function readActiveSessionId() {
  try {
    return localStorage.getItem(`${storageKey.value}.active`)
  } catch {
    return ''
  }
}

function createWelcomeMessage() {
  return createMessage(
    'assistant',
    'normal',
    `你好，${props.currentUser.name}。我是 CampusFlow 平台助手，会基于你的${roleLabel(props.currentUser.role)}权限和平台数据回答问题。`
  )
}

function ensureActiveSessionTitle(content) {
  const session = activeSession.value
  if (!session) return
  const title = String(session.title || '').trim()
  if (title && title !== DEFAULT_SESSION_TITLE) return
  session.title = toSessionTitle(content)
  session.updatedAt = new Date().toISOString()
  persistSessions()
}

function toSessionTitle(content) {
  const normalized = String(content).replace(/\s+/g, ' ').trim()
  if (!normalized) return DEFAULT_SESSION_TITLE
  return normalized.length > 18 ? `${normalized.slice(0, 18)}...` : normalized
}

function sessionMeta(session) {
  if (session.agentSessionId) return `ID ${shortId(session.agentSessionId)}`
  return formatSessionTime(session.updatedAt)
}

function formatSessionTime(value) {
  return dayjs(value).isValid() ? dayjs(value).format('MM-DD HH:mm') : '本地会话'
}

function shortId(value) {
  return String(value || '').slice(0, 8)
}

function cloneData(value) {
  return JSON.parse(JSON.stringify(value ?? null))
}

function createMessage(role, type, content, extra = {}) {
  return {
    id: createClientId(),
    role,
    type,
    content,
    createdAt: dayjs().format('HH:mm'),
    ...extra
  }
}

function createClientId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID()
  }
  return `local-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function patchAssistantMessage(index, patch) {
  const current = messages.value[index]
  if (!current) return
  const nextPatch = typeof patch === 'function' ? patch(current) : patch
  messages.value[index] = {
    ...current,
    ...nextPatch
  }
}

function appendStep(step) {
  if (!step || steps.value.includes(step)) return
  if (steps.value.length === 1 && steps.value[0] === '正在连接智能体...') {
    steps.value = [step]
    return
  }
  steps.value.push(step)
}

function friendlyError(err) {
  if (err.code === 'ECONNABORTED') return '后端响应超时，请稍后重试。'
  if (!navigator.onLine) return '当前网络不可用，请恢复连接后重试。'
  return '未能连接到智能体服务，请确认后端服务已启动。'
}

function roleLabel(role) {
  const map = {
    teacher: '教师',
    student: '学生',
    admin: '管理员'
  }
  return map[role] || '用户'
}

function buildUserContext() {
  return {
    user_id: backendUserId(props.currentUser),
    name: props.currentUser.name,
    role: props.currentUser.role,
    student_no: props.currentUser.studentNo || null,
    teacher_num: props.currentUser.teacherNo || null,
    class_id: props.currentUser.classId || null,
    class_ids: props.currentUser.classIds || []
  }
}

function backendUserId(user = {}) {
  return user.studentNo || user.teacherNo || user.username || user.id || ''
}

function isTodoTool(toolName = '') {
  return [
    'add_todo',
    'delete_todo',
    'query_todos_by_date',
    'query_user_todos',
    'update_todo',
    'update_todo_status',
    'batch_update_status',
    'batch_update_todo_status',
    'get_todo_stats'
  ].includes(toolName)
}

function buildPlatformContext() {
  return {
    classes: props.classes,
    students: props.students,
    courses: props.courses,
    weather: props.weather
  }
}

function buildAgentMessage(content) {
  return `${buildAgentPlatformContext()}\n\n用户问题：${content}`
}

function buildAgentPlatformContext() {
  const user = props.currentUser
  const currentClass = props.classes.find(item => item.id === user.classId)
  const visibleClassIds = getVisibleClassIds()
  const visibleStudents = props.students.filter(item => visibleClassIds.includes(item.classId))
  const visibleCourses = props.courses.filter(item => visibleClassIds.includes(item.classId))
  const ownCourses = user.role === 'student'
    ? props.courses.filter(item => item.classId === user.classId)
    : visibleCourses
  const contextLines = [
    '【CampusFlow平台上下文】',
    '说明：以下数据来自当前前端已加载的学校平台数据库，只用于回答用户问题。回答时不要复述本段说明。',
    `当前用户：${user.name}；角色：${roleLabel(user.role)}；学号：${user.studentNo || '无'}；教师编号：${user.teacherNo || '无'}；当前班级：${currentClass?.name || user.classId || '未分配'}`,
    `天气：${props.weather.weather || '未知'}；城市：${props.weather.city || '未知'}；温度：${props.weather.temperature || '未知'}；风力：${props.weather.wind || '未知'}。`
  ]

  if (user.role === 'student') {
    contextLines.push(`我的班级：${currentClass?.name || user.classId || '未分配'}`)
    contextLines.push(`我的课表：${formatCourseList(ownCourses)}`)
  } else {
    contextLines.push(`可管理班级：${formatClassList(props.classes.filter(item => visibleClassIds.includes(item.id)))}`)
    contextLines.push(`班级学生：${formatStudentList(visibleStudents)}`)
    contextLines.push(`平台课程：${formatCourseList(visibleCourses)}`)
  }

  return contextLines.join('\n')
}

function getVisibleClassIds() {
  const user = props.currentUser
  if (user.role === 'student') return [user.classId].filter(Boolean)
  if (Array.isArray(user.classIds) && user.classIds.length) return user.classIds
  return props.classes.map(item => item.id)
}

function formatClassList(classes) {
  if (!classes.length) return '暂无班级数据'
  return classes.map(item => `${item.name || item.id}`).join('、')
}

function formatStudentList(students) {
  if (!students.length) return '暂无学生数据'
  return limitItems(students, 40)
    .map(item => `${item.name}(${item.studentNo})/${item.classId}`)
    .join('；')
}

function formatCourseList(courses) {
  if (!courses.length) return '暂无课程数据'
  return limitItems(courses, 40)
    .map(item => {
      const className = props.classes.find(cls => cls.id === item.classId)?.name || item.classId || '未分班'
      return `${className}｜${item.weekday} ${item.startTime}-${item.endTime}｜${item.courseName}｜教师:${item.teacher}｜地点:${item.location}｜周次:${item.weeks || '未设置'}`
    })
    .join('；')
}

function limitItems(items, max) {
  return items.slice(0, max)
}

function mergeMessageArtifacts(current = [], next = []) {
  const merged = [...current]
  for (const artifact of next) {
    const key = messageArtifactKey(artifact)
    if (!merged.some(item => messageArtifactKey(item) === key)) {
      merged.push(artifact)
    }
  }
  return merged
}

function messageArtifactKey(artifact = {}) {
  if (artifact.type === 'file') return `file:${artifact.name || artifact.path || artifact.url}`
  return `${artifact.type}:${artifact.title || ''}`
}

function normalizeWeekdayIndex(index) {
  return ((index % 7) + 7) % 7
}

function parseWeekday(value) {
  const text = String(value || '').toLowerCase()
  if (/^(0|7)$/.test(text) || /(星期|周)?(日|天)|sun/.test(text)) return 0
  if (/^1$/.test(text) || /(星期|周)?一|mon/.test(text)) return 1
  if (/^2$/.test(text) || /(星期|周)?二|tue/.test(text)) return 2
  if (/^3$/.test(text) || /(星期|周)?三|wed/.test(text)) return 3
  if (/^4$/.test(text) || /(星期|周)?四|thu/.test(text)) return 4
  if (/^5$/.test(text) || /(星期|周)?五|fri/.test(text)) return 5
  if (/^6$/.test(text) || /(星期|周)?六|sat/.test(text)) return 6
  return -1
}
</script>
