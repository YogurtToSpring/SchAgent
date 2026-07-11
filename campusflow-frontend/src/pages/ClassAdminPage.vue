<template>
  <section class="admin-page">
    <section v-if="activeModule === 'home'" class="admin-module-grid">
      <article
        v-for="module in modules"
        :key="module.key"
        class="admin-module-card"
        @click="activeModule = module.key"
      >
        <span>{{ module.meta }}</span>
        <strong>{{ module.title }}</strong>
        <p>{{ module.desc }}</p>
      </article>
    </section>

    <section v-else class="content-panel admin-subpage">
      <div class="section-heading">
        <div>
          <button class="ghost-action compact" type="button" @click="goHome">返回</button>
          <h2>{{ currentModule.title }}</h2>
          <p>{{ currentModule.desc }}</p>
        </div>
      </div>

      <template v-if="activeModule === 'classes'">
        <form v-if="isAdmin" class="structured-form class-create-form" @submit.prevent="addClass">
          <label>
            班级号
            <input v-model="newClass.classId" />
          </label>
          <label>
            班级名称
            <input v-model="newClass.name" />
          </label>
          <label>
            年级
            <input v-model="newClass.grade" />
          </label>
          <label>
            专业
            <input v-model="newClass.major" />
          </label>
          <label>
            容量
            <input v-model.number="newClass.capacity" min="1" type="number" />
          </label>
          <label class="search-field">
            班主任
            <input v-model="newClass.teacherQuery" />
            <div v-if="teacherSuggestions(newClass.teacherQuery).length" class="search-suggestions">
              <button
                v-for="teacher in teacherSuggestions(newClass.teacherQuery)"
                :key="teacher.teacherNo"
                type="button"
                @click="newClass.teacherQuery = formatTeacher(teacher)"
              >
                {{ formatTeacher(teacher) }}
              </button>
            </div>
          </label>
          <button class="primary-action compact" type="submit">确认创建</button>
        </form>

        <div class="filter-bar">
          <label class="filter-field"><span>班级搜索</span><input v-model="classFilters.keyword" /></label>
          <label class="filter-field"><span>年级</span><input v-model="classFilters.grade" /></label>
          <label class="filter-field"><span>专业</span><input v-model="classFilters.major" /></label>
        </div>

        <div class="data-table-wrap">
          <table>
            <thead>
              <tr>
                <th>班级号</th>
                <th>班级名称</th>
                <th>年级</th>
                <th>专业</th>
                <th>班主任</th>
                <th>容量</th>
                <th>学生数</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in pagedClasses" :key="item.id">
                <td>{{ item.id }}</td>
                <td>{{ item.name }}</td>
                <td>{{ item.grade }}</td>
                <td>{{ item.major }}</td>
                <td>{{ item.headTeacher }}</td>
                <td>{{ item.capacity || '-' }}</td>
                <td>{{ classStudents(item.id).length }}</td>
                <td>
                  <button class="ghost-action compact" type="button" @click="selectedClassId = item.id">查看学生</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination-bar">
          <span>第 {{ classFilters.page }} / {{ classTotalPages }} 页，共 {{ filteredClasses.length }} 条</span>
          <div>
            <button class="ghost-action compact" type="button" :disabled="classFilters.page <= 1" @click="classFilters.page--">上一页</button>
            <button class="ghost-action compact" type="button" :disabled="classFilters.page >= classTotalPages" @click="classFilters.page++">下一页</button>
          </div>
        </div>

        <section v-if="selectedClass" class="detail-panel">
          <div class="section-heading">
            <div>
              <h2>{{ selectedClass.name }}</h2>
              <p>{{ selectedClass.id }} · {{ classStudents(selectedClass.id).length }} 名学生</p>
            </div>
            <button class="ghost-action compact" type="button" @click="prepareClassNotice(selectedClass)">发送通知</button>
          </div>

          <div class="data-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>班级</th>
                  <th>学生</th>
                  <th>学号</th>
                  <th>总绩点</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="student in classStudents(selectedClass.id)" :key="student.id">
                  <td>{{ selectedClass.name }}</td>
                  <td>{{ student.name }}</td>
                  <td>{{ student.studentNo }}</td>
                  <td>{{ studentGpa(student) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>

      <template v-else-if="activeModule === 'students' && isAdmin">
        <div class="filter-bar">
          <label class="filter-field"><span>学生搜索</span><input v-model="studentFilters.keyword" /></label>
          <label class="filter-field"><span>目标班级</span><input v-model="studentFilters.targetClass" /></label>
        </div>

        <div class="data-table-wrap">
          <table>
            <thead>
              <tr>
                <th>姓名</th>
                <th>学号</th>
                <th>当前班级</th>
                <th>调整班级</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="student in pagedStudents" :key="student.id">
                <td>{{ student.name }}</td>
                <td>{{ student.studentNo }}</td>
                <td>{{ className(student.classId) }}</td>
                <td>
                  <div class="inline-search">
                    <input
                      :value="classQueries[student.id] ?? studentFilters.targetClass"
                      @input="classQueries[student.id] = $event.target.value"
                    />
                    <div v-if="studentClassSuggestions(student).length" class="search-suggestions">
                      <button
                        v-for="item in studentClassSuggestions(student)"
                        :key="item.id"
                        type="button"
                        @click="confirmAssignStudent(student, item)"
                      >
                        {{ item.id }} · {{ item.name }}
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination-bar">
          <span>第 {{ studentFilters.page }} / {{ studentTotalPages }} 页，共 {{ filteredStudents.length }} 条</span>
          <div>
            <button class="ghost-action compact" type="button" :disabled="studentFilters.page <= 1" @click="studentFilters.page--">上一页</button>
            <button class="ghost-action compact" type="button" :disabled="studentFilters.page >= studentTotalPages" @click="studentFilters.page++">下一页</button>
          </div>
        </div>
      </template>

      <template v-else-if="activeModule === 'accounts' && isAdmin">
        <form class="structured-form account-import-form" @submit.prevent="stageStudent">
          <label>
            姓名
            <input v-model="studentDraft.name" />
          </label>
          <label>
            学号
            <input v-model="studentDraft.studentNo" />
          </label>
          <label class="search-field">
            班级
            <input v-model="studentDraft.classQuery" />
            <div v-if="classSuggestions(studentDraft.classQuery).length" class="search-suggestions">
              <button
                v-for="item in classSuggestions(studentDraft.classQuery)"
                :key="item.id"
                type="button"
                @click="studentDraft.classQuery = formatClass(item)"
              >
                {{ formatClass(item) }}
              </button>
            </div>
          </label>
          <label>
            初始密码
            <input v-model="studentDraft.password" />
          </label>
          <button class="primary-action compact" type="submit">加入待导入</button>
        </form>

        <div class="data-table-wrap">
          <table>
            <thead>
              <tr>
                <th>姓名</th>
                <th>学号</th>
                <th>班级</th>
                <th>初始密码</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in pendingStudents" :key="row.studentNo">
                <td>{{ row.name }}</td>
                <td>{{ row.studentNo }}</td>
                <td>{{ className(row.classId) }}</td>
                <td>{{ row.password }}</td>
                <td><button class="ghost-action compact" type="button" @click="removePendingStudent(row.studentNo)">移除</button></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="section-actions">
          <button class="primary-action compact" type="button" :disabled="!pendingStudents.length" @click="confirmImportStudents">
            确认导入账号
          </button>
        </div>

        <div v-if="studentImportResult" class="import-result">
          <strong>成功 {{ studentImportResult.success }} 条，失败 {{ studentImportResult.failed }} 条</strong>
          <span v-for="message in studentImportResult.messages.slice(0, 6)" :key="message">{{ message }}</span>
        </div>
      </template>

      <template v-else-if="activeModule === 'courses'">
        <form v-if="isAdmin" class="structured-form course-import-form" @submit.prevent="addCourse">
          <label>
            课程编号
            <input v-model="newCourse.courseId" />
          </label>
          <label>
            课程名称
            <input v-model="newCourse.courseName" />
          </label>
          <label class="search-field">
            面向班级
            <input v-model="newCourse.classQuery" />
            <div v-if="classSuggestions(newCourse.classQuery).length" class="search-suggestions">
              <button
                v-for="item in classSuggestions(newCourse.classQuery)"
                :key="item.id"
                type="button"
                @click="newCourse.classQuery = formatClass(item)"
              >
                {{ formatClass(item) }}
              </button>
            </div>
          </label>
          <label class="search-field">
            任课教师
            <input v-model="newCourse.teacherQuery" />
            <div v-if="teacherSuggestions(newCourse.teacherQuery).length" class="search-suggestions">
              <button
                v-for="teacher in teacherSuggestions(newCourse.teacherQuery)"
                :key="teacher.teacherNo"
                type="button"
                @click="newCourse.teacherQuery = formatTeacher(teacher)"
              >
                {{ formatTeacher(teacher) }}
              </button>
            </div>
          </label>
          <label>
            星期
            <input v-model="newCourse.weekday" />
          </label>
          <label>
            开始时间
            <input v-model="newCourse.startTime" />
          </label>
          <label>
            结束时间
            <input v-model="newCourse.endTime" />
          </label>
          <label class="search-field">
            地点
            <input
              v-model="newCourse.roomQuery"
              @blur="scheduleCloseRoomSuggestions"
              @focus="roomSuggestionsOpen = true"
              @input="roomSuggestionsOpen = true"
              @keydown.esc="roomSuggestionsOpen = false"
            />
            <div v-if="roomSuggestionsOpen && roomSuggestions(newCourse.roomQuery).length" class="search-suggestions">
              <button
                v-for="room in roomSuggestions(newCourse.roomQuery)"
                :key="room.roomFull"
                type="button"
                @mousedown.prevent="selectCourseRoom(room)"
              >
                {{ room.label }}
              </button>
            </div>
          </label>
          <label>
            起始周
            <input v-model="newCourse.weekStart" />
          </label>
          <label>
            结束周
            <input v-model="newCourse.weekEnd" />
          </label>
          <label>
            学期
            <input v-model="newCourse.semester" />
          </label>
          <label>
            学分
            <input v-model="newCourse.credit" type="number" min="0" step="0.5" />
          </label>
          <button class="primary-action compact" type="submit">确认添加课程</button>
        </form>

        <div class="filter-bar">
          <label class="filter-field"><span>课程搜索</span><input v-model="courseFilters.keyword" /></label>
          <label class="filter-field"><span>学期</span><input v-model="courseFilters.semester" /></label>
        </div>

        <div class="course-card-list">
          <article
            v-for="course in filteredCourses"
            :key="course.id"
            class="course-manage-card"
            :class="{ active: selectedCourseKey === course.id }"
            @click="selectedCourseKey = course.id"
          >
            <div class="course-card-head">
              <span>{{ course.backendCourseId || course.courseId || course.id }}</span>
              <strong>{{ course.courseName }}</strong>
            </div>
            <div class="course-card-meta">
              <span>{{ className(course.classId) }}</span>
              <span>{{ course.teacher || '待定教师' }}</span>
            </div>
            <div class="course-card-detail">
              <span>{{ course.weekday || '未排课' }} {{ course.startTime || '--:--' }}-{{ course.endTime || '--:--' }}</span>
              <span>{{ course.location || course.roomId || '未设置地点' }}</span>
            </div>
            <div class="course-card-foot">
              <span>{{ course.semester || '未设置学期' }}</span>
              <span>{{ courseStudents(course).length }} 名学生</span>
            </div>
          </article>
        </div>

        <section v-if="selectedCourse" class="detail-panel">
          <div class="section-heading">
            <div>
              <h2>{{ selectedCourse.courseName }}</h2>
              <p>{{ className(selectedCourse.classId) }} · {{ selectedCourse.weekday }} {{ selectedCourse.startTime }}-{{ selectedCourse.endTime }}</p>
            </div>
            <button class="ghost-action compact" type="button" @click="prepareCourseNotice(selectedCourse)">发送通知</button>
          </div>

          <div class="data-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>学生</th>
                  <th>学号</th>
                  <th>平时分</th>
                  <th>期末分</th>
                  <th>绩点</th>
                  <th>备注</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="student in courseStudents(selectedCourse)" :key="student.studentNo">
                  <td>{{ student.name }}</td>
                  <td>{{ student.studentNo }}</td>
                  <td><input v-model="gradeEdit(selectedCourse, student).usual" class="table-input" type="number" min="0" max="100" /></td>
                  <td><input v-model="gradeEdit(selectedCourse, student).final" class="table-input" type="number" min="0" max="100" /></td>
                  <td>{{ gradePointPreview(selectedCourse, student) }}</td>
                  <td><input v-model="gradeEdit(selectedCourse, student).remark" class="table-input" /></td>
                  <td>
                    <button class="primary-action compact" type="button" @click="confirmSaveCourseGrade(selectedCourse, student)">
                      保存
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>

      <section v-if="noticeTarget" class="detail-panel">
        <div class="section-heading">
          <div>
            <h2>发送通知</h2>
            <p>{{ noticeTarget.label }}</p>
          </div>
          <button class="ghost-action compact" type="button" @click="noticeTarget = null">关闭</button>
        </div>
        <form class="structured-form notice-compose-form" @submit.prevent="sendNotice">
          <label>
            标题
            <input v-model="noticeDraft.title" />
          </label>
          <label>
            内容
            <input v-model="noticeDraft.content" />
          </label>
          <button class="primary-action compact" type="submit">确认发送</button>
        </form>
      </section>
    </section>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  classes: {
    type: Array,
    required: true
  },
  students: {
    type: Array,
    required: true
  },
  teachers: {
    type: Array,
    default: () => []
  },
  rooms: {
    type: Array,
    default: () => []
  },
  courses: {
    type: Array,
    default: () => []
  },
  grades: {
    type: Array,
    default: () => []
  },
  currentUser: {
    type: Object,
    required: true
  },
  studentImportResult: {
    type: Object,
    default: null
  }
})

