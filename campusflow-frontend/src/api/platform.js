import axios from 'axios'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

const platformClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000
})

const weekdayLabels = {
  1: '周一',
  2: '周二',
  3: '周三',
  4: '周四',
  5: '周五',
  6: '周六',
  7: '周日'
}

const weekdayValues = Object.entries(weekdayLabels).reduce((acc, [value, label]) => {
  acc[label] = Number(value)
  return acc
}, {})

export async function loadPlatformSnapshot() {
  const [studentsRes, teachersRes, coursesRes, roomsRes, enrollmentsRes, classesRes, classmatesRes] = await Promise.all([
    platformClient.get('/api/students'),
    platformClient.get('/api/teacher'),
    platformClient.get('/api/course'),
    platformClient.get('/api/room'),
    platformClient.get('/api/class-stu'),
    safeGet('/api/classi', { Classes: [] }),
    safeGet('/api/classmate', { alls: [] })
  ])

  const classmates = normalizeClassmates(getFirstArray(classmatesRes.data, ['alls', 'classmates', 'relations']))
  const students = normalizeStudents(studentsRes.data?.students || [], classmates)
  const teachers = normalizeTeachers(teachersRes.data?.teacher || [])
  const rooms = normalizeRooms(roomsRes.data?.rooms || [])
  const enrollments = normalizeEnrollments(enrollmentsRes.data?.enrollments || [])
  const courses = normalizeCourses(
    coursesRes.data?.Courses || coursesRes.data?.courses || [],
    enrollments,
    students,
    teachers
  )
  const classes = mergeClasses(
    normalizeClasses(getFirstArray(classesRes.data, ['Classes', 'classes', 'classi']), students, teachers),
    students,
    courses
  )

  return {
    classes,
    students,
    teachers,
    courses,
    rooms,
    enrollments,
    classmates
  }
}

export async function loginPlatformUser({ role, username, password }) {
  const account = username.trim()
  const loginRole = role || 'student'

  if (loginRole === 'student') {
    await platformClient.post('/api/students/login', {
      StuNum: account,
      password
    })
    const { data } = await platformClient.get('/api/students')
    const student = normalizeStudents(data?.students || []).find(item => item.studentNo === account)
    if (!student) throw new Error('登录成功，但没有找到对应学生信息。')

    return {
      id: student.userId,
      username: student.studentNo,
      role: 'student',
      name: student.name,
      studentNo: student.studentNo,
      classId: student.classId
    }
  }

  if (loginRole === 'admin') {
    await platformClient.post('/api/admin/login', {
      Number: account,
      password
    })
    const { data } = await platformClient.get('/api/admin')
    const admin = (data?.admin || []).find(item => String(item.Number) === account)

    return {
      id: `admin-${account}`,
      username: account,
      role: 'admin',
      authRole: 'admin',
      name: admin?.Name || '管理员',
      teacherNo: account,
      classIds: []
    }
  }

  await platformClient.post('/api/teacher/login', {
    Number: account,
    password
  })
  const { data } = await platformClient.get('/api/teacher')
  const teacher = normalizeTeachers(data?.teacher || []).find(item => item.teacherNo === account)
  if (!teacher) throw new Error('登录成功，但没有找到对应教师信息。')

  return {
    id: teacher.id,
    username: teacher.username,
    role: 'teacher',
    name: teacher.name,
    teacherNo: teacher.teacherNo,
    classIds: []
  }
}

export async function registerPlatformUser({ role, name, username, password, className }) {
  const account = username.trim()
  const displayName = name.trim()
  const registerRole = role || 'student'

  if (registerRole === 'student') {
    await platformClient.post('/api/students/register', {
      Name: displayName,
      StuNum: account,
      Cls: className?.trim() || '未分配',
      password
    })
    return loginPlatformUser({ role: 'student', username: account, password })
  }

  if (registerRole === 'admin') {
    await platformClient.post('/api/admin/register', {
      Name: displayName,
      Number: account,
      password
    })
    return loginPlatformUser({ role: 'admin', username: account, password })
  }

  await platformClient.post('/api/teacher/register', {
    Name: displayName,
    Number: account,
    password
  })
  return loginPlatformUser({ role: 'teacher', username: account, password })
}

