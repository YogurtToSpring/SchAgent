import axios from 'axios'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL

export async function sendMessage(payload) {
  if (!apiBaseUrl) {
    return mockChatResponse(payload)
  }

  const { data } = await axios.post(`${apiBaseUrl}/api/chat`, payload, {
    timeout: 30000
  })
  return data
}

async function mockChatResponse({ session_id, message, user_context, platform_context }) {
  await wait(650)

  const text = message.trim()
  const sessionId = session_id || `mock-${Date.now()}`
  const role = user_context?.role || 'student'

  if (needsDate(text)) {
    return {
      session_id: sessionId,
      status: 'need_clarification',
      answer: '我还需要知道你想查询哪一天。可以直接回复“今天”“明天”或具体日期。',
      missing_fields: ['date'],
      steps: ['识别任务：课程查询', '发现缺少必要条件：日期'],
      tool_calls: [],
      artifacts: []
    }
  }

  if (role === 'teacher' && (text.includes('班') || text.includes('冲突') || text.includes('提醒'))) {
    return teacherClassResponse(sessionId, platform_context)
  }

  if (text.includes('学习计划') || text.includes('复习') || text.includes('考试')) {
    return studyPlanResponse(sessionId)
  }

  if (text.includes('骑车') || text.includes('天气') || text.includes('出门')) {
    return commuteResponse(sessionId)
  }

  return courseResponse(sessionId)
}

function teacherClassResponse(sessionId, platformContext = {}) {
  const targetClass = platformContext.classes?.find(item => item.name.includes('软件工程1班')) ||
    platformContext.classes?.[0] || {
      id: 'class-se-1',
      name: '软件工程1班'
    }
  const courses = (platformContext.courses || []).filter(item => item.classId === targetClass.id)

  return {
    session_id: sessionId,
    status: 'success',
    answer:
      `已按教师权限查询 **${targetClass.name}** 的课表。当前未发现明显时间冲突；如果需要，我可以继续生成班级课程提醒。`,
    steps: [
      '识别任务：班级课表查询 / 冲突检查',
      '校验当前用户角色：教师管理员',
      '调用班级查询工具',
      '调用班级课表查询工具',
      '调用课表冲突检测工具',
      '生成面向教师的处理建议'
    ],
    tool_calls: [
      {
        tool: 'class_query',
        label: '班级查询',
        status: 'success',
        input: {
          class_name: targetClass.name
        },
        output: {
          class_id: targetClass.id,
          class_name: targetClass.name
        }
      },
      {
        tool: 'class_schedule_query',
        label: '班级课表查询',
        status: 'success',
        input: {
          class_id: targetClass.id,
          range: '本周'
        },
        output: {
          course_count: courses.length,
          courses: courses.map(item => `${item.weekday} ${item.startTime}-${item.endTime} ${item.courseName}`)
        }
      },
      {
        tool: 'schedule_conflict_check',
        label: '课表冲突检测',
        status: 'success',
        input: {
          class_id: targetClass.id
        },
        output: {
          has_conflict: false,
          message: '未发现同一时间段重复课程'
        }
      }
    ],
    artifacts: [
      {
        type: 'table',
        title: `${targetClass.name}课表摘要`,
        columns: ['星期', '时间', '课程', '地点'],
        rows: courses.map(item => [
          item.weekday,
          `${item.startTime}-${item.endTime}`,
          item.courseName,
          item.location
        ])
      }
    ]
  }
}

function courseResponse(sessionId) {
  return {
    session_id: sessionId,
    status: 'success',
    answer:
      '明天上午有 **高等数学**，时间是 08:00-09:40，地点在三教302。建议 07:40 从宿舍出发，留出到教室和课前准备时间。',
    steps: [
      '识别任务：查询明天上午课程',
      '调用课程查询工具',
      '整理课程时间、地点和教师信息',
      '生成最终回答'
    ],
    tool_calls: [
      {
        tool: 'course_query',
        label: '课程查询',
        status: 'success',
        input: {
          date: '明天',
          time_range: '上午'
        },
        output: {
          course_name: '高等数学',
          time: '08:00-09:40',
          location: '三教302',
          teacher: '王老师'
        }
      }
    ],
    artifacts: [
      {
        type: 'table',
        title: '明日课程安排',
        columns: ['课程', '时间', '地点', '教师'],
        rows: [['高等数学', '08:00-09:40', '三教302', '王老师']]
      }
    ]
  }
}