const emit = defineEmits([
  'add-class',
  'assign-student',
  'add-course',
  'import-students',
  'save-grade',
  'send-notification'
])

const pageSize = 8
const GRADE_DRAFT_STORAGE_KEY = 'campusflow.courseGradeDrafts'
const activeModule = ref('home')
const selectedClassId = ref('')
const selectedCourseKey = ref('')
const pendingStudents = ref([])
const noticeTarget = ref(null)
const roomSuggestionsOpen = ref(false)
const classQueries = reactive({})
const storedGradeDrafts = reactive(loadStoredGradeDrafts())
const gradeEdits = reactive({})

const isAdmin = computed(() => props.currentUser.role === 'admin')
const isTeacher = computed(() => props.currentUser.role === 'teacher')

const modules = computed(() => {
  if (isAdmin.value) {
    return [
      { key: 'classes', title: '班级模块', meta: 'CLASS', desc: '创建班级、检索班级、查看班级学生并发送通知。' },
      { key: 'students', title: '学生班级分配', meta: 'STUDENT', desc: '按姓名或学号搜索学生，并通过搜索调整班级。' },
      { key: 'accounts', title: '学生账号导入', meta: 'ACCOUNT', desc: '逐项填写账号信息，确认后批量注册学生。' },
      { key: 'courses', title: '课程模块', meta: 'COURSE', desc: '维护课程并在课程详情中管理学生成绩。' }
    ]
  }

  return [
    { key: 'classes', title: '我的班级', meta: 'CLASS', desc: '查看自己作为班主任负责的班级和学生绩点。' },
    { key: 'courses', title: '我的课程', meta: 'COURSE', desc: '查看自己所教课程、学生名单并录入成绩。' }
  ]
})

