<template>
  <section class="todo-page module-page">
    <section class="module-toolbar content-panel">
      <div>
        <h2>待办事项</h2>
        <p>{{ pendingCount }} 项待处理</p>
      </div>
      <form class="quick-create" @submit.prevent="submitTodo">
        <input v-model="draft.title" placeholder="新增待办，例如 复习数据库第三章" />
        <input v-model="draft.dueDate" placeholder="截止时间" />
        <button class="primary-action compact" type="submit">新增</button>
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
            <span>{{ todo.dueDate }} · {{ todo.category }} · {{ todo.source }}</span>
            <p v-if="todo.note">{{ todo.note }}</p>
          </div>
          <small :class="`priority ${todo.priority}`">{{ priorityText(todo.priority) }}</small>
        </article>

        <div v-if="!filteredTodos.length" class="empty-state compact">暂无待办</div>
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
  }
})

const emit = defineEmits(['add-todo', 'toggle-todo'])

const activeFilter = ref('today')
const draft = reactive({
  title: '',
  dueDate: '今天 22:00'
})

const filters = [
  { key: 'today', label: '今天' },
  { key: 'week', label: '本周' },
  { key: 'study', label: '学习' },
  { key: 'library', label: '图书馆' },
  { key: 'done', label: '已完成' }
]

const pendingCount = computed(() => props.todos.filter(item => item.status !== 'done').length)

const filteredTodos = computed(() => {
  const list = [...props.todos]
  if (activeFilter.value === 'done') return list.filter(item => item.status === 'done')
  if (activeFilter.value === 'study') return list.filter(item => item.category === '学习' || item.category === '课程')
  if (activeFilter.value === 'library') return list.filter(item => item.category === '图书馆')
  if (activeFilter.value === 'today') return list.filter(item => item.dueDate.includes('今天') && item.status !== 'done')
  return list.filter(item => item.status !== 'done')
})

function submitTodo() {
  if (!draft.title.trim()) return
  emit('add-todo', {
    title: draft.title.trim(),
    dueDate: draft.dueDate.trim() || '今天',
    category: '学习',
    source: '手动创建',
    priority: 'medium',
    note: ''
  })
  draft.title = ''
}

function countByFilter(key) {
  if (key === 'done') return props.todos.filter(item => item.status === 'done').length
  if (key === 'study') return props.todos.filter(item => item.category === '学习' || item.category === '课程').length
  if (key === 'library') return props.todos.filter(item => item.category === '图书馆').length
  if (key === 'today') return props.todos.filter(item => item.dueDate.includes('今天') && item.status !== 'done').length
  return props.todos.filter(item => item.status !== 'done').length
}

function priorityText(priority) {
  const map = {
    high: '高',
    medium: '中',
    low: '低'
  }
  return map[priority] || '中'
}
</script>
