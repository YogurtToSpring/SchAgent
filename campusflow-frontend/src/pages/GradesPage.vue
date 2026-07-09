<template>
  <section v-if="currentUser.role === 'admin'" class="grades-page module-page">
    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h2>成绩管理</h2>
          <p>通过学号搜索学生成绩，并在确认后修改成绩记录。</p>
        </div>
        <button class="ghost-action" type="button" :disabled="loading" @click="$emit('refresh-grades')">
          {{ loading ? '同步中' : '同步成绩' }}
        </button>
      </div>

      <form class="filter-bar grade-search-bar" @submit.prevent="searchStudentGrades">
        <input v-model="adminSearch" placeholder="输入学生学号，例如 2024001" />
        <button class="primary-action compact" type="submit">查询</button>
      </form>

      <div v-if="selectedStudentNo" class="admin-grade-summary">
        <article>
          <span>学号</span>
          <strong>{{ selectedStudentNo }}</strong>
        </article>
        <article>
          <span>姓名</span>
          <strong>{{ selectedStudent?.name || '未匹配学生表' }}</strong>
        </article>
        <article>
          <span>班级</span>
          <strong>{{ selectedStudent?.classId || '-' }}</strong>
        </article>
        <article>
          <span>成绩记录</span>
          <strong>{{ adminStudentGrades.length }}</strong>
        </article>
      </div>

      <div class="data-table-wrap">
        <table>
          <thead>
            <tr>
              <th>课程号</th>
              <th>课程</th>
              <th>学期</th>
              <th>学分</th>
              <th>分数</th>
              <th>绩点</th>
              <th>等级</th>
              <th>考试类型</th>
              <th>备注</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="grade in adminStudentGrades" :key="grade.id">
              <td>{{ grade.courseId }}</td>
              <td>{{ grade.courseName }}</td>
              <td>{{ grade.semester }}</td>
              <td>{{ grade.credit }}</td>
              <td><strong>{{ grade.score }}</strong></td>
              <td>{{ grade.gradePoint }}</td>
              <td>{{ grade.gradeLetter }}</td>
              <td>{{ grade.examType || '-' }}</td>
              <td>{{ grade.remark || '-' }}</td>
              <td>
                <button class="ghost-action compact" type="button" @click="startEditGrade(grade)">修改</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="selectedStudentNo && !adminStudentGrades.length" class="empty-state compact">
        没有查询到该学生成绩
      </div>
      <div v-else-if="!selectedStudentNo" class="empty-state compact">
        输入学号后查询成绩记录
      </div>
    </section>

    <section v-if="editingGrade" class="content-panel">
      <div class="section-heading">
        <div>
          <h2>修改成绩</h2>
          <p>{{ editingGrade.courseName }} · {{ editingGrade.studentNo }}</p>
        </div>
      </div>

      <form class="structured-form grade-edit-form" @submit.prevent="confirmSaveEditedGrade">
        <label>
          课程号
          <input :value="editingGrade.courseId" disabled />
        </label>
        <label>
          学号
          <input :value="editingGrade.studentNo" disabled />
        </label>
        <label>
          分数
          <input v-model.number="editGrade.score" min="0" max="100" step="0.1" type="number" />
        </label>
        <label>
          学期
          <input v-model="editGrade.semester" />
        </label>
        <label>
          考试类型
          <input v-model="editGrade.examType" />
        </label>
        <label>
          备注
          <input v-model="editGrade.remark" />
        </label>
        <div class="section-actions">
          <button class="ghost-action compact" type="button" @click="cancelEditGrade">取消</button>
          <button class="primary-action compact" type="submit" :disabled="loading">确认修改</button>
        </div>
      </form>
    </section>
  </section>

  <section v-else class="grades-page module-page">
    <div class="overview-grid compact-grid">
      <article class="metric-card">
        <span>平均分</span>
        <strong>{{ averageScore }}</strong>
        <p>{{ selectedSemester }} 学期</p>
      </article>
      <article class="metric-card">
        <span>{{ currentUser.role === 'student' ? '累计 GPA' : '平均绩点' }}</span>
        <strong>{{ displayGpa }}</strong>
        <p>{{ filteredGrades.length }} 条成绩</p>
      </article>
      <article class="metric-card">
        <span>风险课程</span>
        <strong>{{ riskCourses.length }}</strong>
        <p>低于 60 分计入风险</p>
      </article>
      <article class="metric-card">
        <span>通过率</span>
        <strong>{{ passRate }}</strong>
        <p>{{ passedCount }} / {{ filteredGrades.length }}</p>
      </article>
    </div>

    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h2>{{ pageTitle }}</h2>
          <p>{{ pageSubtitle }}</p>
        </div>
        <div class="section-actions">
          <input v-model="selectedSemester" placeholder="学期" />
          <button class="ghost-action" type="button" :disabled="loading" @click="$emit('refresh-grades')">
            {{ loading ? '同步中' : '同步成绩' }}
          </button>
        </div>
      </div>

      <form v-if="canManageGrades" class="grade-entry-form" @submit.prevent="submitGrade">
        <label>
          课程号
          <input v-model="gradeForm.courseId" placeholder="输入课程号" />
        </label>
        <label>
          学号
          <input v-model="gradeForm.studentNo" placeholder="输入学生学号" />
        </label>
        <label>
          分数
          <input v-model.number="gradeForm.score" min="0" max="100" step="0.1" type="number" />
        </label>
        <label>
          学期
          <input v-model="gradeForm.semester" placeholder="2025-2026-2" />
        </label>
        <label>
          考试类型
          <input v-model="gradeForm.examType" placeholder="期末考试" />
        </label>
        <label>
          备注
          <input v-model="gradeForm.remark" placeholder="可选" />
        </label>
        <button class="primary-action compact" type="submit" :disabled="loading || !gradeForm.courseId || !gradeForm.studentNo">
          保存成绩
        </button>
      </form>

      <div class="data-table-wrap">
        <table>
          <thead>
            <tr>
              <th v-if="canManageGrades">学生</th>
              <th>课程</th>
              <th>学分</th>
              <th>分数</th>
              <th>绩点</th>
              <th>等级</th>
              <th>考试类型</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="grade in filteredGrades" :key="grade.id">
              <td v-if="canManageGrades">{{ grade.studentName }}（{{ grade.studentNo }}）</td>
              <td>{{ grade.courseName }}</td>
              <td>{{ grade.credit }}</td>
              <td><strong>{{ grade.score }}</strong></td>
              <td>{{ grade.gradePoint }}</td>
              <td>{{ grade.gradeLetter }}</td>
              <td>{{ grade.examType || '-' }}</td>
              <td>{{ grade.remark || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="!filteredGrades.length" class="empty-state compact">
        {{ loading ? '正在同步成绩' : '暂无成绩记录' }}
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  currentUser: {
    type: Object,
    required: true
  },
  grades: {
    type: Array,
    required: true
  },
  courses: {
    type: Array,
    default: () => []
  },
  students: {
    type: Array,
    default: () => []
  },
  summary: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['save-grade', 'refresh-grades'])

const selectedSemester = ref(props.grades[0]?.semester || '2025-2026-2')
const adminSearch = ref('')
const selectedStudentNo = ref('')
const editingGradeId = ref('')

const gradeForm = reactive({
  courseId: '',
  studentNo: '',
  score: 0,
  semester: selectedSemester.value,
  examType: '期末考试',
  remark: ''
})

const editGrade = reactive({
  score: 0,
  semester: '',
  examType: '',
  remark: ''
})

const canManageGrades = computed(() => props.currentUser.role === 'teacher')

const pageTitle = computed(() => props.currentUser.role === 'teacher' ? '成绩录入' : '我的成绩')

const pageSubtitle = computed(() => {
  if (props.currentUser.role === 'teacher') return '录入或修改本人授课课程的学生成绩。'
  return '成绩、绩点和 GPA 来自后端成绩系统。'
})

const filteredGrades = computed(() => props.grades.filter(item => item.semester === selectedSemester.value))

const selectedStudent = computed(() => props.students.find(student => student.studentNo === selectedStudentNo.value))

const adminStudentGrades = computed(() => {
  if (!selectedStudentNo.value) return []
  return props.grades.filter(grade => grade.studentNo === selectedStudentNo.value)
})

const editingGrade = computed(() => adminStudentGrades.value.find(grade => grade.id === editingGradeId.value))

const averageScore = computed(() => {
  if (!filteredGrades.value.length) return '-'
  return Math.round(filteredGrades.value.reduce((sum, item) => sum + Number(item.score || 0), 0) / filteredGrades.value.length)
})

const averageGradePoint = computed(() => {
  if (!filteredGrades.value.length) return '-'
  return (filteredGrades.value.reduce((sum, item) => sum + Number(item.gradePoint || 0), 0) / filteredGrades.value.length).toFixed(2)
})

const displayGpa = computed(() => {
  if (props.currentUser.role === 'student' && props.summary?.gpa != null) {
    return Number(props.summary.gpa).toFixed(2)
  }
  return averageGradePoint.value
})

const riskCourses = computed(() => filteredGrades.value.filter(item => Number(item.score || 0) < 60))

const passedCount = computed(() => filteredGrades.value.filter(item => Number(item.score || 0) >= 60).length)

const passRate = computed(() => {
  if (!filteredGrades.value.length) return '-'
  return `${Math.round((passedCount.value / filteredGrades.value.length) * 100)}%`
})

watch(
  () => props.grades,
  value => {
    if (!value.some(item => item.semester === selectedSemester.value) && value[0]?.semester) {
      selectedSemester.value = value[0].semester
    }
  }
)

watch(
  () => selectedSemester.value,
  value => {
    gradeForm.semester = value
  },
  { immediate: true }
)

function searchStudentGrades() {
  selectedStudentNo.value = adminSearch.value.trim()
  editingGradeId.value = ''
}

function startEditGrade(grade) {
  editingGradeId.value = grade.id
  editGrade.score = Number(grade.score || 0)
  editGrade.semester = grade.semester || ''
  editGrade.examType = grade.examType || '期末考试'
  editGrade.remark = grade.remark || ''
}

function cancelEditGrade() {
  editingGradeId.value = ''
}

function confirmSaveEditedGrade() {
  if (!editingGrade.value) return
  const message = `确认修改 ${editingGrade.value.studentNo} 的 ${editingGrade.value.courseName} 成绩？`
  if (!window.confirm(message)) return
  emit('save-grade', {
    courseId: editingGrade.value.courseId,
    studentNo: editingGrade.value.studentNo,
    score: Number(editGrade.score || 0),
    semester: editGrade.semester || editingGrade.value.semester,
    examType: editGrade.examType || '期末考试',
    remark: editGrade.remark || ''
  })
  editingGradeId.value = ''
}

function submitGrade() {
  if (!window.confirm(`确认保存 ${gradeForm.studentNo} 的课程 ${gradeForm.courseId} 成绩？`)) return
  emit('save-grade', {
    courseId: gradeForm.courseId,
    studentNo: gradeForm.studentNo,
    score: Number(gradeForm.score || 0),
    semester: gradeForm.semester || selectedSemester.value,
    examType: gradeForm.examType || '期末考试',
    remark: gradeForm.remark || ''
  })
}
</script>