const classFilters = reactive({
  keyword: '',
  grade: '',
  major: '',
  page: 1
})

const studentFilters = reactive({
  keyword: '',
  targetClass: '',
  page: 1
})

const courseFilters = reactive({
  keyword: '',
  semester: ''
})

const newClass = reactive({
  classId: '',
  name: '',
  grade: '2024级',
  major: '',
  capacity: 45,
  teacherQuery: ''
})

const studentDraft = reactive({
  name: '',
  studentNo: '',
  classQuery: '',
  password: '123456'
})

const newCourse = reactive({
  courseId: nextCourseId(),
  courseName: '',
  classQuery: '',
  teacherQuery: '',
  weekday: '周一',
  startTime: '08:00',
  endTime: '09:40',
  roomQuery: '',
  weekStart: '1',
  weekEnd: '16',
  semester: '2025-2026-2',
  credit: '2'
})

const noticeDraft = reactive({
  title: '',
  content: ''
})

const currentModule = computed(() => modules.value.find(item => item.key === activeModule.value) || modules.value[0])

const manageableClasses = computed(() => {
  if (isAdmin.value) return props.classes
  return props.classes.filter(item => isTeacherHeadOfClass(item))
})

const filteredClasses = computed(() => {
  const keyword = normalize(classFilters.keyword)
  const grade = normalize(classFilters.grade)
  const major = normalize(classFilters.major)
  return manageableClasses.value.filter(item => {
    const matchesKeyword = !keyword || [item.id, item.name, item.headTeacher, item.masterId].some(value => normalize(value).includes(keyword))
    const matchesGrade = !grade || normalize(item.grade).includes(grade)
    const matchesMajor = !major || normalize(item.major).includes(major)
    return matchesKeyword && matchesGrade && matchesMajor
  })
})

