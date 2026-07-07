# SchAgent Backend — 数据库管理 & 方法调用全息文档

## 目录总览

| 模块文件 | 数据库文件 | 用途 | 启动方式 |
|----------|-----------|------|---------|
| main.py | — | 核心代理层，编排 LangChain Agent 对话 | `uvicorn main:app --port 8080` |
| admin.py | admin.db | 管理员注册、列表、改密码 | 内嵌于模块 |
| student.py | students.db | 学生注册、列表、改班级、改密码 | 内嵌于模块 |
| teacher.py | teacher.db | 教师注册、列表、改密码 | 内嵌于模块 |
| course.py | course.db | 课程 CRUD、筛选、查空教室、查老师学生 | 内嵌于模块 |
| class_stu.py | class_stu.db | 选课/退课、按学生/课程查询、跨库 JOIN | 内嵌于模块 |
| room.py | room.db | 教室增删、列表 | 内嵌于模块 |

---

# 一、数据库管理

每个模块独立管理自己的 SQLite 数据库文件，通过环境变量指定路径。
数据文件 `.db` 创建于 `C:\Users\92151\Desktop\workspace\SchAgent\Backend\`。

## 1. admin.db — 管理员表

```sql
CREATE TABLE IF NOT EXISTS admin (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    Name          TEXT NOT NULL,
    Number        TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);
```

**字段说明**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 自增主键 |
| Name | TEXT | NOT NULL | 管理员姓名 |
| Number | TEXT | UNIQUE, NOT NULL | 工号（唯一标识） |
| password_hash | TEXT | NOT NULL | pbkdf2_sha256 哈希密码 |

- **环境变量**: `DATABASE_URL`，默认 `admin.db`
- **密码算法**: pbkdf2_sha256

---

## 2. students.db — 学生表

```sql
CREATE TABLE IF NOT EXISTS students (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    Name          TEXT NOT NULL,
    StuNum        TEXT UNIQUE NOT NULL,
    Cls           TEXT,
    password_hash TEXT NOT NULL
);
```

**字段说明**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 自增主键 |
| Name | TEXT | NOT NULL | 学生姓名 |
| StuNum | TEXT | UNIQUE, NOT NULL | 学号（唯一标识） |
| Cls | TEXT | — | 班级号 |
| password_hash | TEXT | NOT NULL | pbkdf2_sha256 哈希密码 |

- **环境变量**: `DATABASE_URL`，默认 `students.db`

---

## 3. teacher.db — 教师表

```sql
CREATE TABLE IF NOT EXISTS teacher (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    Name          TEXT NOT NULL,
    Number        TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);
