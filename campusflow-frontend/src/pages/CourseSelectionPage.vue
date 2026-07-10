<template>
  <section class="course-selection-page module-page">
    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h2>学生选课</h2>
          <p>浏览课程并完成选课或退课，时间冲突由系统自动校验。</p>
        </div>
        <button class="ghost-action compact icon-text-action" type="button" :disabled="loading" @click="loadCourses">
          <RefreshCw :size="16" />
          刷新
        </button>
      </div>

      <section class="course-selection-summary" aria-label="选课概览">
        <div>
          <span>课程总数</span>
          <strong>{{ courses.length }}</strong>
        </div>
        <div>
          <span>已选课程</span>
          <strong>{{ selectedCourseIds.length }}</strong>
        </div>
        <div>
          <span>已选学分</span>
          <strong>{{ selectedCredits }}</strong>
        </div>
        <div>
          <span>当前学号</span>
          <strong class="summary-account">{{ studentNo }}</strong>
        </div>
      </section>

      <div class="course-selection-toolbar">
        <div class="selection-tabs" role="tablist" aria-label="课程范围">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            :class="{ active: filters.scope === tab.key }"
            @click="filters.scope = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>
        <div class="course-selection-filters">
          <label class="search-input-field">
            <Search :size="16" />
            <input v-model="filters.keyword" placeholder="搜索课程号、课程名、教师或地点" />
          </label>
          <select v-model="filters.semester" aria-label="按学期筛选">
            <option value="">全部学期</option>
            <option v-for="semester in semesters" :key="semester" :value="semester">{{ semester }}</option>
          </select>
          <select v-model="filters.weekday" aria-label="按星期筛选">
            <option value="">全部星期</option>
            <option v-for="weekday in weekdays" :key="weekday" :value="weekday">{{ weekday }}</option>
          </select>
        </div>
      </div>

      <p v-if="feedback.text" class="module-feedback" :class="feedback.type" role="status">
        {{ feedback.text }}
      </p>

      <div v-if="loading" class="empty-state">正在加载课程...</div>
      <div v-else-if="!filteredCourses.length" class="empty-state">当前筛选条件下没有课程</div>
      <template v-else>
        <div class="data-table-wrap course-selection-table-wrap">
          <table class="course-selection-table">
            <thead>
              <tr>
                <th>课程号</th>
                <th>课程名称</th>
                <th>授课教师</th>
                <th>上课时间</th>
                <th>地点</th>
                <th>周次</th>
                <th>学期</th>
                <th>学分</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="course in pagedCourses" :key="course.courseId" :class="{ 'selected-course-row': isSelected(course) }">
                <td><strong>{{ course.courseId }}</strong></td>
                <td>{{ course.courseName }}</td>
                <td>{{ course.teacher }}</td>
                <td>{{ course.weekday }} {{ course.startTime }}-{{ course.endTime }}</td>
                <td>{{ course.location }}</td>
                <td>{{ course.weeks }}</td>
                <td>{{ course.semester || '-' }}</td>
                <td>{{ course.credit || '-' }}</td>
                <td>
                  <span class="selection-status" :class="isSelected(course) ? 'selected' : 'available'">
                    {{ isSelected(course) ? '已选' : '可选' }}
                  </span>
                </td>
                <td>
                  <button
                    v-if="isSelected(course)"
                    class="ghost-action compact danger-action icon-text-action"
                    type="button"
                    :disabled="pendingCourseId === course.courseId"
                    @click="dropCourse(course)"
                  >
                    <Trash2 :size="15" />
                    退课
                  </button>
                  <button
                    v-else
                    class="primary-action compact icon-text-action"
                    type="button"
                    :disabled="pendingCourseId === course.courseId"
                    @click="selectCourse(course)"
                  >
                    <Plus :size="15" />
                    选课
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination-bar">
          <span>第 {{ filters.page }} / {{ totalPages }} 页，共 {{ filteredCourses.length }} 门课程</span>
          <div>
            <button class="ghost-action compact" type="button" :disabled="filters.page <= 1" @click="filters.page--">上一页</button>
            <button class="ghost-action compact" type="button" :disabled="filters.page >= totalPages" @click="filters.page++">下一页</button>
          </div>
        </div>
      </template>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Plus, RefreshCw, Search, Trash2 } from 'lucide-vue-next'
import { dropStudentCourse, enrollStudent, loadStudentCourseSelection } from '../api/platform'

