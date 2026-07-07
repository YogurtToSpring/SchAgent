<template>
  <section class="schedule-page">
    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h2>{{ currentUser.role === 'teacher' ? '班级课表' : '我的课表' }}</h2>
          <p>{{ currentUser.role === 'teacher' ? '教师可切换查看不同班级课表。' : '课表来自学生所属班级。' }}</p>
        </div>

        <select v-if="currentUser.role === 'teacher'" v-model="selectedClassId">
          <option v-for="item in classes" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
      </div>

      <div class="schedule-summary">
        <div>
          <span>当前班级</span>
          <strong>{{ selectedClass?.name || '未分配' }}</strong>
        </div>
        <div>
          <span>今日天气</span>
          <strong>{{ weather.weather }} · {{ weather.temperature }}</strong>
        </div>
        <div>
          <span>课程数量</span>
          <strong>{{ visibleCourses.length }}</strong>
        </div>
      </div>

      <div class="data-table-wrap">
        <table>
          <thead>
            <tr>
              <th>星期</th>
              <th>时间</th>
              <th>课程</th>
              <th>教师</th>
              <th>地点</th>
              <th>周次</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="course in visibleCourses" :key="course.id">
              <td>{{ course.weekday }}</td>
              <td>{{ course.startTime }}-{{ course.endTime }}</td>
              <td>{{ course.courseName }}</td>
              <td>{{ course.teacher }}</td>
              <td>{{ course.location }}</td>
              <td>{{ course.weeks }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

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
  },
  weather: {
    type: Object,
    required: true
  }
})

const selectedClassId = ref(
  props.currentUser.role === 'teacher' ? props.currentUser.classIds[0] : props.currentUser.classId
)

watch(
  () => props.currentUser,
  user => {
    selectedClassId.value = user.role === 'teacher' ? user.classIds[0] : user.classId
  }
)

const selectedClass = computed(() => props.classes.find(item => item.id === selectedClassId.value))

const visibleCourses = computed(() => {
  return props.courses.filter(item => item.classId === selectedClassId.value)
})
</script>
