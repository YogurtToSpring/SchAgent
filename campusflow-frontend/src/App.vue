<template>
  <main v-if="restoringSession" class="login-page">
    <section class="login-panel">
      <h2>正在恢复登录状态</h2>
      <p>正在读取本地会话并同步平台数据。</p>
    </section>
  </main>

  <LoginPage v-else-if="!currentUser" @login="handleLogin" />

  <PlatformLayout
    v-else
    :current-user="currentUser"
    :active-view="activeView"
    @navigate="handleNavigate"
    @logout="logout"
  >
    <DashboardPage
      v-show="activeView === 'dashboard'"
      :current-user="currentUser"
      :classes="classes"
      :students="students"
      :courses="courses"
      :weather="weather"
      :todos="todos"
      :notifications="visibleNotifications"
      :reservations="reservations"
      :grades="grades"
      @navigate="handleNavigate"
    />

    <ProfilePage
      v-show="activeView === 'profile'"
      :current-user="currentUser"
      :classes="classes"
    />

    <TodoPage
      v-show="activeView === 'todos'"
      :todos="todos"
      :loading="todoLoading"
      @add-todo="addTodo"
      @toggle-todo="toggleTodo"
      @delete-todo="deleteTodo"
    />

    <ClassAdminPage
      v-if="currentUser.role === 'admin' || currentUser.role === 'teacher'"
      v-show="activeView === 'classes'"
      :classes="classes"
      :students="students"
      :teachers="teachers"
      :rooms="rooms"
      :courses="courses"
      :grades="grades"
      :current-user="currentUser"
      :student-import-result="studentImportResult"
      @add-class="addClass"
      @assign-student="assignStudent"
      @add-course="addCourse"
      @import-students="importStudents"
      @save-grade="saveGrade"
      @send-notification="sendNotification"
    />

    <SchedulePage
      v-show="activeView === 'schedule'"
      :current-user="currentUser"
      :classes="classes"
      :courses="courses"
    />

    <GradesPage
      v-show="activeView === 'grades'"
      :current-user="currentUser"
      :grades="grades"
      :courses="courses"
      :students="students"
      :summary="gradeSummary"
      :loading="gradeLoading"
      @save-grade="saveGrade"
      @refresh-grades="refreshGrades"
    />

    <LibraryPage
      v-show="activeView === 'library'"
      :seats="librarySeats"
      :reservations="reservations"
      @reserve-seat="reserveSeat"
      @add-todo="addTodo"
    />

    <ForumPage
      v-show="activeView === 'forum'"
      :current-user="currentUser"
      :posts="forumPosts"
      @add-post="addPost"
      @review-post="reviewPost"
    />

    <NotificationsPage
      v-show="activeView === 'notifications'"
      :notifications="visibleNotifications"
      @mark-all-read="markAllNotificationsRead"
      @open-notice="openNotice"
    />

    <FileCenterPage
      v-show="activeView === 'files'"
      :files="visibleFiles"
      @refresh-files="refreshFiles"
    />

    <ChatPage
      v-show="activeView === 'assistant'"
      :current-user="currentUser"
      :classes="classes"
      :students="students"
      :courses="courses"
      :weather="weather"
      @todo-updated="refreshTodos"
    />

    <AdminCenterPage
      v-if="currentUser.role === 'admin'"
      v-show="activeView === 'admin'"
      :classes="classes"
      :students="students"
      :courses="courses"
      :posts="forumPosts"
      :logs="systemLogs"
      @navigate="handleNavigate"
    />

    <div v-if="platformError" class="platform-alert" role="alert">
      <strong>平台数据提示</strong>
      <span>{{ platformError }}</span>
    </div>
  </PlatformLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import AdminCenterPage from './pages/AdminCenterPage.vue'