const pagedClasses = computed(() => paginate(filteredClasses.value, classFilters.page))
const classTotalPages = computed(() => totalPages(filteredClasses.value.length))

const selectedClass = computed(() => manageableClasses.value.find(item => item.id === selectedClassId.value))

const filteredStudents = computed(() => {
  const keyword = normalize(studentFilters.keyword)
  return props.students.filter(student => {
    if (!keyword) return true
    return [student.name, student.studentNo, student.classId, className(student.classId)].some(value => normalize(value).includes(keyword))
  })
})

const pagedStudents = computed(() => paginate(filteredStudents.value, studentFilters.page))
const studentTotalPages = computed(() => totalPages(filteredStudents.value.length))

const manageableCourses = computed(() => {
  if (isAdmin.value) return props.courses
  return props.courses.filter(course => isTeacherCourse(course))
})

const filteredCourses = computed(() => {
  const keyword = normalize(courseFilters.keyword)
  const semester = normalize(courseFilters.semester)
  return manageableCourses.value.filter(course => {
    const matchesKeyword = !keyword || [
      course.id,
      course.backendCourseId,
      course.courseId,
      course.courseName,
      course.teacher,
      course.teacherNo,
      course.classId,
      className(course.classId)
    ].some(value => normalize(value).includes(keyword))
    const matchesSemester = !semester || normalize(course.semester).includes(semester)
    return matchesKeyword && matchesSemester
  })
})

