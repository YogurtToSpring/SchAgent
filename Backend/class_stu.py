from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import sqlite3
import os

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
            course_id INTEGER NOT NULL,
            stu_num TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cs_course ON class_stu(course_id);
        CREATE INDEX IF NOT EXISTS idx_cs_student ON class_stu(stu_num);
    """)
    conn.commit()
    conn.close()

init_db()


class EnrollRequest(BaseModel):
    course_id: int
    stu_num: str


class DeleteEnrollRequest(BaseModel):
    course_id: int
    stu_num: str


@router.post("/class-stu/enroll")
def enroll(req: EnrollRequest):
    conn = get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM class_stu WHERE course_id = ? AND stu_num = ?",
            (req.course_id, req.stu_num)).fetchone()
        if existing:
            conn.close()
            return {"message": "Already enrolled", "id": existing["id"]}
        cur = conn.execute(
            "INSERT INTO class_stu (course_id, stu_num) VALUES (?, ?)",
            (req.course_id, req.stu_num))
        conn.commit()
        return {"message": "Enrolled successfully", "id": cur.lastrowid}
    finally:
        conn.close()


@router.delete("/class-stu/enroll")
def drop_course(req: DeleteEnrollRequest):
    conn = get_conn()
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


@router.get("/class-stu/student/{stu_num}")
def get_student_courses(stu_num: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM class_stu WHERE stu_num = ?", (stu_num,)).fetchall()
    conn.close()
    return {"stu_num": stu_num, "courses": [dict(r) for r in rows], "count": len(rows)}


@router.get("/class-stu/course/{course_id}")
def get_course_students(course_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM class_stu WHERE course_id = ?", (course_id,)).fetchall()
    conn.close()
    return {"course_id": course_id, "students": [dict(r) for r in rows], "count": len(rows)}


@router.get("/class-stu")
def list_all():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM class_stu ORDER BY stu_num, course_id").fetchall()
    conn.close()
    return {"enrollments": [dict(r) for r in rows], "count": len(rows)}


app.include_router(router)


# ---- 学生查询完整课程详情（跨库 JOIN）----
COURSE_DB = os.getenv("COURSE_DB_PATH", "course.db")


@router.get("/class-stu/student/{stu_num}/details")
def get_student_course_details(stu_num: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT course_id FROM class_stu WHERE stu_num = ?", (stu_num,)).fetchall()
    conn.close()

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