```

**字段说明**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 自增主键 |
| Name | TEXT | NOT NULL | 教师姓名 |
| Number | TEXT | UNIQUE, NOT NULL | 教师编号（唯一标识） |
| password_hash | TEXT | NOT NULL | pbkdf2_sha256 哈希密码 |

- **环境变量**: `DATABASE_URL`，默认 `teacher.db`

---

## 4. course.db — 课程表

```sql
CREATE TABLE IF NOT EXISTS course (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id    TEXT NOT NULL UNIQUE,
    day          INTEGER NOT NULL,
    start_time   TEXT NOT NULL,
    end_time     TEXT NOT NULL,
    course_name  TEXT NOT NULL,
    teacher_name TEXT NOT NULL,
    room_id      TEXT,
    week_start   INTEGER NOT NULL,
    week_end     INTEGER NOT NULL,
    semester     TEXT NOT NULL
);
```

**字段说明**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 自增主键 |
| course_id | TEXT | UNIQUE, NOT NULL | 课程编号 |
| day | INTEGER | NOT NULL | 星期几（1-7） |
| start_time | TEXT | NOT NULL | 上课时间，如 "08:00" |
| end_time | TEXT | NOT NULL | 下课时间，如 "09:35" |
| course_name | TEXT | NOT NULL | 课程名称 |
| teacher_name | TEXT | NOT NULL | 授课教师 |
| room_id | TEXT | — | 教室 ID，格式 "area-building-room_id" |
| week_start | INTEGER | NOT NULL | 起始周 |
| week_end | INTEGER | NOT NULL | 结束周 |
| semester | TEXT | NOT NULL | 学期标识 |

- **环境变量**: `DATABASE_URL`，默认 `course.db`
- **额外**: `CLASS_STU_DB_PATH`→`class_stu.db`，`STUDENTS_DB_PATH`→`students.db`（跨库 JOIN）

---

## 5. class_stu.db — 选课关系表

```sql
CREATE TABLE IF NOT EXISTS class_stu (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    stu_num   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cs_course ON class_stu(course_id);
CREATE INDEX IF NOT EXISTS idx_cs_student ON class_stu(stu_num);
```

**字段说明**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 自增主键 |
| course_id | INTEGER | NOT NULL | 关联 course.course_id |
| stu_num | TEXT | NOT NULL | 学号 |

- **环境变量**: `CLASS_STU_DB`，默认 `class_stu.db`
- **索引**: `idx_cs_course`(按课程查), `idx_cs_student`(按学生查)
- **额外**: `COURSE_DB_PATH`→`course.db`（跨库 JOIN）

---

## 6. room.db — 教室表

```sql
CREATE TABLE IF NOT EXISTS room (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    area     TEXT NOT NULL,
    building TEXT NOT NULL,
    room_id  TEXT NOT NULL,
    capacity TEXT NOT NULL,
    UNIQUE(area, building, room_id)
);
```

**字段说明**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 自增主键 |
| area | TEXT | NOT NULL | 校区/区域编号 |
| building | TEXT | NOT NULL | 楼栋编号 |
| room_id | TEXT | NOT NULL | 房间号 |
| capacity | TEXT | NOT NULL | 容量 |

- **环境变量**: `DATABASE_URL`，默认 `room.db`
- **联合唯一约束**: `(area, building, room_id)`

---

# 二、方法调用全逻辑

## 1. main.py — 核心编排层

**职责**: FastAPI 应用，接收前端请求，代理调用 LangChain Agent API。

**启动**:
```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### 对外接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 + 探测下游 Agent 状态 |
| POST | `/api/chat` | 非流式对话，收集 SSE 事件后返回结构化 JSON |
| POST | `/api/chat/stream` | SSE 流式对话，直接透传下游事件 |
| GET | `/api/history/{session_id}` | 获取对话历史 |
| DELETE | `/api/history/{session_id}` | 清除对话历史 |
| GET | `/api/memory/{username}` | 读取长期记忆 |
| PUT | `/api/memory/{username}` | 写入长期记忆 |
| GET | `/api/files` | 获取工作区文件列表 |

### 核心函数: `call_agent_stream_collect`

```
入参: session_id, message, username?

流程:
  1. POST 请求下游 {AGENT_API_BASE}/chat/stream (SSE)
  2. 逐行解析 SSE，按事件类型分流收集:
     - event: status     → 收集到 collected_steps[]
     - event: token      → 追加到 collected_tokens[]
     - event: tool_call  → 记录工具名 + 参数到 collected_tool_calls[]
     - event: tool_result→ 匹配最近同名工具，填回 output + status
     - event: error      → 记录错误信息
     - event: done       → 拿到 final_session_id
  3. 拼接完整回答，判定状态:
     - 空回答 + 有错误 → status = "failed"
     - 回答含疑问词头 → status = "need_clarification"
     - 正常 → status = "success"
  4. 返回 ChatResponse(session_id, status, answer, steps, tool_calls, artifacts)
```

**工具标签映射 (TOOL_LABELS)**

| 工具名 | 中文标签 |
|--------|---------|
| `get_weather` | 天气查询 |
| `calculator` | 数学计算 |
| `get_current_time` | 时间查询 |
| `list_files` | 文件列表 |
| `read_file` | 读取文件 |
| `write_file` | 写入文件 |
| `save_memory` | 保存记忆 |
| `recall_memory` | 读取记忆 |
| `markdown_to_html` | Markdown 转 HTML |
| `markdown_to_pdf` | Markdown 转 PDF |

---

## 2. admin.py — 管理员管理

**初始化**: `init_db()` 自动建表 `admin`。
**密码工具**: `hash_password(pw)` → pbkdf2_sha256；`verify_password(pw, hash)` → bool

| 方法 | 路径 | 参数 | 逻辑简述 |
|------|------|------|---------|
| POST | `/api/register` | `AdminRegister{Name, Number, password}` | 检查 Number 唯一 → 存在则 409 → 哈希密码 → INSERT |
| GET | `/api/admin` | — | SELECT 全部管理员（不含密码） |
| PUT | `/api/admin/{admin_id}/password` | `PasswordChange{old_password, new_password}` | 查存在 → 校验旧密码 → 新旧不同 → 哈希 NEW → UPDATE |

---

## 3. student.py — 学生管理

**初始化**: `init_db()` 自动建表 `students`。

| 方法 | 路径 | 参数 | 逻辑简述 |
|------|------|------|---------|
| POST | `/api/register` | `StudentRegister{Name, StuNum, Cls, password}` | 检查 StuNum 唯一 → 哈希 → INSERT |
| GET | `/api/students` | — | SELECT 全部学生 |
| PATCH | `/api/students/{student_id}/Cls` | `newcls`(query) | 查存在 → 检查未相同 → UPDATE Cls |
| PUT | `/api/students/{student_id}/password` | `PasswordChange` | 查存在 → 校验旧密码 → 新旧不同 → 哈希 → UPDATE |

---

## 4. teacher.py — 教师管理

**初始化**: `init_db()` 自动建表 `teacher`。

| 方法 | 路径 | 参数 | 逻辑简述 |
|------|------|------|---------|
| POST | `/api/register` | `TeacherRegister{Name, Number, password}` | 检查 Number 唯一 → 哈希 → INSERT |
| GET | `/api/teacher` | — | SELECT 全部教师 |
| PUT | `/api/teacher/{teacher_id}/password` | `PasswordChange` | 查存在 → 校验旧密码 → 新旧不同 → 哈希 → UPDATE |

---

## 5. course.py — 课程管理

**初始化**: `init_db()` 自动建表 `course`。

| 方法 | 路径 | 参数/请求体 | 逻辑简述 |
|------|------|------------|---------|
| POST | `/api/course/add` | `Corse` 完整对象 | 查 course_id 唯一 → 校验 room_id 三段格式 → 跨库查 room.db → INSERT |
| PATCH | `/api/course/{course_id}/info` | `Corse` 完整对象 | 查存在 → 校验 room_id → 验证 room.db → UPDATE 全部字段 |
| DELETE | `/api/course/delete` | `course_id`(query) | 查存在 → DELETE |
| GET | `/api/course` | — | SELECT * ORDER BY course_id |
| GET | `/api/course/display` | 所有字段可选(query) | 动态 WHERE 拼接，course_name/teacher_name 支持 LIKE 模糊搜索 |
| GET | `/api/course/teacher/{teacher_name}/students` | — | **跨三库 JOIN**: course.db → class_stu.db → students.db，拼装每课程下的学生列表 |
| GET | `/api/course/free-room` | `week,day,st_time,ed_time,area,building,roomid` | 拼接 room_id → 查课程时段 → 检查时间冲突 |

**跨三库 JOIN 流程 (`/api/course/teacher/{teacher}/students`)**:

```
1. course.db:   SELECT * FROM course WHERE teacher_name = ?
   → 拿到该老师所有课程的 course_id 列表

2. class_stu.db: SELECT * FROM class_stu WHERE course_id IN (?,?,...)
   → 拿到所有选课记录，按 course_id 分组

3. students.db:  SELECT StuNum, Name, Cls FROM students WHERE StuNum IN (?,?,...)
   → 拿到所有学生姓名 + 班级

4. 组装: 每门课程下挂 students[{stu_num, name, cls}]
```

---

## 6. class_stu.py — 选课关系管理

**初始化**: `init_db()` 自动建表 `class_stu` + 索引。

| 方法 | 路径 | 参数 | 逻辑简述 |
|------|------|------|---------|
| POST | `/api/class-stu/enroll` | `EnrollRequest{course_id, stu_num}` | 查是否已选 → 已有则 return id → 否则 INSERT |
| DELETE | `/api/class-stu/enroll` | `DeleteEnrollRequest{course_id, stu_num}` | DELETE 匹配行 → rowcount=0 则 404 |
| GET | `/api/class-stu/student/{stu_num}` | — | 查学生所有选课 |
| GET | `/api/class-stu/course/{course_id}` | — | 查课程所有学生 |
| GET | `/api/class-stu` | — | 全量列表，按 stu_num,course_id 排序 |
| GET | `/api/class-stu/student/{stu_num}/details` | — | **跨库 JOIN**: class_stu.db → course.db，返回完整课程信息 |

**跨库 JOIN 流程 (`/api/class-stu/student/{stu_num}/details`)**:

```
1. class_stu.db: SELECT course_id FROM class_stu WHERE stu_num = ?
   → 该学生的所有 course_id

2. course.db:    SELECT * FROM course WHERE course_id IN (?,?,...)
   → 完整课程详情
```

---

## 7. room.py — 教室管理

**初始化**: `init_db()` 自动建表 `room`（含联合唯一约束）。

| 方法 | 路径 | 参数 | 逻辑简述 |
|------|------|------|---------|
| POST | `/api/room/add` | `roomReg{area, building, room_id, capacity}` | 检查 room_id 重复（⚠️ 仅查单字段）→ INSERT |
| GET | `/api/room` | — | SELECT + 拼装 room_full |

**种子数据** (`room.py` 中 `seed_trial()` 函数):

| 区域 | 楼栋 | 房间 | 容量 |
|------|------|------|------|
| 3 | 1 | 209 | 60 |
| 3 | 1 | 415 | 90 |
| 3 | 1 | 512 | 40 |
| 3 | 1 | 709 | 100 |
| 3 | 2 | 402 | 60 |
| 3 | 2 | 108 | 40 |
| 3 | 3 | 301 | 90 |
| 3 | 3 | 201 | 80 |
| 1 | 5 | 107 | 40 |
| 1 | 6 | 103 | 45 |

---

# 三、架构总览

```
Vue 前端 (A)
  │
  │ POST /api/chat  / POST /api/chat/stream
  ▼
main.py (B)  ←── 核心编排层
  │
  │ HTTP → {AGENT_API_BASE}/chat/stream
  ▼
LangChain API (C) — api.py
  │
  ▼
Agent (D) → DeepSeek

数据库模块（admin/student/teacher/room/course/class_stu）
各自可独立启动或作为模块被引用。
```

---

# 四、已知问题

| 位置 | 问题 | 影响 | 建议修复 |
|------|------|------|---------|
| `course.py:66` addcourse | `return {"message", ...}` — 花括号内用逗号，实际返回 set | JSON 序列化异常 | 改逗号为冒号 `:` |
| `room.py:52` addroom | 字符串拼接缺少 f-string 前缀 | Python 语法错误，此路由不可用 | 加 `f` 前缀 |
| `room.py:41-51` addroom | 查重只查 `room_id` 字段，应联合查 `(area,building,room_id)` | 误报/漏报 | 加联合查重条件 |
| `course.py:160-170` free-room | 调用了 `display_courses()` 传参方式有误 | 传参不匹配 | 改为手动拼接提示信息 |
| 所有用户模块 | 注册后无登录/JWT 验证接口 | 密码哈希仅存储，无法校验身份 | 加 `/api/login` 端点 |

# 五、todo list
## 登录接口
## 选课信息冲突调整
## 批量导入（链接csv） -- 可选
## 配合处理下载文档的功能