const selectedCourse = computed(() => filteredCourses.value.find(course => course.id === selectedCourseKey.value))

watch(
  () => [classFilters.keyword, classFilters.grade, classFilters.major],
  () => {
    classFilters.page = 1
  }
)

watch(
  () => studentFilters.keyword,
  () => {
    studentFilters.page = 1
  }
)

watch(
  () => props.teachers,
  () => {
    if (!newClass.teacherQuery) newClass.teacherQuery = props.teachers[0] ? formatTeacher(props.teachers[0]) : ''
    if (!newCourse.teacherQuery) {
      const currentTeacher = props.teachers.find(item => item.teacherNo === props.currentUser.teacherNo)
      newCourse.teacherQuery = currentTeacher ? formatTeacher(currentTeacher) : props.currentUser.teacherNo || props.currentUser.name || ''
    }
  },
  { immediate: true }
)

watch(
  () => props.classes,
  () => {
    if (!studentDraft.classQuery) studentDraft.classQuery = props.classes[0] ? formatClass(props.classes[0]) : ''
    if (!newCourse.classQuery) newCourse.classQuery = props.classes[0] ? formatClass(props.classes[0]) : ''
    if (!selectedClassId.value && manageableClasses.value[0]) selectedClassId.value = manageableClasses.value[0].id
  },
  { immediate: true }
)