import ChatPage from './pages/ChatPage.vue'
import ClassAdminPage from './pages/ClassAdminPage.vue'
import DashboardPage from './pages/DashboardPage.vue'
import FileCenterPage from './pages/FileCenterPage.vue'
import ForumPage from './pages/ForumPage.vue'
import GradesPage from './pages/GradesPage.vue'
import LibraryPage from './pages/LibraryPage.vue'
import LoginPage from './pages/LoginPage.vue'
import NotificationsPage from './pages/NotificationsPage.vue'
import ProfilePage from './pages/ProfilePage.vue'
import SchedulePage from './pages/SchedulePage.vue'
import TodoPage from './pages/TodoPage.vue'
import PlatformLayout from './components/PlatformLayout.vue'
import {
  cloneData,
  initialClasses,
  initialCourses,
  initialStudents,
  weatherSnapshot
} from './data/platformData'
import {
  initialFiles,
  initialForumPosts,
  initialGrades,
  initialLibrarySeats,
  initialNotifications,
  initialReservations,
  initialSystemLogs,
  initialTodos
} from './data/campusModules'
import {
  createTodoItem,
  createClass,
  createCourse,
  deleteTodoItem,
  enrollStudent,
  loadGradesForUser,
  loadRealtimeWeather,
  loadPlatformSnapshot,
  loadTodosForUser,
  registerStudentAccount,
  saveGradeRecord,
  updateTodoItemStatus,
  updateStudentClass
} from './api/platform'
import { listAgentFiles } from './api/files'

const SESSION_STORAGE_KEY = 'campusflow.currentUser'

const currentUser = ref(null)
const activeView = ref('dashboard')
const classes = ref(cloneData(initialClasses))
const students = ref(cloneData(initialStudents))
const teachers = ref([])
const courses = ref(cloneData(initialCourses))
const rooms = ref([])
const weather = ref(cloneData(weatherSnapshot))
const todos = ref(cloneData(initialTodos))
const grades = ref(cloneData(initialGrades))
const gradeSummary = ref(null)
const librarySeats = ref(cloneData(initialLibrarySeats))
const reservations = ref(cloneData(initialReservations))
const forumPosts = ref(cloneData(initialForumPosts))
const notifications = ref(cloneData(initialNotifications))
const files = ref(cloneData(initialFiles))
const systemLogs = ref(cloneData(initialSystemLogs))
const platformError = ref('')
const todoLoading = ref(false)
const gradeLoading = ref(false)
const studentImportResult = ref(null)
const restoringSession = ref(true)

const visibleNotifications = computed(() => {
  if (!currentUser.value) return []
  return notifications.value.filter(item => canCurrentUserSeeItem(item))
})

const visibleFiles = computed(() => {
  if (!currentUser.value) return []
  return files.value.filter(item => canCurrentUserSeeItem(item))
})

onMounted(() => {
  restoreLoginSession()
})

async function handleLogin(user) {
  platformError.value = ''
  try {
    const snapshot = await loadPlatformSnapshot()
    applyPlatformSnapshot(snapshot)
    currentUser.value = hydrateUser(user, snapshot)
  } catch (error) {
    currentUser.value = user
    platformError.value = '后端平台数据暂时不可用，当前使用本地缓存数据。'
  }
  saveLoginSession(currentUser.value)
  await Promise.allSettled([refreshTodos(), refreshGrades()])
  refreshWeather()
  refreshFiles()
  activeView.value = 'dashboard'
}

function handleNavigate(view) {
  if (!canAccessView(view)) {
    activeView.value = 'dashboard'
    return
  }
  activeView.value = view
  if (view === 'todos') refreshTodos()
  if (view === 'grades' || view === 'classes') refreshGrades()
}

function logout() {
  currentUser.value = null
  activeView.value = 'dashboard'
  platformError.value = ''
  localStorage.removeItem(SESSION_STORAGE_KEY)
}

async function addTodo(payload) {
  const userId = backendUserId(currentUser.value)
  if (!userId) return

  try {
    const todo = await createTodoItem(userId, {
      ...payload,
      date: toBackendDate(payload.date || payload.dueDate)
    })
    todos.value.unshift(todo)
    platformError.value = ''
  } catch (error) {
    platformError.value = '新增待办失败，请确认后端待办接口可用且日期格式正确。'
  }
}