function commuteResponse(sessionId) {
  return {
    session_id: sessionId,
    status: 'success',
    answer:
      '明天上午有 **高等数学**，天气为小雨，宿舍到三教步行约 12 分钟、骑车约 5 分钟。综合天气和路面情况，建议步行，07:40 出门更稳妥。',
    steps: [
      '识别任务：课程查询 + 天气查询 + 出行建议',
      '调用课程查询工具',
      '调用天气查询工具',
      '调用地点距离工具',
      '综合课程、天气和距离生成建议'
    ],
    tool_calls: [
      {
        tool: 'course_query',
        label: '课程查询',
        status: 'success',
        input: {
          date: '明天',
          time_range: '上午'
        },
        output: {
          course_name: '高等数学',
          time: '08:00-09:40',
          location: '三教302'
        }
      },
      {
        tool: 'weather_query',
        label: '天气查询',
        status: 'success',
        input: {
          date: '明天'
        },
        output: {
          weather: '小雨',
          temperature: '23-28℃',
          wind: '东北风 2 级'
        }
      },
      {
        tool: 'campus_route',
        label: '地点距离',
        status: 'success',
        input: {
          from: '宿舍1号楼',
          to: '三教'
        },
        output: {
          walking_minutes: 12,
          biking_minutes: 5,
          distance: '800米'
        }
      }
    ],
    artifacts: [
      {
        type: 'table',
        title: '出行判断',
        columns: ['项目', '结果'],
        rows: [
          ['课程', '高等数学 08:00-09:40'],
          ['地点', '三教302'],
          ['天气', '小雨，23-28℃'],
          ['建议', '不建议骑车，建议步行'],
          ['出门时间', '07:40']
        ]
      }
    ]
  }
}

function studyPlanResponse(sessionId) {
  return {
    session_id: sessionId,
    status: 'success',
    answer:
      '我根据课表、考试时间和资料重点生成了一个三天复习安排。今天建议先完成数据库第一轮复习，再处理高数作业。',
    steps: [
      '识别任务：学习规划',
      '查询近期课程和空闲时间',
      '查询考试与作业截止时间',
      '检索数据库复习资料',
      '计算任务优先级并生成计划'
    ],
    tool_calls: [
      {
        tool: 'schedule_query',
        label: '空闲时间查询',
        status: 'success',
        input: {
          range: '未来3天'
        },
        output: {
          free_slots: ['今天 19:00-21:00', '明天 15:00-17:00', '后天 20:00-21:30']
        }
      },
      {
        tool: 'deadline_query',
        label: '截止时间查询',
        status: 'success',
        input: {
          courses: ['数据库', '高等数学']
        },
        output: {
          database_exam: '下周三',
          math_homework: '本周五 23:59'
        }
      },
      {
        tool: 'file_search',
        label: '资料检索',
        status: 'success',
        input: {
          keyword: '数据库 重点'
        },
        output: {
          materials: ['事务与并发控制.md', 'SQL查询练习.md', '范式与ER图.md']
        }
      }
    ],
    artifacts: [
      {
        type: 'table',
        title: '三天复习计划',
        columns: ['时间', '任务', '原因'],
        rows: [
          ['今天 19:00-20:20', '数据库：事务与并发控制', '考试优先级最高'],
          ['今天 20:20-21:00', '高数作业', '截止时间较近'],
          ['明天 15:00-17:00', '数据库：SQL练习', '需要连续练习'],
          ['后天 20:00-21:30', '数据库：范式与ER图', '补齐薄弱章节']
        ]
      }
    ]
  }
}

function needsDate(text) {
  const asksSchedule = text.includes('有没有课') || text.includes('课表') || text.includes('课程')
  const hasDate =
    text.includes('今天') ||
    text.includes('明天') ||
    text.includes('后天') ||
    /\d{4}[-/年]\d{1,2}[-/月]\d{1,2}/.test(text)
  return asksSchedule && !hasDate
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