watch(
  () => manageableCourses.value,
  value => {
    if (!selectedCourseKey.value && value[0]) selectedCourseKey.value = value[0].id
  },
  { immediate: true }
)

watch(
  () => props.rooms,
  () => {
    if (!newCourse.roomQuery) newCourse.roomQuery = props.rooms[0]?.roomFull || '3-3-301'
  },
  { immediate: true }
)

function goHome() {
  activeModule.value = 'home'
  noticeTarget.value = null
}

function addClass() {
  const classId = newClass.classId.trim() || newClass.name.trim()
  const name = newClass.name.trim() || classId
  const masterId = resolveTeacherNo(newClass.teacherQuery)
  if (!classId || !name || !masterId) return
  if (!window.confirm(`确认创建班级 ${name}（${classId}）？`)) return
  emit('add-class', {
    classId,
    name,
    major: newClass.major.trim() || '未设置',
    grade: newClass.grade.trim() || '2024级',
    headTeacherNo: masterId,
    teacherNo: masterId,
    masterId,
    capacity: Number(newClass.capacity) || 45
  })
  newClass.classId = ''
  newClass.name = ''
  newClass.major = ''
}

function confirmAssignStudent(student, targetClass) {
  if (!targetClass?.id || targetClass.id === student.classId) return
  if (!window.confirm(`确认将 ${student.name}（${student.studentNo}）调整到 ${targetClass.name}？`)) return
  emit('assign-student', { studentId: student.id, classId: targetClass.id })
  classQueries[student.id] = ''
}

function stageStudent() {
  const classId = resolveClassId(studentDraft.classQuery)
  if (!studentDraft.name.trim() || !studentDraft.studentNo.trim() || !classId) return
  pendingStudents.value.push({
    name: studentDraft.name.trim(),
    studentNo: studentDraft.studentNo.trim(),
    classId,
    password: studentDraft.password || '123456'
  })
  studentDraft.name = ''
  studentDraft.studentNo = ''
}

function removePendingStudent(studentNo) {
  pendingStudents.value = pendingStudents.value.filter(item => item.studentNo !== studentNo)
}

function confirmImportStudents() {
  if (!pendingStudents.value.length) return
  if (!window.confirm(`确认导入 ${pendingStudents.value.length} 个学生账号？`)) return
  emit('import-students', pendingStudents.value)
  pendingStudents.value = []
}

function addCourse() {
  const classId = resolveClassId(newCourse.classQuery)
  const teacherNum = resolveTeacherNo(newCourse.teacherQuery)
  const roomId = newCourse.roomQuery.trim() || '3-3-301'
  if (!newCourse.courseId.trim() || !newCourse.courseName.trim() || !classId || !teacherNum) return
  if (!window.confirm(`确认添加课程 ${newCourse.courseName} 到 ${className(classId)}？`)) return
  emit('add-course', {
    courseId: newCourse.courseId.trim(),
    classId,
    courseName: newCourse.courseName.trim(),
    teacher: teacherNum,
    teacherNum,
    weekday: newCourse.weekday.trim() || '周一',
    startTime: newCourse.startTime.trim() || '08:00',
    endTime: newCourse.endTime.trim() || '09:40',
    roomId,
    location: roomId,
    weekStart: Number(newCourse.weekStart) || 1,
    weekEnd: Number(newCourse.weekEnd) || 16,
    semester: newCourse.semester.trim() || '2025-2026-2',
    credit: Number(newCourse.credit) || 0,
    weeks: `${Number(newCourse.weekStart) || 1}-${Number(newCourse.weekEnd) || 16}周`
  })
  newCourse.courseId = nextCourseId()
  newCourse.courseName = ''
}

