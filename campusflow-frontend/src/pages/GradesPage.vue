<template>
  <section class="grades-page module-page">
    <div class="overview-grid compact-grid">
      <article class="metric-card">
        <span>平均分</span>
        <strong>{{ averageScore }}</strong>
        <p>{{ selectedSemester }} 学期</p>
      </article>
      <article class="metric-card">
        <span>平均绩点</span>
        <strong>{{ averageGpa }}</strong>
        <p>{{ filteredGrades.length }} 门课程</p>
      </article>
      <article class="metric-card">
        <span>风险课程</span>
        <strong>{{ riskCourses.length }}</strong>
        <p>低于 75 分自动标记</p>
      </article>
      <article class="metric-card">
        <span>最高课程</span>
        <strong>{{ topCourse?.score || '-' }}</strong>
        <p>{{ topCourse?.courseName || '暂无数据' }}</p>
      </article>
    </div>

    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h2>{{ currentUser.role === 'teacher' ? '成绩录入' : '我的成绩' }}</h2>
          <p>{{ currentUser.role === 'teacher' ? '按班级维护课程成绩并查看分布。' : '查看成绩构成、绩点和课程风险。' }}</p>
        </div>
        <select v-model="selectedSemester">
          <option v-for="semester in semesters" :key="semester">{{ semester }}</option>
        </select>
      </div>

      <div class="data-table-wrap">
        <table>
          <thead>
            <tr>
              <th>课程</th>
              <th>学分</th>
              <th>平时</th>
              <th>期末</th>
              <th>总评</th>
              <th>绩点</th>
              <th>排名</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="grade in filteredGrades" :key="grade.id">
              <td>{{ grade.courseName }}</td>
              <td>{{ grade.credit }}</td>
              <td>{{ grade.usual }}</td>
              <td>{{ grade.final }}</td>
              <td><strong>{{ grade.score }}</strong></td>
              <td>{{ grade.gpa }}</td>
              <td>{{ grade.rank }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="content-panel insight-panel">
      <div class="section-heading">
        <div>
          <h2>成绩分析</h2>
          <p>课程表现会作为助手生成学习计划和待办的上下文。</p>
        </div>
      </div>
      <div class="grade-bars">
        <div v-for="grade in filteredGrades" :key="`${grade.id}-bar`">
          <span>{{ grade.courseName }}</span>
          <strong>{{ grade.score }}</strong>
          <i :style="{ width: `${grade.score}%` }"></i>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  currentUser: {
    type: Object,
    required: true
  },
  grades: {
    type: Array,
    required: true
  }
})

const selectedSemester = ref(props.grades[0]?.semester || '2025-2026-1')

const semesters = computed(() => [...new Set(props.grades.map(item => item.semester))])

const filteredGrades = computed(() => props.grades.filter(item => item.semester === selectedSemester.value))

const averageScore = computed(() => {
  if (!filteredGrades.value.length) return '-'
  return Math.round(filteredGrades.value.reduce((sum, item) => sum + item.score, 0) / filteredGrades.value.length)
})

const averageGpa = computed(() => {
  if (!filteredGrades.value.length) return '-'
  return (filteredGrades.value.reduce((sum, item) => sum + item.gpa, 0) / filteredGrades.value.length).toFixed(2)
})

const riskCourses = computed(() => filteredGrades.value.filter(item => item.score < 75))

const topCourse = computed(() => [...filteredGrades.value].sort((a, b) => b.score - a.score)[0])
</script>
