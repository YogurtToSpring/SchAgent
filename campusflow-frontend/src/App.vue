<template>
  <LoginPage v-if="!currentUser" @login="handleLogin" />

  <PlatformLayout
    v-else
    :current-user="currentUser"
    :active-view="activeView"
    @navigate="activeView = $event"
    @logout="logout"
  >
    <DashboardPage
      v-if="activeView === 'dashboard'"
      :current-user="currentUser"
      :classes="classes"
      :students="students"
      :courses="courses"
      :weather="weather"
    />

    <ClassAdminPage
      v-else-if="activeView === 'classes' && currentUser.role === 'teacher'"
      :classes="classes"
      :students="students"
      :current-user="currentUser"
      @add-class="addClass"
      @assign-student="assignStudent"
      @add-course="addCourse"
    />

    <SchedulePage
      v-else-if="activeView === 'schedule'"
      :current-user="currentUser"
      :classes="classes"
      :courses="courses"
      :weather="weather"
    />

    <ChatPage
      v-else
      :current-user="currentUser"
      :classes="classes"
      :students="students"
      :courses="courses"
      :weather="weather"
    />
  </PlatformLayout>
</template>

<script setup>
import { ref } from 'vue'
import ChatPage from './pages/ChatPage.vue'
import ClassAdminPage from './pages/ClassAdminPage.vue'
import DashboardPage from './pages/DashboardPage.vue'
import LoginPage from './pages/LoginPage.vue'
import SchedulePage from './pages/SchedulePage.vue'
import PlatformLayout from './components/PlatformLayout.vue'
import {
  cloneData,
  initialClasses,
  initialCourses,
  initialStudents,
  weatherSnapshot
} from './data/platformData'

const currentUser = ref(null)
const activeView = ref('dashboard')
const classes = ref(cloneData(initialClasses))
const students = ref(cloneData(initialStudents))
const courses = ref(cloneData(initialCourses))
const weather = ref(cloneData(weatherSnapshot))

function handleLogin(user) {
  currentUser.value = user
  activeView.value = 'dashboard'
}

function logout() {
  currentUser.value = null
  activeView.value = 'dashboard'
}

function addClass(payload) {
  const classItem = {
    id: `class-${Date.now()}`,
    ...payload
  }
  classes.value.push(classItem)

  if (currentUser.value?.role === 'teacher') {
    currentUser.value = {
      ...currentUser.value,
      classIds: [...currentUser.value.classIds, classItem.id]
    }
  }
}

function assignStudent({ studentId, classId }) {
  const student = students.value.find(item => item.id === studentId)
  if (student) {
    student.classId = classId
  }

  if (student?.userId && currentUser.value?.id === student.userId) {
    currentUser.value = {
      ...currentUser.value,
      classId
    }
  }
}

function addCourse(payload) {
  courses.value.push({
    id: `course-${Date.now()}`,
    ...payload
  })
}
</script>