const props = defineProps({
  currentUser: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['enrollment-changed'])
const pageSize = 12
const tabs = [
  { key: 'all', label: '全部课程' },
  { key: 'selected', label: '已选课程' },
  { key: 'available', label: '可选课程' }
]
const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const courses = ref([])
const selectedCourseIds = ref([])
const loading = ref(false)
const pendingCourseId = ref('')
const feedback = reactive({ text: '', type: '' })
const filters = reactive({
  scope: 'all',
  keyword: '',
  semester: '',
  weekday: '',
  page: 1
})

const studentNo = computed(() => props.currentUser.studentNo || props.currentUser.username || '')
const selectedIdSet = computed(() => new Set(selectedCourseIds.value))
const semesters = computed(() => [...new Set(courses.value.map(course => course.semester).filter(Boolean))].sort().reverse())
const selectedCredits = computed(() => {
  const total = courses.value
    .filter(course => selectedIdSet.value.has(course.courseId))
    .reduce((sum, course) => sum + Number(course.credit || 0), 0)
  return Number.isInteger(total) ? total : total.toFixed(1)
})

const filteredCourses = computed(() => {
  const keyword = normalize(filters.keyword)
  return courses.value.filter(course => {
    const selected = isSelected(course)
    const matchesScope = filters.scope === 'all' || (filters.scope === 'selected' ? selected : !selected)
    const matchesSemester = !filters.semester || course.semester === filters.semester
    const matchesWeekday = !filters.weekday || course.weekday === filters.weekday
    const matchesKeyword = !keyword || [
      course.courseId,
      course.courseName,
      course.teacher,
      course.teacherNo,
      course.location
    ].some(value => normalize(value).includes(keyword))
    return matchesScope && matchesSemester && matchesWeekday && matchesKeyword
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredCourses.value.length / pageSize)))
const pagedCourses = computed(() => {
  const start = (filters.page - 1) * pageSize
  return filteredCourses.value.slice(start, start + pageSize)
})

watch(
  () => [filters.scope, filters.keyword, filters.semester, filters.weekday],
  () => {
    filters.page = 1
  }
)

onMounted(loadCourses)

async function loadCourses() {
  if (!studentNo.value) return
  loading.value = true
  clearFeedback()
  try {
    const result = await loadStudentCourseSelection(studentNo.value)
    courses.value = result.courses
    selectedCourseIds.value = result.selectedCourseIds
    if (filters.page > totalPages.value) filters.page = totalPages.value
  } catch (error) {
    courses.value = []
    selectedCourseIds.value = []
    showFeedback(toCourseError(error, '课程加载失败，请确认后端课程接口可用。'), 'error')
  } finally {
    loading.value = false
  }
}

async function selectCourse(course) {
  pendingCourseId.value = course.courseId
  clearFeedback()
  try {
    await enrollStudent(course.courseId, studentNo.value)
    if (!selectedIdSet.value.has(course.courseId)) {
      selectedCourseIds.value = [...selectedCourseIds.value, course.courseId]
    }
    showFeedback(`已选择《${course.courseName}》。`, 'success')
    emit('enrollment-changed')
  } catch (error) {
    showFeedback(toCourseError(error, '选课失败，请稍后重试。'), 'error')
  } finally {
    pendingCourseId.value = ''
  }
}

async function dropCourse(course) {
  if (!window.confirm(`确认退选《${course.courseName}》？`)) return
  pendingCourseId.value = course.courseId
  clearFeedback()
  try {
    await dropStudentCourse(course.courseId, studentNo.value)
    selectedCourseIds.value = selectedCourseIds.value.filter(id => id !== course.courseId)
    showFeedback(`已退选《${course.courseName}》。`, 'success')
    emit('enrollment-changed')
  } catch (error) {
    showFeedback(toCourseError(error, '退课失败，请稍后重试。'), 'error')
  } finally {
    pendingCourseId.value = ''
  }
}

function isSelected(course) {
  return selectedIdSet.value.has(course.courseId)
}

function showFeedback(text, type) {
  feedback.text = text
  feedback.type = type
}

function clearFeedback() {
  feedback.text = ''
  feedback.type = ''
}

function toCourseError(error, fallback) {
  const detail = String(error?.response?.data?.detail || '')
  if (detail.includes('Conflict') || detail.includes('not free')) return '该课程与已选课程时间冲突，无法选择。'
  if (detail.includes('Already enrolled')) return '该课程已经选择，无需重复操作。'
  if (error?.response?.status === 404) return '没有找到对应的学生或课程。'
  return detail || fallback
}

function normalize(value) {
  return String(value || '').trim().toLowerCase()
}
</script>