export async function loadRealtimeWeather() {
  const latitude = import.meta.env.VITE_WEATHER_LAT || '30.5928'
  const longitude = import.meta.env.VITE_WEATHER_LON || '114.3055'
  const city = import.meta.env.VITE_WEATHER_CITY || '武汉'
  const params = new URLSearchParams({
    latitude,
    longitude,
    current: 'temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m',
    timezone: 'Asia/Shanghai'
  })

  const response = await fetch(`https://api.open-meteo.com/v1/forecast?${params.toString()}`)
  if (!response.ok) throw new Error(`天气接口返回 ${response.status}`)
  const data = await response.json()
  const current = data.current || {}

  return {
    city,
    weather: weatherCodeLabel(current.weather_code),
    temperature: current.temperature_2m == null ? '未知' : `${Math.round(current.temperature_2m)}℃`,
    wind: current.wind_speed_10m == null ? '风力未知' : `${Math.round(current.wind_speed_10m)} km/h`,
    humidity: current.relative_humidity_2m == null ? null : `${current.relative_humidity_2m}%`,
    updatedAt: current.time ? `实时 ${current.time.replace('T', ' ')}` : '实时数据'
  }
}

export async function updateStudentClass(studentId, classId) {
  const studentNo = String(studentId)
  try {
    const { data } = await platformClient.patch('/api/classmate/change_info', {
      stu_num: studentNo,
      class_id: classId
    })
    return data
  } catch (error) {
    const status = error?.response?.status
    if (status && status !== 404) throw error
  }

  try {
    const { data } = await platformClient.patch(`/api/students/${studentNo}/Cls`, null, {
      params: {
        newcls: classId
      }
    })
    await createClassmate(studentNo, classId)
    return data
  } catch (error) {
    const detail = String(error?.response?.data?.detail || '')
    if (error?.response?.status === 400 && detail.includes('not been changed')) {
      await createClassmate(studentNo, classId)
      return { message: 'class unchanged, classmate relation synced if needed' }
    }
    throw error
  }
}

export async function createClass(classInfo) {
  const { data } = await platformClient.post('/api/classi/add', toBackendClass(classInfo))
  return data
}

export async function createCourse(course) {
  const backendCourse = toBackendCourse(course)
  const { data } = await platformClient.post('/api/course/add', backendCourse)
  return data
}

export async function enrollStudent(courseId, studentNo) {
  const { data } = await platformClient.post('/api/class-stu/enroll', {
    course_id: String(courseId),
    stu_num: String(studentNo)
  })
  return data
}

export async function createTodoItem(userId, todo) {
  const { data } = await platformClient.post('/api/todo/add', {
    user_id: String(userId),
    title: todo.title,
    description: todo.description || todo.note || '',
    date: todo.date || todo.dueDate,
    priority: todo.priority || 'medium'
  })
  return normalizeTodo(data.todo)
}

export async function loadTodosForUser(user) {
  const userId = getBackendUserId(user)
  if (!userId) return []

  if (user.role === 'admin') {
    const { data } = await platformClient.get('/api/todo', {
      params: {
        limit: 500,
        offset: 0
      }
    })
    return normalizeTodos(data?.todos || [])
  }

  const { data } = await platformClient.get(`/api/todo/user/${encodeURIComponent(userId)}`)
  return normalizeTodos(data?.todos || [])
}

export async function updateTodoItemStatus(todoId, status) {
  const { data } = await platformClient.patch(`/api/todo/${todoId}/status`, {
    status: toBackendTodoStatus(status)
  })
  return normalizeTodo(data.todo)
}

export async function deleteTodoItem(todoId) {
  const { data } = await platformClient.delete('/api/todo/delete', {
    params: {
      todo_id: todoId
    }
  })
  return data
}

export async function loadGradesForUser(user, context = {}) {
  if (!user) return { grades: [], summary: null }

  if (user.role === 'student') {
    const studentNo = user.studentNo || user.username
    if (!studentNo) return { grades: [], summary: null }
    const [gradesRes, gpaRes] = await Promise.all([
      platformClient.get(`/api/grade/student/${encodeURIComponent(studentNo)}`),
      safeGet(`/api/students/${encodeURIComponent(studentNo)}/gpa`, null)
    ])
    return {
      grades: normalizeStudentGrades(gradesRes.data?.grades || [], gradesRes.data),
      summary: gpaRes.data ? normalizeGpaSummary(gpaRes.data) : null
    }
  }

  if (user.role === 'teacher') {
    const teacherNo = user.teacherNo || user.username
    if (!teacherNo) return { grades: [], summary: null }
    const { data } = await platformClient.get(`/api/grade/teacher/${encodeURIComponent(teacherNo)}`)
    return {
      grades: normalizeTeacherGrades(data?.courses || [], context),
      summary: {
        teacherName: data?.teacher_name || user.name,
        courseCount: data?.count || 0
      }
    }
  }

  const { data } = await platformClient.get('/api/grade')
  return {
    grades: normalizeAdminGrades(data?.grades || [], context),
    summary: {
      count: data?.count || 0
    }
  }
}