function confirmSaveCourseGrade(course, student) {
  const edit = gradeEdit(course, student)
  if (!window.confirm(`确认保存 ${student.name} 的 ${course.courseName} 成绩？`)) return
  persistGradeDraft(course, student, edit)
  emit('save-grade', {
    courseId: course.backendCourseId || course.courseId || course.id,
    studentNo: student.studentNo,
    regularScore: Number(edit.usual || 0),
    finalExamScore: Number(edit.final || 0),
    semester: course.semester || '2025-2026-2',
    examType: '期末考试',
    remark: edit.remark || ''
  })
}

function prepareClassNotice(targetClass) {
  noticeTarget.value = {
    type: 'class',
    classId: targetClass.id,
    label: `${targetClass.name} 全班学生`
  }
  noticeDraft.title = `${targetClass.name} 通知`
  noticeDraft.content = ''
}

function prepareCourseNotice(course) {
  noticeTarget.value = {
    type: 'course',
    classId: course.classId,
    courseId: course.backendCourseId || course.courseId || course.id,
    label: `${course.courseName} 课程学生`
  }
  noticeDraft.title = `${course.courseName} 课程通知`
  noticeDraft.content = ''
}

function sendNotice() {
  if (!noticeTarget.value || !noticeDraft.title.trim()) return
  if (!window.confirm(`确认向 ${noticeTarget.value.label} 发送通知？`)) return
  emit('send-notification', {
    ...noticeTarget.value,
    title: noticeDraft.title.trim(),
    content: noticeDraft.content.trim()
  })
  noticeTarget.value = null
  noticeDraft.title = ''
  noticeDraft.content = ''
}

function gradeEdit(course, student) {
  const key = gradeKey(course, student)
  if (!gradeEdits[key]) {
    const grade = findGrade(course, student)
    const stored = storedGradeDrafts[key] || {}
    gradeEdits[key] = {
      usual: grade?.regularScore ?? grade?.usual ?? grade?.usualScore ?? stored.usual ?? grade?.score ?? '',
      final: grade?.finalExamScore ?? grade?.final ?? stored.final ?? grade?.score ?? '',
      remark: grade?.remark ?? stored.remark ?? ''
    }
  }
  return gradeEdits[key]
}

function gradePointPreview(course, student) {
  const edit = gradeEdit(course, student)
  if (edit.final !== '' && edit.final != null) {
    return scoreToGradePoint(weightedScore(edit.usual, edit.final)).toFixed(2)
  }
  const grade = findGrade(course, student)
  if (grade?.gradePoint != null) return Number(grade.gradePoint).toFixed(2)
  return '-'
}

function findGrade(course, student) {
  const courseId = String(course.backendCourseId || course.courseId || course.id || '')
  return props.grades.find(grade => {
    const sameStudent = grade.studentNo === student.studentNo
    const sameCourse = String(grade.courseId || grade.backendCourseId || '') === courseId || grade.courseName === course.courseName
    return sameStudent && sameCourse
  })
}

function gradeKey(course, student) {
  return `${course.backendCourseId || course.courseId || course.id}-${student.studentNo}`
}

function persistGradeDraft(course, student, edit) {
  const key = gradeKey(course, student)
  storedGradeDrafts[key] = {
    usual: edit.usual ?? '',
    final: edit.final ?? '',
    remark: edit.remark ?? ''
  }
  saveStoredGradeDrafts(storedGradeDrafts)
}

function loadStoredGradeDrafts() {
  try {
    return JSON.parse(localStorage.getItem(GRADE_DRAFT_STORAGE_KEY) || '{}')
  } catch {
    return {}
  }
}

function saveStoredGradeDrafts(value) {
  localStorage.setItem(GRADE_DRAFT_STORAGE_KEY, JSON.stringify(value))
}

function classStudents(classId) {
  return props.students.filter(item => item.classId === classId)
}

function courseStudents(course) {
  if (Array.isArray(course.studentNos)) {
    const enrolled = new Set(course.studentNos)
    return props.students.filter(student => enrolled.has(student.studentNo))
  }
  return classStudents(course.classId)
}

function studentGpa(student) {
  if (student.gpa != null && Number(student.gpa) > 0) return Number(student.gpa).toFixed(2)
  const rows = props.grades.filter(grade => grade.studentNo === student.studentNo && grade.gradePoint != null)
  if (!rows.length) return '-'
  const avg = rows.reduce((sum, grade) => sum + Number(grade.gradePoint || 0), 0) / rows.length
  return avg.toFixed(2)
}

