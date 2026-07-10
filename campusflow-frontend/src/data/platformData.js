export const initialClasses = [
  {
    id: 'class-se-1',
    name: '软件工程1班',
    grade: '2024级',
    major: '软件工程',
    headTeacher: '林老师'
  },
  {
    id: 'class-ai-1',
    name: '人工智能1班',
    grade: '2024级',
    major: '人工智能',
    headTeacher: '林老师'
  }
]

export const initialStudents = [
  {
    id: 'stu-001',
    userId: 'student-2024001',
    name: '赵同学',
    studentNo: '2024001',
    classId: 'class-se-1'
  },
  {
    id: 'stu-002',
    name: '陈同学',
    studentNo: '2024002',
    classId: 'class-se-1'
  },
  {
    id: 'stu-003',
    name: '周同学',
    studentNo: '2024003',
    classId: 'class-ai-1'
  }
]

export const initialCourses = [
  {
    id: 'course-001',
    classId: 'class-se-1',
    courseName: '高等数学',
    teacher: '王老师',
    weekday: '周一',
    startTime: '08:00',
    endTime: '09:40',
    location: '三教302',
    weeks: '1-16周'
  },
  {
    id: 'course-002',
    classId: 'class-se-1',
    courseName: '数据库原理',
    teacher: '李老师',
    weekday: '周三',
    startTime: '10:00',
    endTime: '11:40',
    location: '二教205',
    weeks: '1-16周'
  },
  {
    id: 'course-003',
    classId: 'class-se-1',
    courseName: '软件工程导论',
    teacher: '林老师',
    weekday: '周五',
    startTime: '14:00',
    endTime: '15:40',
    location: '实验楼A403',
    weeks: '1-12周'
  },
  {
    id: 'course-004',
    classId: 'class-ai-1',
    courseName: 'Python程序设计',
    teacher: '刘老师',
    weekday: '周二',
    startTime: '08:00',
    endTime: '09:40',
    location: '实验楼B201',
    weeks: '1-16周'
  }
]

export const weatherSnapshot = {
  city: '校园本部',
  weather: '小雨',
  temperature: '23-28℃',
  wind: '东北风 2 级',
  updatedAt: '今日 08:00'
}

export function cloneData(value) {
  return JSON.parse(JSON.stringify(value))
}