export async function saveGradeRecord(grade) {
  const payload = toBackendGrade(grade)
  try {
    const { data } = await platformClient.post('/api/grade/add', payload)
    await refreshGpaCache().catch(() => null)
    return data
  } catch (error) {
    const detail = String(error?.response?.data?.detail || '')
    if (error?.response?.status === 400 && detail.includes('already exist')) {
      const { data } = await platformClient.patch('/api/grade/modify', payload)
      await refreshGpaCache().catch(() => null)
      return data
    }
    throw error
  }
}

export async function refreshGpaCache() {
  const { data } = await platformClient.post('/api/students/gpa/refresh')
  return data
}

export async function registerStudentAccount(student) {
  const classId = student.classId || student.Cls || student.className || '未分配'
  const studentNo = String(student.studentNo || student.StuNum || student.username || '').trim()
  const name = String(student.name || student.Name || '').trim()
  const password = String(student.password || '123456')

  const { data } = await platformClient.post('/api/students/register', {
    Name: name,
    StuNum: studentNo,
    Cls: classId,
    password
  })

  await createClassmate(studentNo, classId)
  return data
}

export function toBackendCourse(course) {
  return {
    course_id: String(course.courseId || course.backendCourseId || Date.now()),
    day: weekdayValues[course.weekday] || Number(course.day) || 1,
    start_time: course.startTime || course.start_time || '08:00',
    end_time: course.endTime || course.end_time || '09:40',
    course_name: course.courseName || course.course_name || '未命名课程',
    teacher_num: String(course.teacherNum || course.teacher_num || course.teacherNo || course.teacher || '待定'),
    room_id: course.roomId || course.location || course.room_id || '3-3-301',
    week_start: Number(course.weekStart || course.week_start || 1),
    week_end: Number(course.weekEnd || course.week_end || 16),
    semester: course.semester || '2025-2026-2',
    credit: Number(course.credit || course.courseCredit || 0)
  }
}

function toBackendClass(classInfo) {
  const classId = String(classInfo.classId || classInfo.id || classInfo.name || Date.now())
  return {
    class_id: classId,
    name: classInfo.name || classId,
    master_id: String(classInfo.masterId || classInfo.teacherNo || classInfo.headTeacherNo || '未分配'),
    capacity: Number(classInfo.capacity || 45)
  }
}

async function createClassmate(studentNo, classId) {
  try {
    await platformClient.post('/api/classmate/add', {
      stu_num: studentNo,
      class_id: classId
    })
  } catch {
    // 班级成员关系是新接口；学生表已更新成功时，这里允许前端继续使用。
  }
}

async function safeGet(url, fallbackData) {
  try {
    return await platformClient.get(url)
  } catch {
    return { data: fallbackData }
  }
}

function getFirstArray(data, keys) {
  for (const key of keys) {
    if (Array.isArray(data?.[key])) return data[key]
  }
  return []
}

function normalizeStudents(rows, classmates = []) {
  const classByStudent = new Map(
    classmates.map(item => [item.studentNo, item.classId])
  )

  return rows.map(row => ({
    id: row.id || `student-${row.StuNum}`,
    backendId: String(row.StuNum || ''),
    recordId: row.id,
    userId: `student-${row.StuNum}`,
    name: row.Name || '未命名学生',
    studentNo: String(row.StuNum || ''),
    classId: classByStudent.get(String(row.StuNum || '')) || row.Cls || '未分配',
    gpa: Number(row.gpa || 0),
    raw: row
  }))
}

function normalizeTeachers(rows) {
  return rows.map(row => ({
    id: `teacher-${row.Number}`,
    backendId: row.id,
    role: 'teacher',
    name: row.Name || '未命名教师',
    teacherNo: String(row.Number || ''),
    username: String(row.Number || ''),
    raw: row
  }))
}