async function toggleTodo(todoId) {
  const todo = todos.value.find(item => item.id === todoId)
  if (!todo) return
  const nextStatus = todo.status === 'done' ? 'pending' : 'done'
  try {
    const updated = await updateTodoItemStatus(todo.backendId || todo.id, nextStatus)
    Object.assign(todo, updated)
    platformError.value = ''
  } catch (error) {
    platformError.value = '更新待办状态失败，请确认后端服务已启动。'
  }
}

async function deleteTodo(todoId) {
  const todo = todos.value.find(item => item.id === todoId)
  if (!todo) return
  try {
    await deleteTodoItem(todo.backendId || todo.id)
    todos.value = todos.value.filter(item => item.id !== todoId)
    platformError.value = ''
  } catch (error) {
    platformError.value = '删除待办失败，请稍后重试。'
  }
}

function reserveSeat(payload) {
  reservations.value.unshift({
    id: `res-${Date.now()}`,
    ...payload
  })
  const seatNo = payload.target.split(' ').pop()
  const seat = librarySeats.value.find(item => item.seatNo === seatNo)
  if (seat) seat.status = 'reserved'
}

function addPost(payload) {
  forumPosts.value.unshift({
    id: `post-${Date.now()}`,
    ...payload
  })
  notifications.value.unshift({
    id: `notice-${Date.now()}`,
    type: '论坛互动',
    title: payload.status === 'review' ? '帖子已提交审核' : '帖子已发布',
    time: '刚刚',
    status: 'unread',
    link: 'forum',
    ownerId: backendUserId(currentUser.value),
    audienceRoles: [currentUser.value?.role].filter(Boolean)
  })
}

function reviewPost(postId) {
  const post = forumPosts.value.find(item => item.id === postId)
  if (!post) return
  post.status = 'published'
}

function markAllNotificationsRead() {
  const visibleIds = new Set(visibleNotifications.value.map(item => item.id))
  notifications.value = notifications.value.map(item => ({
    ...item,
    status: visibleIds.has(item.id) ? 'read' : item.status
  }))
}

function openNotice(notice) {
  const target = notifications.value.find(item => item.id === notice.id)
  if (target) target.status = 'read'
  if (notice.link && canAccessView(notice.link)) activeView.value = notice.link
}

function sendNotification(payload) {
  const targetLabel = payload.type === 'course' ? '课程通知' : '班级通知'
  notifications.value.unshift({
    id: `notice-${Date.now()}`,
    type: targetLabel,
    title: payload.title,
    content: payload.content,
    time: '刚刚',
    status: 'unread',
    link: payload.type === 'course' ? 'schedule' : 'notifications',
    classId: payload.classId,
    courseId: payload.courseId,
    ownerId: backendUserId(currentUser.value),
    audienceRoles: ['student']
  })
  platformError.value = '通知已发送。'
}

async function addClass(payload) {
  try {
    const masterId = payload.masterId || payload.teacherNo || payload.headTeacherNo || teachers.value[0]?.teacherNo || ''
    await createClass({
      ...payload,
      classId: payload.classId || payload.id || payload.name,
      teacherNo: masterId,
      masterId
    })
    await refreshPlatformData()
    platformError.value = ''
  } catch (error) {
    platformError.value = '创建班级失败，请确认班级编号未重复、班主任教师编号存在且后端服务可用。'
  }
}

async function assignStudent({ studentId, classId }) {
  const student = students.value.find(item => item.id === studentId)
  if (!student) return

  try {
    await updateStudentClass(student.backendId || student.id, classId)
    student.classId = classId
    student.raw = {
      ...(student.raw || {}),
      Cls: classId
    }
    ensureClassExists(classId)
    await refreshPlatformData()
    platformError.value = ''
  } catch (error) {
    platformError.value = '调整学生班级失败，请确认后端服务已启动。'
    return
  }

  if (student?.userId && currentUser.value?.id === student.userId) {
    currentUser.value = {
      ...currentUser.value,
      classId
    }
    saveLoginSession(currentUser.value)
  }
}

