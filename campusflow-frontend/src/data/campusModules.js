export const initialTodos = [
  {
    id: 'todo-001',
    title: '复习数据库原理第三章',
    dueDate: '今天 22:00',
    status: 'pending',
    category: '学习',
    source: '课程提醒',
    priority: 'high',
    note: '整理 SQL 连接查询和事务隔离级别。'
  },
  {
    id: 'todo-002',
    title: '确认明天下午图书馆座位',
    dueDate: '明天 13:00',
    status: 'pending',
    category: '图书馆',
    source: '预约',
    priority: 'medium',
    note: '优先选择信息学部馆二楼靠窗座位。'
  },
  {
    id: 'todo-003',
    title: '查看软件工程导论课程资料',
    dueDate: '周五 12:00',
    status: 'done',
    category: '课程',
    source: '手动创建',
    priority: 'low',
    note: '课前浏览项目案例。'
  }
]

export const initialGrades = [
  { id: 'grade-001', semester: '2025-2026-1', courseName: '高等数学', credit: 4, usual: 88, final: 84, score: 86, gpa: 3.6, rank: '前 35%' },
  { id: 'grade-002', semester: '2025-2026-1', courseName: '数据库原理', credit: 3, usual: 92, final: 90, score: 91, gpa: 4.0, rank: '前 15%' },
  { id: 'grade-003', semester: '2025-2026-1', courseName: '软件工程导论', credit: 2, usual: 85, final: 88, score: 87, gpa: 3.7, rank: '前 30%' },
  { id: 'grade-004', semester: '2025-2026-2', courseName: 'Python程序设计', credit: 3, usual: 90, final: 86, score: 88, gpa: 3.8, rank: '前 25%' }
]

export const initialLibrarySeats = [
  { id: 'seat-201', library: '信息学部图书馆', floor: '二楼', area: 'A区', seatNo: 'A-201', status: 'available', time: '14:00-17:00' },
  { id: 'seat-215', library: '信息学部图书馆', floor: '二楼', area: 'A区', seatNo: 'A-215', status: 'reserved', time: '14:00-17:00' },
  { id: 'seat-306', library: '总馆', floor: '三楼', area: '研讨区', seatNo: 'G-306', status: 'available', time: '18:00-21:00' },
  { id: 'seat-412', library: '工学部图书馆', floor: '四楼', area: '静音区', seatNo: 'D-412', status: 'available', time: '09:00-12:00' }
]

export const initialReservations = [
  { id: 'res-001', type: '座位', target: '信息学部图书馆 A-201', time: '明天 14:00-17:00', status: 'active' }
]

export const initialForumPosts = [
  {
    id: 'post-001',
    channel: '学习交流',
    title: '数据库原理复习资料整理',
    author: '赵同学',
    role: 'student',
    replies: 12,
    likes: 28,
    status: 'published',
    summary: '整理了事务、索引和范式相关知识点。'
  },
  {
    id: 'post-002',
    channel: '校园生活',
    title: '本周五社团开放日集合信息',
    author: '周同学',
    role: 'student',
    replies: 8,
    likes: 16,
    status: 'published',
    summary: '社团开放日流程、地点和报名方式。'
  },
  {
    id: 'post-003',
    channel: '失物招领',
    title: '三教拾到校园卡一张',
    author: '陈同学',
    role: 'student',
    replies: 3,
    likes: 5,
    status: 'review',
    summary: '等待管理员审核后展示联系方式。'
  }
]

export const initialNotifications = [
  { id: 'notice-001', type: '课程通知', title: '数据库原理本周实验安排已更新', time: '今天 09:20', status: 'unread', link: 'schedule', audienceRoles: ['student', 'teacher'], classId: 'class-se-1' },
  { id: 'notice-002', type: '成绩通知', title: '2025-2026-1 学期成绩已发布', time: '昨天 18:00', status: 'unread', link: 'grades', audienceRoles: ['student'], classId: 'class-se-1' },
  { id: 'notice-003', type: '图书馆通知', title: '明天下午座位预约即将开始', time: '昨天 12:30', status: 'read', link: 'library', audienceRoles: ['student'] },
  { id: 'notice-004', type: '论坛互动', title: '你的帖子收到 2 条新回复', time: '周一 20:10', status: 'read', link: 'forum', audienceRoles: ['student'] },
  { id: 'notice-005', type: '系统通知', title: '本周需完成新生账号导入核验', time: '今天 08:45', status: 'unread', link: 'classes', audienceRoles: ['admin'] }
]

export const initialFiles = [
  { id: 'file-001', name: '数据库复习计划.md', type: 'Markdown', source: '助手生成', size_formatted: '4.8 KB', createdAt: '今天 10:30', url: '', audienceRoles: ['student'], classId: 'class-se-1' },
  { id: 'file-002', name: '软件工程导论课程资料.pdf', type: 'PDF', source: '课程资料', size_formatted: '1.2 MB', createdAt: '昨天 16:20', url: '', audienceRoles: ['student', 'teacher'], classId: 'class-se-1' },
  { id: 'file-003', name: '学生账号导入模板.xlsx', type: 'Excel', source: '管理资料', size_formatted: '18 KB', createdAt: '今天 09:00', url: '', audienceRoles: ['admin'] }
]

export const initialSystemLogs = [
  { id: 'log-001', actor: '管理员', action: '发布系统公告', time: '今天 08:30' },
  { id: 'log-002', actor: '林老师', action: '更新软件工程1班课表', time: '昨天 19:10' },
  { id: 'log-003', actor: '管理员', action: '审核论坛帖子', time: '昨天 17:45' }
]