function normalizeRooms(rows) {
  return rows.map(row => {
    const roomFull = row.room_full || `${row.area}-${row.building}-${row.room_id}`
    return {
      id: row.id,
      area: row.area,
      building: row.building,
      roomId: row.room_id,
      roomFull,
      label: `${roomFull}${row.capacity ? `（${row.capacity}人）` : ''}`,
      raw: row
    }
  })
}

function normalizeEnrollments(rows) {
  return rows.map(row => ({
    id: row.id,
    courseId: String(row.course_id),
    studentNo: String(row.stu_num || ''),
    raw: row
  }))
}

function normalizeClassmates(rows) {
  return rows.map(row => ({
    id: row.id || `${row.class_id}-${row.stu_num}`,
    classId: String(row.class_id || row.Cls || '未分配'),
    studentNo: String(row.stu_num || row.StuNum || ''),
    raw: row
  })).filter(item => item.studentNo)
}

function normalizeClasses(rows, students, teachers) {
  const teacherByNo = new Map(teachers.map(teacher => [teacher.teacherNo, teacher]))

  return rows.map(row => {
    const classId = String(row.class_id || row.id || row.name || '')
    const masterId = String(row.master_id || row.teacher_num || '')
    const studentCount = students.filter(student => student.classId === classId).length
    const teacher = teacherByNo.get(masterId)

    return {
      id: classId,
      name: row.name || classId || '未命名班级',
      grade: inferGrade(row.name || classId),
      major: inferMajor(row.name || classId),
      headTeacher: teacher?.name || masterId || '待分配',
      masterId,
      capacity: Number(row.capacity || 0),
      studentCount,
      raw: row
    }
  }).filter(item => item.id)
}

function normalizeCourses(rows, enrollments, students, teachers) {
  const studentByNo = new Map(students.map(student => [student.studentNo, student]))
  const teacherByNo = new Map(teachers.map(teacher => [teacher.teacherNo, teacher]))
  const classIdsByCourse = new Map()

  for (const enrollment of enrollments) {
    const student = studentByNo.get(enrollment.studentNo)
    if (!student) continue
    if (!classIdsByCourse.has(enrollment.courseId)) {
      classIdsByCourse.set(enrollment.courseId, new Set())
    }
    classIdsByCourse.get(enrollment.courseId).add(student.classId)
  }

  return rows.flatMap(row => {
    const backendCourseId = String(row.course_id || row.id)
    const classIds = [...(classIdsByCourse.get(backendCourseId) || ['未分班课程'])]
    const teacherNo = String(row.teacher_num || row.teacherNo || '')
    const teacher = teacherByNo.get(teacherNo)

    return classIds.map(classId => ({
      id: `course-${backendCourseId}-${classId}`,
      backendId: row.id,
      backendCourseId,
      classId,
      courseName: row.course_name || '未命名课程',
      teacher: teacher?.name || row.teacher_name || teacherNo || '待定',
      teacherNo,
      weekday: weekdayLabels[Number(row.day)] || `周${row.day || '?'}`,
      startTime: row.start_time || '',
      endTime: row.end_time || '',
      location: row.room_id || '待定',
      roomId: row.room_id || '',
      weekStart: row.week_start,
      weekEnd: row.week_end,
      weeks: `${row.week_start || 1}-${row.week_end || 16}周`,
      semester: row.semester || '',
      credit: Number(row.credit || 0),
      raw: row
    }))
  })
}

function normalizeTodos(rows) {
  return rows.map(normalizeTodo).filter(Boolean)
}

function normalizeTodo(row = {}) {
  if (!row) return null
  return {
    id: row.id,
    backendId: row.id,
    userId: String(row.user_id || ''),
    title: row.title || '未命名待办',
    dueDate: row.date || '',
    date: row.date || '',
    status: toFrontendTodoStatus(row.status),
    category: row.category || '个人',
    source: row.source || '后端同步',
    priority: row.priority || 'medium',
    note: row.description || row.note || '',
    createdAt: row.created_at || '',
    updatedAt: row.updated_at || '',
    raw: row
  }
}

function normalizeStudentGrades(rows, payload = {}) {
  return rows.map(row => ({
    id: row.id || `${row.course_id}-${payload.stu_num}-${row.semester}`,
    backendId: row.id,
    studentNo: payload.stu_num,
    studentName: payload.name,
    classId: payload.cls,
    courseId: String(row.course_id || ''),
    courseName: row.course_name || String(row.course_id || ''),
    credit: Number(row.credit || 0),
    score: Number(row.score || 0),
    gradePoint: Number(row.grade_point || 0),
    gradeLetter: row.grade_letter || '',
    semester: row.semester || '',
    examType: row.exam_type || '',
    remark: row.remark || '',
    raw: row
  }))
}

