<template>
  <section class="dashboard-page">
    <div class="overview-grid">
      <article class="metric-card weather-card">
        <span>{{ weather.city || '今日天气' }}</span>
        <strong>{{ weather.weather || '暂无数据' }}</strong>
        <p>{{ weather.temperature || '--' }} · {{ weather.wind || '--' }} · {{ weather.updatedAt || '待更新' }}</p>
      </article>

      <article class="metric-card">
        <span>今日课程</span>
        <strong>{{ todayCourses.length }}</strong>
        <p>{{ currentWeekdayLabel }} · {{ nextCourse ? `下一节 ${nextCourse.startTime}` : '暂无课程安排' }}</p>
      </article>

      <article class="metric-card">
        <span>当前班级</span>
        <strong>{{ visibleClasses.length }}</strong>
        <p>{{ currentUser.role === 'teacher' ? '当前教师可管理班级' : selectedClassName }}</p>
      </article>

      <article class="metric-card">
        <span>平台课程</span>
        <strong>{{ visibleCourses.length }}</strong>
        <p>覆盖 {{ visibleStudents.length }} 名学生的可访问课表数据</p>
      </article>
    </div>

    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h2>今日课程</h2>
          <p>{{ currentWeekdayLabel }}的课程安排，助手会基于这些数据回答课表相关问题。</p>
        </div>
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

      <div v-else class="empty-state compact">
        今日暂无课程安排。
      </div>
    </section>

    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h2>{{ currentUser.role === 'teacher' ? '平台管理视角' : '学生个人视角' }}</h2>
          <p>助手会基于当前登录角色读取不同范围的平台数据。</p>
        </div>
      </div>

      <div class="info-list">
        <div v-if="currentUser.role === 'teacher'">
          <strong>教师可用能力</strong>
          <p>创建班级、调整学生班级、维护班级课表，并让助手查询班级课程或检查课表冲突。</p>
        </div>
        <div v-else>
          <strong>学生可用能力</strong>
          <p>查看本人课表、结合天气获取出行建议，并通过助手查询个人课程和学习安排。</p>
        </div>
        <div>
          <strong>扩展方向</strong>
          <p>后续成绩、论坛、会议、通知模块可以作为新业务模块接入，助手通过新增工具调用这些能力。</p>
        </div>
      </div>
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
  }
})

const weekdayLabels = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
const todayIndex = new Date().getDay()
const currentWeekdayLabel = weekdayLabels[todayIndex]

const visibleClasses = computed(() => {
  if (props.currentUser.role === 'student') {
    return props.classes.filter(item => item.id === props.currentUser.classId)
  }

  if (Array.isArray(props.currentUser.classIds) && props.currentUser.classIds.length) {
    return props.classes.filter(item => props.currentUser.classIds.includes(item.id))
  }

  return props.classes
})

const visibleStudents = computed(() => {
  const classIds = visibleClasses.value.map(item => item.id)
  return props.students.filter(item => classIds.includes(item.classId))
})

const visibleCourses = computed(() => {
  const classIds = visibleClasses.value.map(item => item.id)
  return props.courses.filter(item => classIds.includes(item.classId))
})

const todayCourses = computed(() => {
  return visibleCourses.value
    .filter(item => normalizeWeekday(item.weekday) === todayIndex)
    .sort((left, right) => String(left.startTime || '').localeCompare(String(right.startTime || '')))
})

const nextCourse = computed(() => todayCourses.value[0] || null)

const selectedClassName = computed(() => {
  return visibleClasses.value[0]?.name || '未分配班级'
})

function className(classId) {
  return props.classes.find(item => item.id === classId)?.name || classId || '未分班'
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
