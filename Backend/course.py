from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import sqlite3
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

app = FastAPI()

router = APIRouter(prefix="/api")

DATABASE = os.getenv("DATABASE_URL", "course.db")
TEACHER_DB = os.getenv("TEACHER_DB_PATH", "teacher.db")
STUDENTS_DB = os.getenv("STUDENTS_DB_PATH", "students.db")
CLASS_STU_DB = os.getenv("CLASS_STU_DB_PATH", "class_stu.db")

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS course(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id TEXT NOT NULL UNIQUE,
            day INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            course_name TEXT NOT NULL,
            teacher_num TEXT NOT NULL,
            room_id TEXT,
            week_start INTEGER NOT NULL,
            week_end INTEGER NOT NULL,
            semester TEXT NOT NULL,
            credit REAL NOT NULL DEFAULT 0
        )
    """)
    try:
        conn.execute("ALTER TABLE course ADD COLUMN credit REAL NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

class Corse(BaseModel):
    course_id: str
    day: int
    start_time: str
    end_time: str
    course_name: str
    teacher_num: str
    room_id: str
    week_start: int
    week_end: int
    semester: str
    credit: float

# 管理员添加课程接口, 添加新课程，自动校验教室是否存在、教师工号是否有效
# 仅admin可调用，前端应仅在admin面板开放此入口
@router.post("/course/add")
def addcourse(course_data: Corse):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    room = conn.execute("SELECT * FROM course WHERE course_id = ?", (course_data.course_id,)).fetchone()
    if room:
        conn.close()
        raise HTTPException(status_code=400, detail="Course has existed, conflict touched")

    parts = course_data.room_id.split("-")
    if len(parts) != 3:
        conn.close()
        raise HTTPException(status_code=400, detail="room_id 格式应为 area-building-room_id，如 3-3-201")

    room_conn = sqlite3.connect("room.db")
    exists = room_conn.execute(
        "SELECT 1 FROM room WHERE area=? AND building=? AND room_id=?", (parts[0], parts[1], parts[2])
    ).fetchone()
    room_conn.close()
    if not exists:
        conn.close()
        raise HTTPException(status_code=400, detail=f"房间 {course_data.room_id} 不存在")

    tea_conn = sqlite3.connect("teacher.db")
    tea_conn.row_factory = sqlite3.Row
    teach = tea_conn.execute(
        "SELECT * FROM teacher WHERE Number = ?", (course_data.teacher_num,)
    ).fetchone()
    tea_conn.close()
    if not teach:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Teacher {course_data.teacher_num} Not Found")

    conn.execute(
        "INSERT INTO course (course_id, day, start_time, end_time, course_name, teacher_num, room_id, week_start, week_end, semester, credit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (course_data.course_id, course_data.day, course_data.start_time, course_data.end_time, course_data.course_name, course_data.teacher_num, course_data.room_id, course_data.week_start, course_data.week_end, course_data.semester, course_data.credit)
    )

    conn.commit()
    conn.close()

    return {"message": f"Course {course_data.course_id} added successfully"}

# 教师查询自己所授全部课程接口, 根据教师工号返回该教师的所有课程信息（含学分）
# teacher和admin可调用，teacher_num由前端自动传入当前登录账号
@router.get("/course/teacher")
def teacher_course(teacher_num: str):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cont = sqlite3.connect("teacher.db")
    cont.row_factory = sqlite3.Row
    tea = cont.execute(
        "SELECT * FROM teacher WHERE Number = ?", (teacher_num,)
    ).fetchone()
    cont.close()
    if not tea:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Teacher {teacher_num} Not Found")

    rows = conn.execute(
        "SELECT * FROM course WHERE teacher_num = ?", (teacher_num,)
    ).fetchall()
    conn.close()
    return {"teacher_num ": teacher_num, "Course": [dict(row) for row in rows], "count": len(rows)}

# 修改课程信息接口, 需要校验教室和教师是否存在
# admin可修改所有课程，teacher仅可修改自己的课程（由前端控制）
# ============================================================
@router.patch("/course/{course_id}/info")
def change_info(course_id: str, newinfo: Corse):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    course = conn.execute("SELECT * FROM course WHERE course_id = ?", (course_id,)).fetchone()
    if not course:
        conn.close()
        raise HTTPException(status_code=400, detail="Course Not Found 404")
    
    tea_conn = sqlite3.connect("teacher.db")
    tea_conn.row_factory = sqlite3.Row
    teach = tea_conn.execute(
        "SELECT * FROM teacher WHERE Number = ?", (newinfo.teacher_num,)
    ).fetchone()
    tea_conn.close()
    if not teach:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Teacher {newinfo.teacher_num} Not Found")

    parts = newinfo.room_id.split("-")
    if len(parts) != 3:
        conn.close()
        raise HTTPException(status_code=400, detail="room_id 格式应为 area-building-room_id，如 3-3-201")

    room_conn = sqlite3.connect("room.db")
    exists = room_conn.execute(
        "SELECT 1 FROM room WHERE area=? AND building=? AND room_id=?", (parts[0], parts[1], parts[2])
    ).fetchone()
    room_conn.close()
    if not exists:
        conn.close()
        raise HTTPException(status_code=400, detail=f"房间 {newinfo.room_id} 不存在")
    
    conn.execute(
    """UPDATE course 
       SET day = ?,
           start_time = ?,
           end_time = ?,
           course_name = ?,
          teacher_num = ?,
           room_id = ?,
          week_start = ?,
           week_end = ?,
           semester = ?,
           credit = ?
       WHERE course_id = ?""",
    (
        newinfo.day,
        newinfo.start_time,
        newinfo.end_time,
        newinfo.course_name,
        newinfo.teacher_num,
        newinfo.room_id,
        newinfo.week_start,
        newinfo.week_end,
        newinfo.semester,
        newinfo.credit,
        course_id
    )
    )
    conn.commit()
    conn.close()

    return {"message": f"Course {course_id} info had been changed successfully"}

# 删除课程接口, 仅admin可调用
@router.delete("/course/delete")
def delete_course(course_id: str):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT * FROM course WHERE course_id = ?", (course_id,)
    ).fetchone()

    if not rows:
        conn.close()
        raise HTTPException(status_code=404, detail="Course Not Found 404")

    conn.execute(
        "DELETE FROM course WHERE course_id = ?", (course_id,)
    )

    conn.commit()
    conn.close()

    return {"message": "Course deleted successfully"}

# 查看全部课程列表接口, 所有用户均可调用
@router.get("/course")
def list_all():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM course ORDER BY course_id",
    ).fetchall()
    conn.close()
    return {"Courses": [dict(row) for row in rows], "count": len(rows)}

# 多条件筛选查询课程接口, 按任意组合条件筛选课程，支持模糊搜索
# 所有用户均可调用
@router.get("/course/display")
def display_courses(course_id=None, day=None, start_time=None, end_time=None, course_name=None, teacher_num=None, room_id=None, week_start=None, week_end=None, semester=None, credit=None):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM course WHERE 1=1"
    params = []
    if course_id is not None:
        query += " AND course_id = ?"
        params.append(course_id)
    if day is not None:
        query += " AND day = ?"
        params.append(day)
    if start_time is not None:
        query += " AND start_time = ?"
        params.append(start_time)
    if end_time is not None:
        query += " AND end_time = ?"
        params.append(end_time)
    if course_name is not None:
        query += " AND course_name LIKE ?"
        params.append(f"%{course_name}%")
    if teacher_num is not None:
        query += " AND teacher_num LIKE ?"
        params.append(f"%{teacher_num}%")
    if room_id is not None:
        query += " AND room_id = ?"
        params.append(room_id)
    if week_start is not None:
        query += " AND week_start = ?"
        params.append(week_start)
    if week_end is not None:
        query += " AND week_end = ?"
        params.append(week_end)
    if semester is not None:
        query += " AND semester = ?"
        params.append(semester)
    if credit is not None:
        query += " AND credit = ?"
        params.append(credit)
    query += " ORDER BY course_id"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return {"courses": [dict(r) for r in rows], "count": len(rows)}

# 返回指定教师所授全部课程的course_id列表
# teacher和admin可调用
@router.get("/course/teacher/course_id")
def get_teacher_course(teacher_num: str):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    tea_conn = sqlite3.connect(TEACHER_DB)
    tea_conn.row_factory = sqlite3.Row
    teacher = tea_conn.execute(
        "SELECT * FROM teacher WHERE Number = ?", (teacher_num,)
    ).fetchone()
    if not teacher:
        conn.close()
        tea_conn.close()
        raise HTTPException(status_code=404, detail=f"Teacher {teacher_num} Not Found!")
    tea_conn.close()

    rows = conn.execute(
        "SELECT * FROM course WHERE teacher_num = ?", (teacher_num,)
    ).fetchall()

    conn.close()
    return {"message": [row["course_id"] for row in rows], "count": len(rows)}

# 返回教师所有课程的学生名单（含学生姓名、班级）
# teacher可查自己，admin可查任意教师
@router.get("/course/teacher/{teacher_num}/students")
def get_teacher_students(teacher_num: str):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    cont = sqlite3.connect(TEACHER_DB)
    cont.row_factory = sqlite3.Row
    teacher = cont.execute(
        "SELECT * FROM teacher WHERE Number = ?", (teacher_num,)
    ).fetchone()
    if not teacher:
        conn.close()
        cont.close()
        raise HTTPException(status_code=404, detail=f"Teacher {teacher_num} Not Found!")
    teacher_name = teacher["Name"]

    courses = conn.execute(
        "SELECT * FROM course WHERE teacher_num = ?", (teacher_num,)).fetchall()
    conn.close()

    if not courses:
        return {"teacher_num": teacher_num, "courses": [], "count": 0}

    conn2 = sqlite3.connect(CLASS_STU_DB)
    conn2.row_factory = sqlite3.Row
    course_ids = [c["course_id"] for c in courses]
    placeholders = ",".join("?" * len(course_ids))
    enrollments = conn2.execute(
        f"SELECT * FROM class_stu WHERE course_id IN ({placeholders})", course_ids).fetchall()
    conn2.close()
    enroll_map = {}
    for e in enrollments:
        cid = str(e["course_id"])
        if cid not in enroll_map:
            enroll_map[cid] = []
        enroll_map[cid].append(e["stu_num"])

    conn3 = sqlite3.connect(STUDENTS_DB)
    conn3.row_factory = sqlite3.Row
    all_stu = list(set(e["stu_num"] for e in enrollments))
    stu_map = {}
    if all_stu:
        p2 = ",".join("?" * len(all_stu))
        student_rows = conn3.execute(
            f"SELECT StuNum, Name, Cls FROM students WHERE StuNum IN ({p2})", all_stu).fetchall()
        for s in student_rows:
            stu_map[s["StuNum"]] = {"name": s["Name"], "cls": s["Cls"]}
    conn3.close()

    result = []
    for course in courses:
        course_dict = dict(course)
        students = []
        for stu_num in enroll_map.get(str(course["course_id"]), []):
            info = stu_map.get(stu_num, {})
            students.append({"stu_num": stu_num, "name": info.get("name", ""), "cls": info.get("cls", "")})
        course_dict["students"] = students
        result.append(course_dict)

    return {"teacher_name": teacher_name, "teacher_num": teacher_num, "courses": result, "count": len(result)}

def time_to_minutes(time_str: str) -> int:
    hours, minutes = map(int, time_str.split(':'))
    return hours * 60 + minutes

# 检测指定时间段内某教室是否有课程冲突，无冲突则返回可用
# 所有用户均可调用，可以用于排课辅助，进一步在图书馆预约可以用同样思路
@router.get("/course/free-room")
def get_free_room(week: str, day: str, st_time: str, ed_time: str, area: str, building: str, roomid: str, semester: str):
    connr = sqlite3.connect("room.db")
    connr.row_factory = sqlite3.Row
    rm = connr.execute(
        "SELECT * FROM room WHERE area = ? AND building = ? AND room_id = ?", (area, building, roomid)
    ).fetchone()
    if not rm:
        connr.close()
        raise HTTPException(status_code=404, detail="Room Not Found")
    connr.close()
    room = area + '-' + building + '-' + roomid
    conn1 = sqlite3.connect(DATABASE)
    conn1.row_factory = sqlite3.Row
    rows = conn1.execute(
        "SELECT * FROM course WHERE room_id = ? AND day = ? AND semester = ?", (room, day, semester)
    ).fetchall()

    st_int = time_to_minutes(st_time)
    ed_int = time_to_minutes(ed_time)

    for r in rows:
        if r["week_start"] <= int(week) and r["week_end"] >= int(week):
            if (time_to_minutes(r["start_time"]) <= st_int and time_to_minutes(r["end_time"]) > st_int) or (time_to_minutes(r["start_time"]) < ed_int and time_to_minutes(r["end_time"]) >= ed_int) or (time_to_minutes(r["start_time"]) >= st_int and time_to_minutes(r["end_time"]) <= ed_int):
                conn1.close()
                raise HTTPException(status_code=400, detail=f"Conflict caused!  |  Selected time is not free")
            
    conn1.close()
    return {"message": f"Time permitted at {room}. Enjoy your time"}


# 按学期查询课程，所有用户均可调用
@router.get("/course/semester/{semester}")
def get_by_semester(semester: str):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM course WHERE semester = ? ORDER BY course_id", (semester,)
    ).fetchall()
    conn.close()
    return {"semester": semester, "courses": [dict(row) for row in rows], "count": len(rows)}


# 功能说明: 返回指定课程的完整信息，同时返回授课教师姓名，所有用户均可调用
@router.get("/course/{course_id}/detail")
def get_course_detail(course_id: str):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    course = conn.execute(
        "SELECT * FROM course WHERE course_id = ?", (course_id,)
    ).fetchone()
    if not course:
        conn.close()
        raise HTTPException(status_code=404, detail="Course Not Found")
    
    course_dict = dict(course)
    
    tea_conn = sqlite3.connect(TEACHER_DB)
    tea_conn.row_factory = sqlite3.Row
    teacher = tea_conn.execute(
        "SELECT Name FROM teacher WHERE Number = ?", (course["teacher_num"],)
    ).fetchone()
    tea_conn.close()
    course_dict["teacher_name"] = teacher["Name"] if teacher else ""
    
    conn.close()
    return {"course": course_dict}


# 统计课程总数、总学分、各学期学分分布
# 所有用户均可调用
@router.get("/course/credit/stats")
def get_credit_stats(semester: Optional[str] = None):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    if semester:
        rows = conn.execute(
            "SELECT course_id, course_name, credit FROM course WHERE semester = ? ORDER BY course_id",
            (semester,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT course_id, course_name, credit, semester FROM course ORDER BY semester, course_id"
        ).fetchall()
    
    semester_stats = {}
    total_credits = 0
    for row in rows:
        sem = row["semester"]
        if sem not in semester_stats:
            semester_stats[sem] = {"count": 0, "total_credit": 0.0, "courses": []}
        semester_stats[sem]["count"] += 1
        semester_stats[sem]["total_credit"] += row["credit"]
        total_credits += row["credit"]
        semester_stats[sem]["courses"].append({
            "course_id": row["course_id"],
            "course_name": row["course_name"],
            "credit": row["credit"]
        })
    
    conn.close()
    
    result = {
        "total_courses": len(rows),
        "total_credits": total_credits,
        "by_semester": semester_stats
    }
    if semester:
        result["semester"] = semester
    
    return result

app.include_router(router)