function normalizeTeacherGrades(courses, context = {}) {
  return courses.flatMap(course => {
    const students = Array.isArray(course.students) ? course.students : []
    return students.map(student => normalizeGradeRow({
      ...student,
      course_id: course.course_id,
      course_name: course.course_name,
      credit: course.credit,
      semester: student.semester || course.semester
    }, context))
  })
}

function normalizeAdminGrades(rows, context = {}) {
  return rows.map(row => normalizeGradeRow(row, context))
}

function normalizeGradeRow(row, context = {}) {
  const courseId = String(row.course_id || '')
  const studentNo = String(row.stu_num || row.studentNo || '')
  const course = (context.courses || []).find(item => item.backendCourseId === courseId || item.courseId === courseId)
  const student = (context.students || []).find(item => item.studentNo === studentNo)

  return {
    id: row.id || `${courseId}-${studentNo}-${row.semester || ''}`,
    backendId: row.id,
    studentNo,
    studentName: row.name || student?.name || studentNo,
    classId: row.cls || student?.classId || '',
    courseId,
    courseName: row.course_name || course?.courseName || courseId,
    credit: Number(row.credit ?? course?.credit ?? 0),
    score: Number(row.score || 0),
    gradePoint: Number(row.grade_point || 0),
    gradeLetter: row.grade_letter || '',
    semester: row.semester || course?.semester || '',
    examType: row.exam_type || '',
    remark: row.remark || '',
    raw: row
  }
}

function normalizeGpaSummary(data = {}) {
  return {
    gpa: Number(data.gpa || 0),
    totalCreditsTaken: Number(data.total_credits_taken || 0),
    totalCreditsEarned: Number(data.total_credits_earned || 0),
    courseCount: Number(data.course_count || 0),
    bySemester: data.by_semester || {}
  }
}

function toBackendGrade(grade) {
  return {
    course_id: String(grade.courseId || grade.course_id || ''),
    stu_num: String(grade.studentNo || grade.stu_num || ''),
    score: Number(grade.score || 0),
    semester: grade.semester || '2025-2026-2',
    exam_type: grade.examType || grade.exam_type || '期末考试',
    remark: grade.remark || ''
  }
}

function getBackendUserId(user = {}) {
  return user.studentNo || user.teacherNo || user.username || user.id || ''
}

function toFrontendTodoStatus(status) {
  if (status === 'completed') return 'done'
  return status || 'pending'
}

function toBackendTodoStatus(status) {
  if (status === 'done') return 'completed'
  return status || 'pending'
}

function mergeClasses(backendClasses, students, courses) {
  const classMap = new Map(backendClasses.map(item => [item.id, item]))
  const classIds = unique([
    ...students.map(student => student.classId).filter(Boolean),
    ...courses.map(course => course.classId).filter(Boolean)
  ])

  for (const classId of classIds) {
    if (classMap.has(classId)) continue
    classMap.set(classId, {
      id: classId,
      name: classId,
      grade: inferGrade(classId),
      major: '后端学生表',
      headTeacher: '待分配',
      capacity: 0
    })
  }

  return [...classMap.values()]
}

function inferGrade(value) {
  return String(value || '').match(/20\d{2}/)?.[0]
    ? `${String(value).match(/20\d{2}/)[0]}级`
    : '数据库'
}

function inferMajor(value) {
  const text = String(value || '')
  return text.replace(/20\d{2}级?/g, '').replace(/[0-9一二三四五六七八九十]+班/g, '').trim() || '班级主数据'
}

function unique(values) {
  return [...new Set(values)]
}

function weatherCodeLabel(code) {
  const labels = {
    0: '晴',
    1: '多云',
    2: '多云',
    3: '阴',
    45: '雾',
    48: '雾凇',
    51: '小毛毛雨',
    53: '毛毛雨',
    55: '大毛毛雨',
    61: '小雨',
    63: '中雨',
    65: '大雨',
    71: '小雪',
    73: '中雪',
    75: '大雪',
    80: '阵雨',
    81: '强阵雨',
    82: '暴雨',
    95: '雷暴',
    96: '雷暴伴冰雹',
    99: '强雷暴伴冰雹'
  }
  return labels[Number(code)] || '天气未知'
}
