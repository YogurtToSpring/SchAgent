from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import sqlite3
import os
from dotenv import load_dotenv
from typing import Optional

from student import score_to_grade_point, score_to_grade_letter

load_dotenv()

app = FastAPI()
router = APIRouter(prefix="/api")

DATABASE = os.getenv("DATABASE_URL", "grade.db")
STUDENT_DB = os.getenv("STUDENTS_DB_PATH", "students.db")
COURSE_DB = os.getenv("COURSE_DB_PATH", "course.db")
TEACHER_DB = os.getenv("TEACHER_DB_PATH", "teacher.db")
CLASS_STU_DB = os.getenv("CLASS_STU_DB_PATH", "class_stu.db")

def compute_score(regular: float, final: float) -> float:
    return round(0.4 * regular + 0.6 * final, 1)

def get_conn():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS grade(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id TEXT NOT NULL,
            stu_num TEXT NOT NULL,
            score REAL DEFAULT 0,
            regular_score REAL DEFAULT NULL,
            final_score REAL DEFAULT NULL,
            semester TEXT NOT NULL,
            exam_type TEXT DEFAULT '期末考试',
            remark TEXT DEFAULT '',
            UNIQUE(course_id, stu_num, semester)
        )
    """)
    for col in ["regular_score", "final_score"]:
        try:
            conn.execute(f"ALTER TABLE grade ADD COLUMN {col} REAL DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

init_db()

conn2 = sqlite3.connect(DATABASE)
try:
    conn2.execute("CREATE INDEX IF NOT EXISTS idx_grade_lookup ON grade(course_id, stu_num, semester)")
except sqlite3.OperationalError:
    pass
conn2.close()

class AddGrade(BaseModel):
    course_id: str
    stu_num: str
    regular_score: float
    final_exam_score: float
    semester: str
    exam_type: str = "期末考试"
    remark: str = ""

class ChangeGrade(BaseModel):
    course_id: str
    stu_num: str
    regular_score: float
    final_exam_score: float
    semester: str
    exam_type: str = "期末考试"
    remark: str = ""


class DeleteGrade(BaseModel):
    course_id: str
    stu_num: str
    semester: str

# 录入成绩，teacher/admin可调用
@router.post("/grade/add")
def add_score(data: AddGrade):
    conn = get_conn()

    str_con = sqlite3.connect(STUDENT_DB)
    if not str_con.execute("SELECT 1 FROM students WHERE StuNum=?", (data.stu_num,)).fetchone():
        str_con.close(); conn.close()
        raise HTTPException(400, f"Student {data.stu_num} Not Found")
    str_con.close()

    cor_con = sqlite3.connect(COURSE_DB)
    if not cor_con.execute("SELECT 1 FROM course WHERE course_id=?", (data.course_id,)).fetchone():
        cor_con.close(); conn.close()
        raise HTTPException(400, f"Course {data.course_id} Not Found")
    cor_con.close()

    if conn.execute("SELECT id FROM grade WHERE course_id=? AND stu_num=? AND semester=?",
                    (data.course_id, data.stu_num, data.semester)).fetchone():
        conn.close()
        raise HTTPException(400, f"Duplicate: {data.course_id} / {data.stu_num} / {data.semester}")

    final = compute_score(data.regular_score, data.final_exam_score)
    conn.execute(
        "INSERT INTO grade (course_id, stu_num, score, regular_score, final_score, semester, exam_type, remark) VALUES (?,?,?,?,?,?,?,?)",
        (data.course_id, data.stu_num, final, data.regular_score, data.final_exam_score,
         data.semester, data.exam_type, data.remark)
    )
    conn.commit()
    conn.close()

    gp = score_to_grade_point(final)
    gl = score_to_grade_letter(final)
    return {
        "message": "Score added successfully",
        "course_id": data.course_id, "stu_num": data.stu_num,
        "regular_score": data.regular_score, "final_exam_score": data.final_exam_score,
        "final_score": final, "grade_point": gp, "grade_letter": gl,
    }


# 修改成绩，teacher可调用
@router.patch("/grade/modify")
def modify_score(data: ChangeGrade):
    conn = get_conn()

    str_con = sqlite3.connect(STUDENT_DB)
    if not str_con.execute("SELECT 1 FROM students WHERE StuNum=?", (data.stu_num,)).fetchone():
        str_con.close(); conn.close()
        raise HTTPException(400, f"Student {data.stu_num} Not Found")
    str_con.close()

    cor_con = sqlite3.connect(COURSE_DB)
    if not cor_con.execute("SELECT 1 FROM course WHERE course_id=?", (data.course_id,)).fetchone():
        cor_con.close(); conn.close()
        raise HTTPException(400, f"Course {data.course_id} Not Found")
    cor_con.close()

    existing = conn.execute("SELECT id FROM grade WHERE course_id=? AND stu_num=? AND semester=?",
                           (data.course_id, data.stu_num, data.semester)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(400, f"Record not found")

    final = compute_score(data.regular_score, data.final_exam_score)
    conn.execute(
        "UPDATE grade SET score=?, regular_score=?, final_score=?, exam_type=?, remark=? WHERE course_id=? AND stu_num=? AND semester=?",
        (final, data.regular_score, data.final_exam_score, data.exam_type, data.remark,
         data.course_id, data.stu_num, data.semester)
    )
    conn.commit()
    conn.close()

    gp = score_to_grade_point(final)
    gl = score_to_grade_letter(final)
    return {
        "message": "Score modified successfully",
        "course_id": data.course_id, "stu_num": data.stu_num,
        "regular_score": data.regular_score, "final_exam_score": data.final_exam_score,
        "final_score": final, "grade_point": gp, "grade_letter": gl,
    }


# 删除成绩，仅admin
@router.delete("/grade/delete")
def delete_grade(data: DeleteGrade):
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM grade WHERE course_id=? AND stu_num=? AND semester=?",
        (data.course_id, data.stu_num, data.semester)
    ).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(404, detail=f"Grade not found for {data.course_id} / {data.stu_num} / {data.semester}")
    conn.execute(
        "DELETE FROM grade WHERE course_id=? AND stu_num=? AND semester=?",
        (data.course_id, data.stu_num, data.semester)
    )
    conn.commit()
    conn.close()
    return {"message": f"Grade deleted: {data.course_id} / {data.stu_num} / {data.semester}"}


# 查看全部成绩（admin）
@router.get("/grade")
def list_all(semester: Optional[str] = None):
    conn = get_conn()
    if semester:
        rows = conn.execute("SELECT * FROM grade WHERE semester=? ORDER BY course_id, score", (semester,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM grade ORDER BY course_id, score").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["final_exam_score"] = d.pop("final_score", None)
        d["final_score"] = r["score"]
        d["grade_point"] = score_to_grade_point(r["score"])
        d["grade_letter"] = score_to_grade_letter(r["score"])
        result.append(d)
    return {"grades": result, "count": len(result)}


# 学生查询个人成绩，学生课调用
@router.get("/grade/student/{stu_num}")
def get_student_grades(stu_num: str, semester: Optional[str] = None):
    stu_con = sqlite3.connect(STUDENT_DB)
    stu_con.row_factory = sqlite3.Row
    student = stu_con.execute("SELECT Name, Cls FROM students WHERE StuNum=?", (stu_num,)).fetchone()
    stu_con.close()
    if not student:
        raise HTTPException(404, f"Student {stu_num} Not Found!")

    conn = get_conn()
    if semester:
        rows = conn.execute("SELECT * FROM grade WHERE stu_num=? AND semester=? ORDER BY course_id",
                           (stu_num, semester)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM grade WHERE stu_num=? ORDER BY semester, course_id", (stu_num,)).fetchall()
    conn.close()

    if not rows:
        return {"stu_num": stu_num, "name": student["Name"], "cls": student["Cls"],
                "grades": [], "count": 0, "semester": semester or "all"}

    course_ids = list(set(r["course_id"] for r in rows))
    cor_con = sqlite3.connect(COURSE_DB)
    cor_con.row_factory = sqlite3.Row
    ph = ",".join("?" * len(course_ids))
    courses = cor_con.execute(f"SELECT course_id, course_name, credit FROM course WHERE course_id IN ({ph})", course_ids).fetchall()
    cor_con.close()
    cmap = {c["course_id"]: {"course_name": c["course_name"], "credit": c["credit"]} for c in courses}

    result = []
    for r in rows:
        info = cmap.get(r["course_id"], {"course_name": "Unknown", "credit": 0})
        result.append({
            "id": r["id"], "course_id": r["course_id"],
            "course_name": info["course_name"], "credit": info["credit"],
            "regular_score": r["regular_score"], "final_exam_score": r["final_score"],
            "final_score": r["score"],
            "grade_point": score_to_grade_point(r["score"]),
            "grade_letter": score_to_grade_letter(r["score"]),
            "semester": r["semester"], "exam_type": r["exam_type"], "remark": r["remark"],
        })

    return {"stu_num": stu_num, "name": student["Name"], "cls": student["Cls"],
            "grades": result, "count": len(result), "semester": semester or "all"}


# 按课程查询成绩，teacher/admin可调用
@router.get("/grade/course/{course_id}")
def get_course_grades(course_id: str):
    cor_con = sqlite3.connect(COURSE_DB)
    cor_con.row_factory = sqlite3.Row
    course = cor_con.execute("SELECT * FROM course WHERE course_id=?", (course_id,)).fetchone()
    cor_con.close()
    if not course:
        raise HTTPException(404, f"Course {course_id} Not Found!")

    conn = get_conn()
    rows = conn.execute("SELECT * FROM grade WHERE course_id=? ORDER BY score DESC", (course_id,)).fetchall()
    conn.close()

    stu_nums = [r["stu_num"] for r in rows]
    stu_map = {}
    if stu_nums:
        s_con = sqlite3.connect(STUDENT_DB)
        s_con.row_factory = sqlite3.Row
        ph = ",".join("?" * len(stu_nums))
        students = s_con.execute(f"SELECT StuNum, Name, Cls FROM students WHERE StuNum IN ({ph})", stu_nums).fetchall()
        s_con.close()
        stu_map = {s["StuNum"]: {"name": s["Name"], "cls": s["Cls"]} for s in students}

    result = []
    total_score = pass_count = 0
    for r in rows:
        info = stu_map.get(r["stu_num"], {"name": "Unknown", "cls": ""})
        total_score += r["score"]
        if r["score"] >= 60: pass_count += 1
        result.append({
            "id": r["id"], "stu_num": r["stu_num"],
            "name": info["name"], "cls": info["cls"],
            "regular_score": r["regular_score"], "final_exam_score": r["final_score"],
            "final_score": r["score"],
            "grade_point": score_to_grade_point(r["score"]),
            "grade_letter": score_to_grade_letter(r["score"]),
            "semester": r["semester"], "exam_type": r["exam_type"], "remark": r["remark"],
        })

    n = len(result)
    return {
        "course_id": course_id, "course_name": course["course_name"],
        "course_credit": course["credit"], "teacher_num": course["teacher_num"],
        "semester": course["semester"], "students": result, "count": n,
        "stats": {
            "avg_score": round(total_score / n, 1) if n else 0,
            "max_score": max(r["score"] for r in rows) if rows else 0,
            "min_score": min(r["score"] for r in rows) if rows else 0,
            "pass_rate": round(pass_count / n * 100, 1) if n else 0,
            "pass_count": pass_count,
        }
    }


# 教师查询所教课程成绩
@router.get("/grade/teacher/{teacher_num}")
def get_teacher_grades(teacher_num: str):
    t_con = sqlite3.connect(TEACHER_DB)
    t_con.row_factory = sqlite3.Row
    teacher = t_con.execute("SELECT Name FROM teacher WHERE Number=?", (teacher_num,)).fetchone()
    t_con.close()
    if not teacher:
        raise HTTPException(404, f"Teacher {teacher_num} Not Found!")

    cor_con = sqlite3.connect(COURSE_DB)
    cor_con.row_factory = sqlite3.Row
    courses = cor_con.execute("SELECT * FROM course WHERE teacher_num=?", (teacher_num,)).fetchall()
    cor_con.close()
    if not courses:
        return {"teacher_num": teacher_num, "teacher_name": teacher["Name"], "courses": [], "count": 0}

    conn = get_conn()
    result = []
    for course in courses:
        grade_rows = conn.execute("SELECT * FROM grade WHERE course_id=? ORDER BY score DESC", (course["course_id"],)).fetchall()

        stu_nums = [r["stu_num"] for r in grade_rows]
        stu_map = {}
        if stu_nums:
            s_con = sqlite3.connect(STUDENT_DB)
            s_con.row_factory = sqlite3.Row
            ph = ",".join("?" * len(stu_nums))
            students = s_con.execute(f"SELECT StuNum, Name, Cls FROM students WHERE StuNum IN ({ph})", stu_nums).fetchall()
            s_con.close()
            stu_map = {s["StuNum"]: {"name": s["Name"], "cls": s["Cls"]} for s in students}

        slist = []
        total_s = pass_c = 0
        for g in grade_rows:
            info = stu_map.get(g["stu_num"], {"name": "Unknown", "cls": ""})
            total_s += g["score"]
            if g["score"] >= 60: pass_c += 1
            slist.append({
                "stu_num": g["stu_num"], "name": info["name"], "cls": info["cls"],
                "regular_score": g["regular_score"], "final_exam_score": g["final_score"],
                "final_score": g["score"],
                "grade_point": score_to_grade_point(g["score"]),
                "grade_letter": score_to_grade_letter(g["score"]),
                "semester": g["semester"], "exam_type": g["exam_type"], "remark": g["remark"],
            })

        n = len(slist)
        result.append({
            "course_id": course["course_id"], "course_name": course["course_name"],
            "credit": course["credit"], "semester": course["semester"],
            "students": slist, "count": n,
            "stats": {
                "avg_score": round(total_s / n, 1) if n else 0,
                "max_score": max(g["score"] for g in grade_rows) if grade_rows else 0,
                "min_score": min(g["score"] for g in grade_rows) if grade_rows else 0,
                "pass_rate": round(pass_c / n * 100, 1) if n else 0,
                "pass_count": pass_c,
            }
        })

    conn.close()
    return {"teacher_num": teacher_num, "teacher_name": teacher["Name"],
            "courses": result, "count": len(result)}

app.include_router(router)