async function addCourse(payload) {
  try {
    await createCourse(payload)
    const targetStudents = students.value.filter(student => student.classId === payload.classId)

    await Promise.all(
      targetStudents.map(student =>
        enrollStudent(payload.courseId, student.studentNo).catch(() => null)
      )
    )

    await refreshPlatformData()
    platformError.value = ''
  } catch (error) {
    platformError.value = '添加课程失败，请检查课程编号是否重复、教室是否存在、后端服务是否可用。'
  }
}

async function importStudents(rows) {
  studentImportResult.value = null
  const result = {
    success: 0,
    failed: 0,
    messages: []
  }

  for (const row of rows) {
    try {
      await registerStudentAccount(row)
      result.success += 1
      result.messages.push(`${row.studentNo} ${row.name} 导入成功`)
    } catch (error) {
      result.failed += 1
      const detail = error?.response?.data?.detail || '导入失败'
      result.messages.push(`${row.studentNo || '未知学号'} ${row.name || ''}：${detail}`)
    }
  }

  studentImportResult.value = result
  await refreshPlatformData().catch(() => null)
}

async function saveGrade(payload) {
  try {
    await saveGradeRecord(payload)
    await refreshGrades()
    platformError.value = ''
  } catch (error) {
    platformError.value = '保存成绩失败，请确认课程、学生和学期信息正确。'
  }
}

async function refreshPlatformData() {
  const snapshot = await loadPlatformSnapshot()
  applyPlatformSnapshot(snapshot)
  if (currentUser.value) {
    currentUser.value = hydrateUser(currentUser.value, snapshot)
    saveLoginSession(currentUser.value)
  }
}

function applyPlatformSnapshot(snapshot) {
  classes.value = snapshot.classes.length ? snapshot.classes : cloneData(initialClasses)
  students.value = snapshot.students.length ? snapshot.students : cloneData(initialStudents)
  teachers.value = snapshot.teachers || []
  courses.value = snapshot.courses.length ? snapshot.courses : cloneData(initialCourses)
  rooms.value = snapshot.rooms || []
}

async function refreshTodos() {
  if (!currentUser.value) return
  todoLoading.value = true
  try {
    todos.value = await loadTodosForUser(currentUser.value)
  } catch (error) {
    platformError.value = '待办数据暂时不可用，当前保留本地显示。'
  } finally {
    todoLoading.value = false
  }
}

async function refreshGrades() {
  if (!currentUser.value) return
  gradeLoading.value = true
  try {
    const result = await loadGradesForUser(currentUser.value, {
      courses: courses.value,
      students: students.value
    })
    grades.value = result.grades
    gradeSummary.value = result.summary
  } catch (error) {
    platformError.value = '成绩数据暂时不可用，当前保留本地显示。'
  } finally {
    gradeLoading.value = false
  }
}

function hydrateUser(user, snapshot) {
  if (user.role === 'admin') {
    return {
      ...user,
      classIds: snapshot.classes.map(item => item.id)
    }
  }

  if (user.role === 'teacher') {
    const teacher = user.authRole === 'admin'
      ? null
      : snapshot.teachers.find(item => item.teacherNo === user.teacherNo || item.username === user.username) || snapshot.teachers[0]
    const teacherNo = teacher?.teacherNo || user.teacherNo || user.username || ''
    const teacherName = teacher?.name || user.name
    const classIds = snapshot.classes
      .filter(item =>
        item.masterId === teacherNo ||
        item.headTeacherNo === teacherNo ||
        item.teacherNo === teacherNo ||
        item.headTeacher === teacherName
      )
      .map(item => item.id)

    return {
      ...user,
      id: teacher?.id || user.id,
      username: teacher?.username || user.username,
      name: teacher?.name || user.name,
      teacherNo,
      classIds
    }
  }

  const student =
    snapshot.students.find(item => item.studentNo === user.studentNo) ||
    snapshot.students[0]

  if (!student) return user

  return {
    ...user,
    id: student.userId,
    username: student.studentNo,
    name: student.name,
    studentNo: student.studentNo,
    classId: student.classId
  }
}