function isTeacherHeadOfClass(item) {
  const teacherNo = props.currentUser.teacherNo || props.currentUser.username
  const teacherName = props.currentUser.name
  return item.masterId === teacherNo || item.headTeacherNo === teacherNo || item.teacherNo === teacherNo || item.headTeacher === teacherName
}

function isTeacherCourse(course) {
  const teacherNo = props.currentUser.teacherNo || props.currentUser.username
  const teacherName = props.currentUser.name
  return course.teacherNo === teacherNo || course.teacherNum === teacherNo || course.teacher === teacherName
}

function teacherSuggestions(query) {
  const keyword = normalize(query)
  if (!keyword) return props.teachers.slice(0, 5)
  return props.teachers
    .filter(teacher => [teacher.name, teacher.teacherNo].some(value => normalize(value).includes(keyword)))
    .slice(0, 5)
}

function classSuggestions(query) {
  const keyword = normalize(query)
  if (!keyword) return props.classes.slice(0, 5)
  return props.classes
    .filter(item => [item.id, item.name, item.grade, item.major].some(value => normalize(value).includes(keyword)))
    .slice(0, 5)
}

function studentClassSuggestions(student) {
  const query = classQueries[student.id] ?? studentFilters.targetClass
  return classSuggestions(query).filter(item => item.id !== student.classId)
}

function roomSuggestions(query) {
  const keyword = normalize(query)
  if (!keyword) return props.rooms.slice(0, 5)
  return props.rooms
    .filter(room => [room.roomFull, room.label, room.area, room.building].some(value => normalize(value).includes(keyword)))
    .slice(0, 5)
}

function selectCourseRoom(room) {
  newCourse.roomQuery = room.roomFull
  roomSuggestionsOpen.value = false
}

function scheduleCloseRoomSuggestions() {
  window.setTimeout(() => {
    roomSuggestionsOpen.value = false
  }, 120)
}

function resolveTeacherNo(value) {
  const text = String(value || '').trim()
  const matched = props.teachers.find(teacher => teacher.teacherNo === text || formatTeacher(teacher) === text || teacher.name === text)
  return matched?.teacherNo || text
}

function resolveClassId(value) {
  const text = String(value || '').trim()
  const matched = props.classes.find(item => item.id === text || item.name === text || formatClass(item) === text)
  return matched?.id || text
}

function formatTeacher(teacher) {
  return `${teacher.teacherNo} · ${teacher.name}`
}

function formatClass(item) {
  return `${item.id} · ${item.name}`
}

function className(classId) {
  return props.classes.find(item => item.id === classId)?.name || classId || '未分配'
}

function paginate(rows, page) {
  const safePage = Math.max(1, Math.min(page, Math.max(1, Math.ceil(rows.length / pageSize))))
  const start = (safePage - 1) * pageSize
  return rows.slice(start, start + pageSize)
}

function totalPages(total) {
  return Math.max(1, Math.ceil(total / pageSize))
}

function scoreToGradePoint(score) {
  if (score >= 90) return 4.0
  if (score >= 85) return 3.7
  if (score >= 82) return 3.3
  if (score >= 78) return 3.0
  if (score >= 75) return 2.7
  if (score >= 72) return 2.3
  if (score >= 68) return 2.0
  if (score >= 64) return 1.5
  if (score >= 60) return 1.0
  return 0
}

function weightedScore(regularScore, finalExamScore) {
  if (regularScore === '' || regularScore == null) return Number(finalExamScore || 0)
  if (finalExamScore === '' || finalExamScore == null) return Number(regularScore || 0)
  const regular = Number(regularScore || 0)
  const final = Number(finalExamScore || 0)
  return Math.round((regular * 0.4 + final * 0.6) * 10) / 10
}

function nextCourseId() {
  return String(Date.now()).slice(-9)
}

function normalize(value) {
  return String(value || '').trim().toLowerCase()
}
</script>
