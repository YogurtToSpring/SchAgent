<template>
  <section class="dashboard-page">
    <div class="overview-grid">
      <article class="metric-card">
        <span>班级数量</span>
        <strong>{{ visibleClasses.length }}</strong>
        <p>{{ currentUser.role === 'teacher' ? '当前教师可管理班级' : '学生所属班级' }}</p>
      </article>
      <article class="metric-card">
        <span>学生数量</span>
        <strong>{{ visibleStudents.length }}</strong>
        <p>来自平台学生管理数据</p>
      </article>
      <article class="metric-card">
        <span>课程数量</span>
        <strong>{{ visibleCourses.length }}</strong>
        <p>已接入课表数据</p>
      </article>
      <article class="metric-card weather-card">
        <span>{{ weather.city || '今日天气' }}</span>
        <strong>{{ weather.weather }}</strong>
        <p>{{ weather.temperature }} · {{ weather.wind }} · {{ weather.updatedAt }}</p>
      </article>
    </div>

    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h2>{{ currentUser.role === 'teacher' ? '平台管理视角' : '学生今日视角' }}</h2>
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

const visibleClasses = computed(() => {
  if (props.currentUser.role === 'teacher') {
    return props.classes.filter(item => props.currentUser.classIds.includes(item.id))
  }
  return props.classes.filter(item => item.id === props.currentUser.classId)
})

const visibleStudents = computed(() => {
  const classIds = visibleClasses.value.map(item => item.id)
  return props.students.filter(item => classIds.includes(item.classId))
})

const visibleCourses = computed(() => {
  const classIds = visibleClasses.value.map(item => item.id)
  return props.courses.filter(item => classIds.includes(item.classId))
})
</script>
