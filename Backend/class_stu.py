from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import sqlite3
import os
from course import time_to_minutes, display_courses

app = FastAPI()

router = APIRouter(prefix="/api")

DATABASE = os.getenv("CLASS_STU_DB", "class_stu.db")


def get_conn():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS class_stu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id TEXT NOT NULL,
            stu_num TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cs_course ON class_stu(course_id);
        CREATE INDEX IF NOT EXISTS idx_cs_student ON class_stu(stu_num);
    """)
    conn.commit()
    conn.close()

init_db()


class EnrollRequest(BaseModel):
    course_id: str
    stu_num: str


class DeleteEnrollRequest(BaseModel):
    course_id: str
    stu_num: str

COURSE_DB = os.getenv("COURSE_DB_PATH", "course.db")
STUDENTS_DB = os.getenv("STUDENTS_DB_PATH", "students.db")

# 选课信息，面向学生student开放端口
# 传入信息中stu_num默认导入，仅需要填充course_id课头号即可
@router.post("/class-stu/enroll")
def enroll(req: EnrollRequest):
    conn = get_conn()
    conn1 = sqlite3.connect(STUDENTS_DB)
    conn1.row_factory = sqlite3.Row
    stu = conn1.execute(
        "SELECT * FROM students WHERE StuNum = ?", (req.stu_num,)
    ).fetchone()
    if not stu:
        conn.close()
        conn1.close()
        raise HTTPException(status_code=404, detail="Student Not Found")
    conn1.close()

    conn2 = sqlite3.connect(COURSE_DB)
    conn2.row_factory = sqlite3.Row
    cor = conn2.execute(
        "SELECT * FROM course WHERE course_id = ?", (req.course_id,)
    ).fetchone()
    if not cor:
        conn.close()
        conn2.close()
        raise HTTPException(status_code=404, detail="Course Not Found")
    day = cor["day"]
    st_int = time_to_minutes(cor["start_time"])
    ed_int = time_to_minutes(cor["end_time"])
    semester = cor["semester"]
    try:
        existing = conn.execute(
            "SELECT id FROM class_stu WHERE course_id = ? AND stu_num = ?",
            (req.course_id, req.stu_num)).fetchone()
        if existing:
            conn.close()
            return {"message": "Already enrolled", "id": existing["id"]}
        rows = conn.execute(
            "SELECT * FROM class_stu WHERE stu_num = ?", (req.stu_num,)
        ).fetchall()
        for row in rows:
            cid = row["course_id"]
            cor = conn2.execute(
                "SELECT * FROM course WHERE course_id = ? AND day = ? AND semester = ?", (cid, day, semester)
            ).fetchone()
            if not cor:
                continue
            if (time_to_minutes(cor["start_time"]) <= st_int and time_to_minutes(cor["end_time"]) > st_int) or (time_to_minutes(cor["start_time"]) < ed_int and time_to_minutes(cor["end_time"]) >= ed_int) or (time_to_minutes(cor["start_time"]) >= st_int and time_to_minutes(cor["end_time"]) <= ed_int):
                conn2.close()
                raise HTTPException(status_code=400, detail=f"Conflict caused! {display_courses(cor["course_id"], cor["day"], cor["start_time"], cor["end_time"])}  |  Selected time is not free")
        conn2.close()
        cur = conn.execute(
            "INSERT INTO class_stu (course_id, stu_num) VALUES (?, ?)",
            (req.course_id, req.stu_num))
        conn.commit()
        return {"message": "Enrolled successfully", "id": cur.lastrowid}
    finally:
        conn2.close()
        conn.close()

# 弃选，admin可以操作所有学生，端口开放stu_num
# student只能弃选自己的已有的课程
@router.delete("/class-stu/enroll")
def drop_course(req: DeleteEnrollRequest):
    conn = get_conn()
    conn_course = sqlite3.connect(COURSE_DB)
    conn_course.row_factory = sqlite3.Row
    corse = conn_course.execute(
        "SELECT * FROM course WHERE course_id = ?", (req.course_id,)
    ).fetchone()
    if not corse:
        conn.close()
        conn_course.close()
        raise HTTPException(status_code=404, detail=f"Course {req.course_id} Not Found!")
    
    try:
        cur = conn.execute(
            "DELETE FROM class_stu WHERE course_id = ? AND stu_num = ?",
            (req.course_id, req.stu_num))
        conn.commit()
        if cur.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Enrollment not found")
        return {"message": "Dropped successfully"}
    finally:
        conn.close()

# 对于一个学生，查看自己的全部课程，stu_num自动导入
# 端口开放给student，admin可以修改stu_num
@router.get("/class-stu/student/{stu_num}")
def get_student_courses(stu_num: str):
    conn = get_conn()
    conn_stu = sqlite3.connect(STUDENTS_DB)
    conn_stu.row_factory = sqlite3.Row
    corse = conn_stu.execute(
        "SELECT * FROM students WHERE StuNum = ?", (stu_num,)
    ).fetchone()
    if not corse:
        conn_stu.close()
        raise HTTPException(status_code=404, detail=f"Student {stu_num} Not Found!")
    rows = conn.execute(
        "SELECT * FROM class_stu WHERE stu_num = ?", (stu_num,)).fetchall()
    conn.close()
    conn_stu.close()
    return {"stu_num": stu_num, "courses": [dict(r) for r in rows], "count": len(rows)}

# 对于一个课程号，返回选择这个课程的所有学生
# 开放给老师，teacher只能查询自己所教课程的课程号的学生
# 通过course.py中get_teacher_course函数，得到所有课头号并展示出来，根据每个课头号都可以查看学生
# 开放给admin，所有课程号均可查看
# 建议调用，而不是用course中get_teacher_students函数，很乱
@router.get("/class-stu/course/{course_id}")
def get_course_students(course_id: str):
    conn = get_conn()
    conn_course = sqlite3.connect(COURSE_DB)
    conn_course.row_factory = sqlite3.Row
    corse = conn_course.execute(
        "SELECT * FROM course WHERE course_id = ?", (course_id,)
    ).fetchone()
    if not corse:
        conn.close()
        conn_course.close()
        raise HTTPException(status_code=404, detail=f"Course {course_id} Not Found!")
    rows = conn.execute(
        "SELECT * FROM class_stu WHERE course_id = ?", (course_id,)).fetchall()
    conn.close()
    conn_course.close()
    return {"course_id": course_id, "students": [dict(r) for r in rows], "count": len(rows)}

# 仅开放给admin
@router.get("/class-stu")
def list_all():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM class_stu ORDER BY stu_num, course_id").fetchall()
    conn.close()
    return {"enrollments": [dict(r) for r in rows], "count": len(rows)}

# 对于一个学生，查看自己的全部课程，stu_num自动导入，这里信息更加详细，包括老师和课程整个的所有信息
# 建议调用
# 端口开放给student，admin可以修改stu_num
@router.get("/class-stu/student/{stu_num}/details")
def get_student_course_details(stu_num: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT course_id FROM class_stu WHERE stu_num = ?", (stu_num,)).fetchall()
    conn.close()

    conn_stu = sqlite3.connect(STUDENTS_DB)
    conn_stu.row_factory = sqlite3.Row
    corse = conn_stu.execute(
        "SELECT * FROM students WHERE StuNum = ?", (stu_num,)
    ).fetchone()
    if not corse:
        conn_stu.close()
        raise HTTPException(status_code=404, detail=f"Student {stu_num} Not Found!")

    course_ids = [r["course_id"] for r in rows]
    if not course_ids:
        return {"stu_num": stu_num, "courses": [], "count": 0}

    conn2 = sqlite3.connect(COURSE_DB)
    conn2.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(course_ids))
    courses = conn2.execute(
        f"SELECT * FROM course WHERE course_id IN ({placeholders})", course_ids).fetchall()
    conn2.close()

    return {"stu_num": stu_num, "courses": [dict(r) for r in courses], "count": len(courses)}


def seed_demo_data():
    conn = get_conn()
    cnt = conn.execute("SELECT COUNT(*) FROM class_stu").fetchone()[0]
    if cnt > 0:
        conn.close()
        return
    data = [
        (1, "2024001"), (2, "2024001"), (3, "2024001"), (4, "2024001"),
        (5, "2024001"), (7, "2024001"), (8, "2024001"), (9, "2024001"),
        (11, "2024001"), (12, "2024001"), (14, "2024001"), (16, "2024001"),
        (2, "2024002"), (6, "2024002"), (10, "2024002"), (15, "2024002"),
    ]
    for cid, stu in data:
        conn.execute(
            "INSERT INTO class_stu (course_id, stu_num) VALUES (?, ?)",
            (cid, stu))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed_demo_data()
    import uvicorn
    print("class-stu API running on http://127.0.0.1:8001")
    uvicorn.run("class-stu:app", host="0.0.0.0", port=8001, reload=True)

app.include_router(router)