function ensureClassExists(classId) {
  if (classes.value.some(item => item.id === classId)) return
  classes.value.push({
    id: classId,
    name: classId,
    grade: '数据库',
    major: '后端学生表',
    headTeacher: currentUser.value?.name || '待分配'
  })
}

async function refreshWeather() {
  try {
    weather.value = await loadRealtimeWeather()
  } catch (error) {
    weather.value = {
      ...weather.value,
      updatedAt: weather.value.updatedAt || '本地备用数据'
    }
  }
}

async function refreshFiles() {
  try {
    const agentFiles = await listAgentFiles()
    const merged = [...cloneData(initialFiles)]
    for (const file of agentFiles) {
      if (!merged.some(item => item.name === file.name)) {
        merged.unshift({
          ...file,
          ownerId: backendUserId(currentUser.value),
          audienceRoles: [currentUser.value?.role].filter(Boolean)
        })
      }
    }
    files.value = merged
  } catch (error) {
    files.value = cloneData(initialFiles)
  }
}

async function restoreLoginSession() {
  const savedUser = readLoginSession()
  if (!savedUser) {
    restoringSession.value = false
    return
  }

  try {
    const snapshot = await loadPlatformSnapshot()
    applyPlatformSnapshot(snapshot)
    currentUser.value = hydrateUser(savedUser, snapshot)
    saveLoginSession(currentUser.value)
    await Promise.allSettled([refreshTodos(), refreshGrades()])
  } catch (error) {
    currentUser.value = savedUser
    platformError.value = '已恢复本地登录状态，平台数据使用本地缓存。'
  } finally {
    refreshWeather()
    refreshFiles()
    activeView.value = 'dashboard'
    restoringSession.value = false
  }
}

function readLoginSession() {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    localStorage.removeItem(SESSION_STORAGE_KEY)
    return null
  }
}

function saveLoginSession(user) {
  if (!user) return
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(user))
}

function canAccessView(view) {
  const role = currentUser.value?.role
  const common = ['dashboard', 'profile', 'todos', 'notifications', 'files', 'assistant']
  const roleViews = {
    student: ['schedule', 'grades', 'library', 'forum'],
    teacher: ['classes', 'schedule', 'forum'],
    admin: ['classes', 'schedule', 'forum', 'admin']
  }
  return [...common, ...(roleViews[role] || [])].includes(view)
}

function canCurrentUserSeeItem(item = {}) {
  const user = currentUser.value
  if (!user) return false
  const role = user.role
  const userId = backendUserId(user)
  const itemOwner = item.ownerId || item.userId || item.user_id || item.studentNo || item.teacherNo
  if (itemOwner && String(itemOwner) === String(userId)) return true
  if (role === 'student' && item.classId) return item.classId === user.classId
  if (role === 'teacher' && item.classId && Array.isArray(user.classIds) && user.classIds.includes(item.classId)) return true
  if (Array.isArray(item.audienceRoles) && item.audienceRoles.includes(role)) return true
  if (item.role && item.role === role) return true
  if (item.classId && Array.isArray(user.classIds) && user.classIds.includes(item.classId)) return true
  if (item.audience === 'all') return true
  return false
}

function backendUserId(user = {}) {
  const account = user || {}
  return account.studentNo || account.teacherNo || account.username || account.id || ''
}

function toBackendDate(value) {
  const text = String(value || '').trim()
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return text
  const today = new Date()
  if (text.includes('明天')) {
    today.setDate(today.getDate() + 1)
  }
  return formatLocalDate(today)
}

function formatLocalDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
</script>
