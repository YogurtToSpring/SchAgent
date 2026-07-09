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
    @navigate="activeView = $event"
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
      :notifications="notifications"
      :reservations="reservations"
      :grades="grades"
      @navigate="activeView = $event"
    />

    <ProfilePage
      v-show="activeView === 'profile'"
      :current-user="currentUser"
      :classes="classes"
    />

    <TodoPage
      v-show="activeView === 'todos'"
      :todos="todos"
      @add-todo="addTodo"
      @toggle-todo="toggleTodo"
    />

    <ClassAdminPage
      v-if="currentUser.role === 'teacher' || currentUser.role === 'admin'"
      v-show="activeView === 'classes'"
      :classes="classes"
      :students="students"
      :teachers="teachers"
      :rooms="rooms"
      :current-user="currentUser"
      @add-class="addClass"
      @assign-student="assignStudent"
      @add-course="addCourse"
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
      :notifications="notifications"
      @mark-all-read="markAllNotificationsRead"
      @open-notice="openNotice"
    />

    <FileCenterPage
      v-show="activeView === 'files'"
      :files="files"
      @refresh-files="refreshFiles"
    />

    <ChatPage
      v-show="activeView === 'assistant'"
      :current-user="currentUser"
      :classes="classes"
      :students="students"
      :courses="courses"
      :weather="weather"
    />

    <AdminCenterPage
      v-if="currentUser.role === 'admin'"
      v-show="activeView === 'admin'"
      :classes="classes"
      :students="students"
      :courses="courses"
      :posts="forumPosts"
      :logs="systemLogs"
      @navigate="activeView = $event"
    />

    <div v-if="platformError" class="platform-alert" role="alert">
      <strong>平台数据提示</strong>
      <span>{{ platformError }}</span>
    </div>
  </PlatformLayout>
</template>

<script setup>
import { onMounted, ref } from 'vue'
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
  createClass,
  createCourse,
  enrollStudent,
  loadRealtimeWeather,
  loadPlatformSnapshot,
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
const librarySeats = ref(cloneData(initialLibrarySeats))
const reservations = ref(cloneData(initialReservations))
const forumPosts = ref(cloneData(initialForumPosts))
const notifications = ref(cloneData(initialNotifications))
const files = ref(cloneData(initialFiles))
const systemLogs = ref(cloneData(initialSystemLogs))
const platformError = ref('')
const restoringSession = ref(true)

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
  refreshWeather()
  refreshFiles()
  activeView.value = 'dashboard'
}

function logout() {
  currentUser.value = null
  activeView.value = 'dashboard'
  platformError.value = ''
  localStorage.removeItem(SESSION_STORAGE_KEY)
}

function addTodo(payload) {
  todos.value.unshift({
    id: `todo-${Date.now()}`,
    status: 'pending',
    ...payload
  })
}

function toggleTodo(todoId) {
  const todo = todos.value.find(item => item.id === todoId)
  if (!todo) return
  todo.status = todo.status === 'done' ? 'pending' : 'done'
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
    link: 'forum'
  })
}

function reviewPost(postId) {
  const post = forumPosts.value.find(item => item.id === postId)
  if (!post) return
  post.status = 'published'
}

function markAllNotificationsRead() {
  notifications.value = notifications.value.map(item => ({
    ...item,
    status: 'read'
  }))
}

function openNotice(notice) {
  const target = notifications.value.find(item => item.id === notice.id)
  if (target) target.status = 'read'
  if (notice.link) activeView.value = notice.link
}

async function addClass(payload) {
  try {
    await createClass({
      ...payload,
      classId: payload.classId || payload.id || payload.name,
      teacherNo: currentUser.value?.teacherNo || payload.teacherNo || payload.masterId,
      masterId: currentUser.value?.teacherNo || payload.masterId || payload.teacherNo
    })
    await refreshPlatformData()
    platformError.value = ''
  } catch (error) {
    platformError.value = '创建班级失败，请确认班级编号未重复且后端服务可用。'
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
    const classIds = snapshot.classes.map(item => item.id)

    return {
      ...user,
      id: teacher?.id || user.id,
      username: teacher?.username || user.username,
      name: teacher?.name || user.name,
      teacherNo: teacher?.teacherNo || user.teacherNo || '',
      classIds: classIds.length ? classIds : user.classIds || []
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
        merged.unshift(file)
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
</script>
