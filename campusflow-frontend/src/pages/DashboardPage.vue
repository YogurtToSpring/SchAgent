<template>
  <section class="dashboard-page">
    <div class="overview-grid">
      <article class="metric-card weather-card">
        <span>{{ weather.city || '武汉' }}</span>
        <strong>{{ weather.weather || '暂无数据' }}</strong>
        <p>{{ weather.temperature || '--' }} · {{ weather.wind || '--' }}</p>
      </article>

      <article v-if="!isAdmin" class="metric-card action-card" @click="$emit('navigate', 'schedule')">
        <span>下一节课</span>
        <strong>{{ nextCourse?.startTime || '-' }}</strong>
        <p>{{ nextCourse ? `${nextCourse.courseName} · ${nextCourse.location}` : '今日暂无课程' }}</p>
      </article>

      <article v-else class="metric-card action-card" @click="$emit('navigate', 'classes')">
        <span>平台对象</span>
        <strong>{{ classes.length }}</strong>
        <p>{{ students.length }} 名学生 · {{ courses.length }} 条课程</p>
      </article>

      <article class="metric-card action-card" @click="$emit('navigate', 'todos')">
        <span>待办</span>
        <strong>{{ pendingTodos.length }}</strong>
        <p>{{ topTodo?.title || '暂无待处理事项' }}</p>
      </article>

      <article class="metric-card action-card" @click="$emit('navigate', 'notifications')">
        <span>未读通知</span>
        <strong>{{ unreadNotifications.length }}</strong>
        <p>{{ unreadNotifications[0]?.title || '暂无未读消息' }}</p>
      </article>
    </div>

    <section class="dashboard-grid">
      <section v-if="!isAdmin" class="content-panel">
        <div class="section-heading">
          <div>
            <h2>今日课程</h2>
            <p>{{ currentWeekdayLabel }}</p>
          </div>
          <button class="ghost-action" type="button" @click="$emit('navigate', 'schedule')">查看课表</button>
        </div>

        <div v-if="todayCourses.length" class="today-course-list">
          <article v-for="course in todayCourses" :key="course.id" class="today-course-item">
            <div>
              <strong>{{ course.courseName }}</strong>
              <span>{{ course.startTime }}-{{ course.endTime }} · {{ course.location }}</span>
            </div>
            <small>{{ course.teacher }} · {{ className(course.classId) }}</small>
          </article>
        </div>
        <div v-else class="empty-state compact">今日暂无课程</div>
      </section>

      <section v-else class="content-panel">
        <div class="section-heading">
          <div>
            <h2>平台概况</h2>
            <p>账号、班级、课程与成绩数据</p>
          </div>
          <button class="ghost-action" type="button" @click="$emit('navigate', 'classes')">进入管理</button>
        </div>

        <div class="admin-overview-list">
          <article>
            <span>班级</span>
            <strong>{{ classes.length }}</strong>
          </article>
          <article>
            <span>学生</span>
            <strong>{{ students.length }}</strong>
          </article>
          <article>
            <span>课程</span>
            <strong>{{ courses.length }}</strong>
          </article>
          <article>
            <span>成绩记录</span>
            <strong>{{ grades.length }}</strong>
          </article>
        </div>
      </section>

      <section class="content-panel">
        <div class="section-heading">
          <div>
            <h2>待办事项</h2>
            <p>{{ pendingTodos.length }} 项待处理</p>
          </div>
          <button class="ghost-action" type="button" @click="$emit('navigate', 'todos')">进入待办</button>
        </div>

        <div class="compact-list">
          <article v-for="todo in pendingTodos.slice(0, 4)" :key="todo.id">
            <strong>{{ todo.title }}</strong>
            <span>{{ todo.dueDate }} · {{ todo.category }}</span>
          </article>
          <div v-if="!pendingTodos.length" class="empty-state compact">暂无待办</div>
        </div>
      </section>

      <section class="content-panel">
        <div class="section-heading">
          <div>
            <h2>{{ currentUser.role === 'teacher' ? '教学工作' : currentUser.role === 'admin' ? '系统工作' : '学习状态' }}</h2>
            <p>{{ roleSummary }}</p>
          </div>
        </div>

        <div class="workbench-actions">
          <button v-for="action in workbenchActions" :key="action.view" type="button" @click="$emit('navigate', action.view)">
            {{ action.label }}
          </button>
        </div>
      </section>

      <section class="content-panel">
        <div class="section-heading">
          <div>
            <h2>最近通知</h2>
            <p>{{ unreadNotifications.length }} 条未读</p>
          </div>
          <button class="ghost-action" type="button" @click="$emit('navigate', 'notifications')">消息中心</button>
        </div>

        <div class="compact-list">
          <article v-for="notice in notifications.slice(0, 4)" :key="notice.id">
            <strong>{{ notice.title }}</strong>
            <span>{{ notice.type }} · {{ notice.time }}</span>
          </article>
        </div>
      </section>
    </section>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentUser: {
    type: Object,
    required: true
  },
  classes: {
    type: Array,
    required: true
  },
  students: {
    type: Array,
    required: true
  },
  courses: {
    type: Array,
    required: true
  },
  weather: {
    type: Object,
    required: true
  },
  todos: {
    type: Array,
    default: () => []
  },
  notifications: {
    type: Array,
    default: () => []
  },
  reservations: {
    type: Array,
    default: () => []
  },
  grades: {
    type: Array,
    default: () => []
  }
})

