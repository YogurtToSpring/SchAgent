<template>
  <section class="schedule-page module-page">
    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h2>{{ pageTitle }}</h2>
          <p>{{ pageSubtitle }}</p>
        </div>
      </div>

      <div class="schedule-summary">
        <div>
          <span>{{ currentUser.role === 'admin' ? '课程总数' : '可见课程' }}</span>
          <strong>{{ filteredCourses.length }}</strong>
        </div>
        <div>
          <span>班级范围</span>
          <strong>{{ visibleClassCount }}</strong>
        </div>
        <div>
          <span>当前学期</span>
          <strong>{{ topSemester }}</strong>
        </div>
      </div>

      <div class="filter-bar">
        <input v-model="filters.keyword" placeholder="搜索课程、教师、地点、课程号" />
        <input v-model="filters.classKeyword" placeholder="搜索班级号或班级名" />
        <input v-model="filters.semester" placeholder="搜索学期" />
        <input v-model="filters.weekday" placeholder="搜索星期" />
      </div>

      <div class="data-table-wrap">
        <table>
          <thead>
            <tr>
              <th>课程号</th>
              <th>课程</th>
              <th>班级号</th>
              <th>班级名称</th>
              <th>星期</th>
              <th>时间</th>
              <th>教师</th>
              <th>地点</th>
              <th>周次</th>
              <th>学期</th>
              <th>学分</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="course in pagedCourses" :key="course.id">
              <td>{{ course.backendCourseId || course.courseId }}</td>
              <td>{{ course.courseName }}</td>
              <td>{{ course.classId }}</td>
              <td>{{ className(course.classId) }}</td>
              <td>{{ course.weekday }}</td>
              <td>{{ course.startTime }}-{{ course.endTime }}</td>
              <td>{{ course.teacher }}</td>
              <td>{{ course.location }}</td>
              <td>{{ course.weeks }}</td>
              <td>{{ course.semester || '-' }}</td>
              <td>{{ course.credit || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pagination-bar">
        <span>第 {{ filters.page }} / {{ totalPages }} 页，共 {{ filteredCourses.length }} 条</span>
        <div>
          <button class="ghost-action compact" type="button" :disabled="filters.page <= 1" @click="filters.page--">上一页</button>
          <button class="ghost-action compact" type="button" :disabled="filters.page >= totalPages" @click="filters.page++">下一页</button>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'

const props = defineProps({
  currentUser: {
    type: Object,
    required: true
  },
  classes: {
    type: Array,
    required: true
  },
  courses: {
    type: Array,
    required: true
  }
})

const pageSize = 10
const filters = reactive({
  keyword: '',
  classKeyword: '',
  semester: '',
  weekday: '',
  page: 1
})

const pageTitle = computed(() => {
  if (props.currentUser.role === 'admin') return '全校课表'
  if (props.currentUser.role === 'teacher') return '教学课表'
  return '我的课表'
})

const pageSubtitle = computed(() => {
  if (props.currentUser.role === 'admin') return '按课程、班级、教师、地点和学期检索全校课程。'
  if (props.currentUser.role === 'teacher') return '显示当前教师授课相关课程。'
  return '显示当前学生所属班级课程。'
})

const roleCourses = computed(() => {
  if (props.currentUser.role === 'admin') return props.courses
  if (props.currentUser.role === 'teacher') {
    return props.courses.filter(course => isTeacherCourse(course))
  }
  const studentNo = props.currentUser.studentNo || props.currentUser.username
  return props.courses.filter(course => {
    if (Array.isArray(course.studentNos)) return course.studentNos.includes(studentNo)
    return course.classId === props.currentUser.classId
  })
})

const filteredCourses = computed(() => {
  const keyword = normalize(filters.keyword)
  const classKeyword = normalize(filters.classKeyword)
  const semester = normalize(filters.semester)
  const weekday = normalize(filters.weekday)
  return roleCourses.value.filter(course => {
    const matchesKeyword = !keyword || [
      course.backendCourseId,
      course.courseId,
      course.courseName,
      course.teacher,
      course.teacherNo,
      course.location,
      course.roomId
    ].some(value => normalize(value).includes(keyword))
    const matchesClass = !classKeyword || [course.classId, className(course.classId)].some(value => normalize(value).includes(classKeyword))
    const matchesSemester = !semester || normalize(course.semester).includes(semester)
    const matchesWeekday = !weekday || normalize(course.weekday).includes(weekday)
    return matchesKeyword && matchesClass && matchesSemester && matchesWeekday
  })
})

const pagedCourses = computed(() => {
  const start = (filters.page - 1) * pageSize
  return filteredCourses.value.slice(start, start + pageSize)
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredCourses.value.length / pageSize)))

const visibleClassCount = computed(() => new Set(filteredCourses.value.map(course => course.classId).filter(Boolean)).size)

const topSemester = computed(() => filteredCourses.value.find(course => course.semester)?.semester || '-')

watch(
  () => [filters.keyword, filters.classKeyword, filters.semester, filters.weekday],
  () => {
    filters.page = 1
  }
)

function className(classId) {
  return props.classes.find(item => item.id === classId)?.name || classId || '未分班'
}

function isTeacherCourse(course) {
  const teacherNo = props.currentUser.teacherNo || props.currentUser.username
  const teacherName = props.currentUser.name
  return course.teacherNo === teacherNo || course.teacherNum === teacherNo || course.teacher === teacherName
}

function normalize(value) {
  return String(value || '').trim().toLowerCase()
}
</script>
