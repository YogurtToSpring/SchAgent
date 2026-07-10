<template>
  <section class="todo-page module-page">
    <section class="module-toolbar content-panel">
      <div>
        <h2>待办事项</h2>
        <p>{{ pendingCount }} 项待处理，可安排未来任意日期</p>
      </div>
      <form class="quick-create" @submit.prevent="submitTodo">
        <input v-model="draft.title" placeholder="新增待办，例如 复习数据库第三章" />
        <input v-model="draft.date" type="date" :min="today()" title="选择未来的待办日期" />
        <select v-model="draft.priority">
          <option value="high">高优先级</option>
          <option value="medium">中优先级</option>
          <option value="low">低优先级</option>
        </select>
        <button class="primary-action compact" type="submit" :disabled="loading">新增</button>
      </form>
    </section>

    <section class="module-grid two-columns">
      <aside class="content-panel side-filter">
        <button
          v-for="item in filters"
          :key="item.key"
          type="button"
          :class="{ active: activeFilter === item.key }"
          @click="activeFilter = item.key"
        >
          <span>{{ item.label }}</span>
          <strong>{{ countByFilter(item.key) }}</strong>
        </button>
      </aside>

      <section class="content-panel task-list">
        <article
          v-for="todo in filteredTodos"
          :key="todo.id"
          class="task-item"
          :class="{ done: todo.status === 'done' }"
        >
          <button class="task-check" type="button" @click="$emit('toggle-todo', todo.id)">
            {{ todo.status === 'done' ? '✓' : '' }}
          </button>
          <div>
            <strong>{{ todo.title }}</strong>
            <span>{{ todoDate(todo) }} · {{ todo.category }} · {{ todo.source }}</span>
            <p v-if="todo.note">{{ todo.note }}</p>
          </div>
          <div class="task-actions">
            <small :class="`priority ${todo.priority}`">{{ priorityText(todo.priority) }}</small>
            <button class="ghost-action compact" type="button" @click="$emit('delete-todo', todo.id)">删除</button>
          </div>
        </article>

        <div v-if="loading" class="empty-state compact">正在同步待办</div>
        <div v-else-if="!filteredTodos.length" class="empty-state compact">暂无待办</div>
      </section>
    </section>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'

const props = defineProps({
  todos: {
    type: Array,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['add-todo', 'toggle-todo', 'delete-todo'])

const activeFilter = ref('all')
const draft = reactive({
  title: '',
  date: today(),
  priority: 'medium'
})

const filters = [
  { key: 'all', label: '全部待办' },
  { key: 'today', label: '今天' },
  { key: 'week', label: '本周' },
  { key: 'upcoming', label: '未来三个月' },
  { key: 'high', label: '高优先级' },
  { key: 'done', label: '已完成' }
]

const pendingCount = computed(() => props.todos.filter(item => item.status !== 'done').length)

const filteredTodos = computed(() => {
  const list = [...props.todos].sort((left, right) => todoDate(left).localeCompare(todoDate(right)))
  if (activeFilter.value === 'done') return list.filter(item => item.status === 'done')
  if (activeFilter.value === 'high') return list.filter(item => item.priority === 'high' && item.status !== 'done')
  if (activeFilter.value === 'today') return list.filter(item => todoDate(item) === today() && item.status !== 'done')
  if (activeFilter.value === 'week') return list.filter(item => isWithinThisWeek(todoDate(item)) && item.status !== 'done')
  if (activeFilter.value === 'upcoming') return list.filter(item => isWithinNextMonths(todoDate(item), 3) && item.status !== 'done')
  return list.filter(item => item.status !== 'done')
})

function submitTodo() {
  if (!draft.title.trim()) return
  emit('add-todo', {
    title: draft.title.trim(),
    date: draft.date || today(),
    dueDate: draft.date || today(),
    category: '个人',
    source: '手动创建',
    priority: draft.priority,
    note: ''
  })
  draft.title = ''
}

function countByFilter(key) {
  if (key === 'done') return props.todos.filter(item => item.status === 'done').length
  if (key === 'high') return props.todos.filter(item => item.priority === 'high' && item.status !== 'done').length
  if (key === 'today') return props.todos.filter(item => todoDate(item) === today() && item.status !== 'done').length
  if (key === 'week') return props.todos.filter(item => isWithinThisWeek(todoDate(item)) && item.status !== 'done').length
  if (key === 'upcoming') return props.todos.filter(item => isWithinNextMonths(todoDate(item), 3) && item.status !== 'done').length
  return props.todos.filter(item => item.status !== 'done').length
}

function todoDate(todo) {
  return todo?.date || todo?.dueDate || ''
}

function priorityText(priority) {
  const map = {
    high: '高',
    medium: '中',
    low: '低'
  }
  return map[priority] || '中'
}

function today() {
  const date = new Date()
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function isWithinThisWeek(value) {
  if (!value) return false
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return false
  const now = new Date()
  const day = now.getDay() || 7
  const start = new Date(now)
  start.setDate(now.getDate() - day + 1)
  start.setHours(0, 0, 0, 0)
  const end = new Date(start)
  end.setDate(start.getDate() + 7)
  return date >= start && date < end
}

function isWithinNextMonths(value, monthCount) {
  if (!value) return false
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return false
  const start = new Date()
  start.setHours(0, 0, 0, 0)
  const end = new Date(start)
  end.setMonth(end.getMonth() + monthCount)
  end.setHours(23, 59, 59, 999)
  return date >= start && date <= end
}
</script>
