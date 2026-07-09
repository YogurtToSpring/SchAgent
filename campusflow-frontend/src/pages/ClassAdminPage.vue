<template>
  <section class="admin-page">
    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h2>班级管理</h2>
          <p>维护班级、学生归属和教学组织。</p>
        </div>
      </div>

      <form class="inline-form" @submit.prevent="addClass">
        <input v-model="newClass.name" placeholder="班级名称，例如 软件工程2班" />
        <input v-model="newClass.major" placeholder="专业，例如 软件工程" />
        <input v-model="newClass.grade" placeholder="年级，例如 2024级" />
        <button class="primary-action compact" type="submit">创建班级</button>
      </form>

      <div class="data-table-wrap">
        <table>
          <thead>
            <tr>
              <th>班级</th>
              <th>年级</th>
              <th>专业</th>
              <th>班主任</th>
              <th>学生数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in classes" :key="item.id">
              <td>{{ item.name }}</td>
              <td>{{ item.grade }}</td>
              <td>{{ item.major }}</td>
              <td>{{ item.headTeacher }}</td>
              <td>{{ countStudents(item.id) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h2>学生班级分配</h2>
          <p>调整学生所属班级后，课表和助手上下文同步更新。</p>
        </div>
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
            <tr v-for="student in students" :key="student.id">
              <td>{{ student.name }}</td>
              <td>{{ student.studentNo }}</td>
              <td>{{ className(student.classId) }}</td>
              <td>
                <select :value="student.classId" @change="assignStudent(student.id, $event.target.value)">
                  <option v-for="item in classes" :key="item.id" :value="item.id">
                    {{ item.name }}
                  </option>
                </select>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h2>课表导入与调整</h2>
          <p>维护课程、教师、教室和周次。</p>
        </div>
      </div>

      <form class="course-form" @submit.prevent="addCourse">
        <input v-model="newCourse.courseId" placeholder="课程编号，例如 123456" />
        <select v-model="newCourse.classId">
          <option v-for="item in classes" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
        <input v-model="newCourse.courseName" placeholder="课程名称" />
        <select v-if="teachers.length" v-model="newCourse.teacher">
          <option v-for="teacher in teachers" :key="teacher.teacherNo" :value="teacher.teacherNo">
            {{ teacher.name }}（{{ teacher.teacherNo }}）
          </option>
        </select>
        <input v-else v-model="newCourse.teacher" placeholder="任课教师编号" />
        <select v-model="newCourse.weekday">
          <option>周一</option>
          <option>周二</option>
          <option>周三</option>
          <option>周四</option>
          <option>周五</option>
        </select>
        <input v-model="newCourse.startTime" placeholder="开始时间 08:00" />
        <input v-model="newCourse.endTime" placeholder="结束时间 09:40" />
        <select v-if="rooms.length" v-model="newCourse.roomId">
          <option v-for="room in rooms" :key="room.roomFull" :value="room.roomFull">
            {{ room.label }}
          </option>
        </select>
        <input v-else v-model="newCourse.roomId" placeholder="教室，例如 3-3-301" />
        <input v-model="newCourse.weekStart" placeholder="起始周 1" />
        <input v-model="newCourse.weekEnd" placeholder="结束周 16" />
        <input v-model="newCourse.semester" placeholder="学期 2025-2026-2" />
        <button class="primary-action compact" type="submit">添加课程</button>
      </form>
    </section>
  </section>
</template>

<script setup>
import { reactive, watch } from 'vue'

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
  currentUser: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['add-class', 'assign-student', 'add-course'])

const newClass = reactive({
  name: '',
  major: '',
  grade: '2024级'
})

const newCourse = reactive({
  courseId: nextCourseId(),
  classId: props.classes[0]?.id || '',
  courseName: '',
  teacher: defaultTeacherNo(),
  weekday: '周一',
  startTime: '08:00',
  endTime: '09:40',
  roomId: props.rooms[0]?.roomFull || '3-3-301',
  weekStart: '1',
  weekEnd: '16',
  semester: '2025-2026-2'
})

watch(
  () => props.classes,
  value => {
    if (!newCourse.classId && value[0]?.id) {
      newCourse.classId = value[0].id
    }
  },
  { immediate: true }
)

watch(
  () => props.rooms,
  value => {
    if (value[0]?.roomFull && (!newCourse.roomId || newCourse.roomId === '3-3-301')) {
      newCourse.roomId = value[0].roomFull
    }
  },
  { immediate: true }
)

watch(
  () => props.teachers,
  () => {
    if (!newCourse.teacher) {
      newCourse.teacher = defaultTeacherNo()
    }
  },
  { immediate: true }
)

function addClass() {
  if (!newClass.name.trim()) return
  emit('add-class', {
    classId: newClass.name.trim(),
    name: newClass.name.trim(),
    major: newClass.major.trim() || '未设置',
    grade: newClass.grade.trim() || '2024级',
    headTeacher: props.currentUser.name,
    headTeacherNo: props.currentUser.teacherNo,
    teacherNo: props.currentUser.teacherNo,
    masterId: props.currentUser.teacherNo,
    capacity: 45
  })
  newClass.name = ''
  newClass.major = ''
}

function assignStudent(studentId, classId) {
  emit('assign-student', { studentId, classId })
}

function addCourse() {
  const teacherNum = newCourse.teacher.trim() || defaultTeacherNo()
  if (!newCourse.classId || !newCourse.courseId.trim() || !newCourse.courseName.trim() || !teacherNum) return
  emit('add-course', {
    ...newCourse,
    courseId: newCourse.courseId.trim(),
    courseName: newCourse.courseName.trim(),
    teacher: teacherNum,
    teacherNum,
    roomId: newCourse.roomId.trim() || '3-3-301',
    location: newCourse.roomId.trim() || '3-3-301',
    weekStart: Number(newCourse.weekStart) || 1,
    weekEnd: Number(newCourse.weekEnd) || 16,
    semester: newCourse.semester.trim() || '2025-2026-2',
    weeks: `${Number(newCourse.weekStart) || 1}-${Number(newCourse.weekEnd) || 16}周`
  })
  newCourse.courseId = nextCourseId()
  newCourse.courseName = ''
  newCourse.teacher = defaultTeacherNo()
  newCourse.weekStart = '1'
  newCourse.weekEnd = '16'
}

function countStudents(classId) {
  return props.students.filter(item => item.classId === classId).length
}

function className(classId) {
  return props.classes.find(item => item.id === classId)?.name || '未分配'
}

function nextCourseId() {
  return String(Date.now()).slice(-9)
}

function defaultTeacherNo() {
  if (props.currentUser.role === 'teacher') return props.currentUser.teacherNo || ''
  return props.teachers[0]?.teacherNo || ''
}
</script>
