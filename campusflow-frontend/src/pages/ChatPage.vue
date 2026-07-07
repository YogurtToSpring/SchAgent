<template>
  <section class="assistant-page">
    <SessionHeader
      :session-id="sessionId"
      :loading="loading"
      @new-session="startNewSession"
    />

    <section class="workspace">
      <aside class="quick-panel" aria-label="快捷问题">
        <div class="panel-title">快捷问题</div>
        <button
          v-for="item in quickPrompts"
          :key="item"
          class="quick-prompt"
          type="button"
          @click="sendQuickPrompt(item)"
        >
          {{ item }}
        </button>
      </aside>

      <section class="chat-panel" aria-label="对话区">
        <ChatWindow
          :messages="messages"
          :loading="loading"
          @quick-reply="sendQuickPrompt"
        />

        <div v-if="error" class="network-alert" role="alert">
          <div>
            <strong>连接失败</strong>
            <span>{{ error }}</span>
          </div>
          <button type="button" @click="retryLastMessage">重试</button>
        </div>

        <ChatInput :disabled="loading" @send="handleSend" />
      </section>

      <ToolTrace
        :steps="steps"
        :tool-calls="toolCalls"
        :status="currentStatus"
      />
    </section>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import dayjs from 'dayjs'
import { sendMessage } from '../api/chat'
import ChatInput from '../components/ChatInput.vue'
import ChatWindow from '../components/ChatWindow.vue'
import SessionHeader from '../components/SessionHeader.vue'
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

const quickPrompts = computed(() => {
  if (props.currentUser.role === 'teacher') {
    return [
      '帮我看软件工程1班明天上午有哪些课',
      '检查软件工程1班周三有没有课表冲突',
      '给软件工程1班生成明天课程提醒',
      '今天下雨的话，提醒学生上课出行注意事项'
    ]
  }

  return [
    '明天上午我有没有课？',
    '明天上课如果下雨，适合骑车吗？',
    '帮我安排今天的学习计划',
    '帮我看看有没有课'
  ]
})

const sessionId = ref(null)
const messages = ref([
  {
    id: crypto.randomUUID(),
    role: 'assistant',
    type: 'normal',
    content: `你好，${props.currentUser.name}。我是 CampusFlow 平台助手，会基于你的${props.currentUser.role === 'teacher' ? '教师权限' : '学生课表'}回答问题。`,
    createdAt: dayjs().format('HH:mm')
  }
])
const steps = ref([])
const toolCalls = ref([])
const loading = ref(false)
const error = ref('')
const lastUserMessage = ref('')
const currentStatus = computed(() => {
  if (loading.value) return 'running'
  if (error.value) return 'error'
  const last = messages.value[messages.value.length - 1]
  return last?.type === 'clarification' ? 'need_clarification' : 'idle'
})

async function handleSend(text) {
  const content = text.trim()
  if (!content || loading.value) return

  error.value = ''
  lastUserMessage.value = content

  messages.value.push(createMessage('user', 'normal', content))
  loading.value = true
  steps.value = ['正在理解任务...']
  toolCalls.value = []

  try {
    const response = await sendMessage({
      session_id: sessionId.value,
      message: content,
      user_context: buildUserContext(),
      platform_context: buildPlatformContext()
    })

    sessionId.value = response.session_id
    steps.value = response.steps || []
    toolCalls.value = response.tool_calls || []

    const type = response.status === 'need_clarification' ? 'clarification' : 'normal'
    messages.value.push(
      createMessage('assistant', type, response.answer, {
        artifacts: response.artifacts || [],
        missingFields: response.missing_fields || []
      })
    )
  } catch (err) {
    error.value = friendlyError(err)
    steps.value = ['请求后端失败，等待用户重试']
  } finally {
    loading.value = false
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
  sessionId.value = null
  steps.value = []
  toolCalls.value = []
  error.value = ''
  lastUserMessage.value = ''
  messages.value = [
    createMessage(
      'assistant',
      'normal',
      `新的会话已创建。当前身份是${props.currentUser.role === 'teacher' ? '教师管理员' : '普通学生'}，你可以继续提问课程、班级、天气或学习计划。`
    )
  ]
}

function createMessage(role, type, content, extra = {}) {
  return {
    id: crypto.randomUUID(),
    role,
    type,
    content,
    createdAt: dayjs().format('HH:mm'),
    ...extra
  }
}

function friendlyError(err) {
  if (err.code === 'ECONNABORTED') return '后端响应超时，请稍后重试。'
  if (!navigator.onLine) return '当前网络不可用，请恢复连接后重试。'
  return '未能连接到智能体服务，请确认后端服务已启动。'
}

function buildUserContext() {
  return {
    user_id: props.currentUser.id,
    name: props.currentUser.name,
    role: props.currentUser.role,
    class_id: props.currentUser.classId || null,
    class_ids: props.currentUser.classIds || []
  }
}

function buildPlatformContext() {
  return {
    classes: props.classes,
    students: props.students,
    courses: props.courses,
    weather: props.weather
  }
}
</script>