defineEmits(['navigate'])

const weekdayLabels = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
const todayIndex = new Date().getDay()
const currentWeekdayLabel = weekdayLabels[todayIndex]
const isAdmin = computed(() => props.currentUser.role === 'admin')

const visibleClassIds = computed(() => {
  if (props.currentUser.role === 'student') return [props.currentUser.classId].filter(Boolean)
  if (Array.isArray(props.currentUser.classIds) && props.currentUser.classIds.length) return props.currentUser.classIds
  return props.classes.map(item => item.id)
})

const visibleCourses = computed(() => {
  if (props.currentUser.role === 'admin') return props.courses
  if (props.currentUser.role === 'teacher') {
    return props.courses.filter(course => isTeacherCourse(course))
  }
  const studentNo = props.currentUser.studentNo || props.currentUser.username
  return props.courses.filter(course => {
    if (Array.isArray(course.studentNos)) return course.studentNos.includes(studentNo)
    return visibleClassIds.value.includes(course.classId)
  })
})

const todayCourses = computed(() => {
  return visibleCourses.value
    .filter(item => normalizeWeekday(item.weekday) === todayIndex)
    .sort((left, right) => String(left.startTime || '').localeCompare(String(right.startTime || '')))
})

const nextCourse = computed(() => todayCourses.value[0] || null)

const pendingTodos = computed(() => props.todos.filter(item => item.status !== 'done'))

const topTodo = computed(() => pendingTodos.value[0] || null)

const unreadNotifications = computed(() => props.notifications.filter(item => item.status === 'unread'))

const roleSummary = computed(() => {
  if (props.currentUser.role === 'teacher') return `${visibleCourses.value.length} 门课程 · ${visibleCourseStudents.value.length} 名学生`
  if (props.currentUser.role === 'admin') return `${props.classes.length} 个班级 · ${props.courses.length} 条课程`
  const average = props.grades.length
    ? Math.round(props.grades.reduce((sum, item) => sum + item.score, 0) / props.grades.length)
    : '-'
  return `平均分 ${average} · ${props.reservations.length} 条预约`
})

const workbenchActions = computed(() => {
  if (props.currentUser.role === 'admin') {
    return [
      { view: 'classes', label: '班级与课程' },
      { view: 'admin', label: '管理后台' },
      { view: 'assistant', label: '问助手' }
    ]
  }
  if (props.currentUser.role === 'teacher') {
    return [
      { view: 'classes', label: '班级与课程' },
      { view: 'schedule', label: '教学课表' },
      { view: 'forum', label: '论坛' },
      { view: 'assistant', label: '问助手' }
    ]
  }
  return [
    { view: 'grades', label: '成绩' },
    { view: 'course-selection', label: '学生选课' },
    { view: 'library', label: '图书馆' },
    { view: 'forum', label: '论坛' },
    { view: 'assistant', label: '问助手' }
  ]
})

function className(classId) {
  return props.classes.find(item => item.id === classId)?.name || classId || '未分班'
}

const visibleCourseStudents = computed(() => {
  const classIds = new Set(visibleCourses.value.map(course => course.classId).filter(Boolean))
  return props.students.filter(student => classIds.has(student.classId))
})

function isTeacherCourse(course) {
  const teacherNo = props.currentUser.teacherNo || props.currentUser.username
  const teacherName = props.currentUser.name
  return course.teacherNo === teacherNo || course.teacherNum === teacherNo || course.teacher === teacherName
}

function normalizeWeekday(value) {
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
