<template>
  <section class="admin-page">
    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h2>班级管理</h2>
          <p>教师管理员可以维护班级，并把学生分配到指定班级。</p>
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
          <p>模拟学校平台中的学生归属维护。</p>
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
          <p>当前版本用表单模拟导入，后续可替换为 Excel、CSV 或教务系统接口。</p>
        </div>
      </div>

      <form class="course-form" @submit.prevent="addCourse">
        <select v-model="newCourse.classId">
          <option v-for="item in classes" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
        <input v-model="newCourse.courseName" placeholder="课程名称" />
        <input v-model="newCourse.teacher" placeholder="任课教师" />
        <select v-model="newCourse.weekday">
          <option>周一</option>
          <option>周二</option>
          <option>周三</option>
          <option>周四</option>
          <option>周五</option>
        </select>
        <input v-model="newCourse.startTime" placeholder="开始时间 08:00" />
        <input v-model="newCourse.endTime" placeholder="结束时间 09:40" />
        <input v-model="newCourse.location" placeholder="地点" />
        <button class="primary-action compact" type="submit">添加课程</button>
      </form>
    </section>
  </section>
</template>

<script setup>
import { reactive } from 'vue'

const props = defineProps({
  classes: {
    type: Array,
    required: true
  },
  students: {
    type: Array,
    required: true
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
  classId: props.classes[0]?.id || '',
  courseName: '',
  teacher: '',
  weekday: '周一',
  startTime: '08:00',
  endTime: '09:40',
  location: ''
})

function addClass() {
  if (!newClass.name.trim()) return
  emit('add-class', {
    name: newClass.name.trim(),
    major: newClass.major.trim() || '未设置',
    grade: newClass.grade.trim() || '2024级',
    headTeacher: props.currentUser.name
  })
  newClass.name = ''
  newClass.major = ''
}

function assignStudent(studentId, classId) {
  emit('assign-student', { studentId, classId })
}

function addCourse() {
  if (!newCourse.classId || !newCourse.courseName.trim()) return
  emit('add-course', {
    ...newCourse,
    courseName: newCourse.courseName.trim(),
    teacher: newCourse.teacher.trim() || props.currentUser.name,
    location: newCourse.location.trim() || '待定',
    weeks: '1-16周'
  })
  newCourse.courseName = ''
  newCourse.teacher = ''
  newCourse.location = ''
}

function countStudents(classId) {
  return props.students.filter(item => item.classId === classId).length
}

function className(classId) {
  return props.classes.find(item => item.id === classId)?.name || '未分配'
}
</script>
