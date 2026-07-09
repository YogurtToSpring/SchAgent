"""
    grade.py - 成绩管理模块

    负责学生成绩的录入、修改、删除、查询，支持按学号、课程号、教师号检索。
    与 student.py 共用绩点换算函数，与 course.py 联查课程学分信息。
"""

from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import sqlite3
import os
from dotenv import load_dotenv
from typing import Optional

# 从 student.py 导入绩点换算函数
from student import score_to_grade_point, score_to_grade_letter

load_dotenv()

app = FastAPI()

router = APIRouter(prefix="/api")

DATABASE = os.getenv("DATABASE_URL", "grade.db")
STUDENT_DB = os.getenv("STUDENTS_DB_PATH", "students.db")
COURSE_DB = os.getenv("COURSE_DB_PATH", "course.db")
TEACHER_DB = os.getenv("TEACHER_DB_PATH", "teacher.db")
CLASS_STU_DB = os.getenv("CLASS_STU_DB_PATH", "class_stu.db")


# ============================================================
# 数据库初始化
# ============================================================

def get_conn():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS grade(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id TEXT NOT NULL,
            stu_num TEXT NOT NULL,
            score REAL DEFAULT 0,
            semester TEXT NOT NULL,
            exam_type TEXT DEFAULT '期末考试',
            remark TEXT DEFAULT '',
            UNIQUE(course_id, stu_num, semester)
        )
    """)
    conn.commit()
    conn.close()

init_db()


# ============================================================
# Pydantic 模型
# ============================================================

class AddGrade(BaseModel):
    course_id: str
    stu_num: str
    score: float
    semester: str
    exam_type: str = "期末考试"
    remark: str = ""

class ChangeGrade(BaseModel):
    course_id: str
    stu_num: str
    score: float
    semester: str
    exam_type: str = "期末考试"
    remark: str = ""


# ============================================================
# 录入成绩接口
# 调用方式: POST /api/grade/add
# 请求体: { course_id, stu_num, score, semester, exam_type (可选), remark (可选) }
# 功能说明: 录入一条成绩记录，自动校验学生和课程是否存在
#           同学生同课程同学期不允许重复录入
# 权限说明: 仅暴露给 teacher 和 admin，teacher 只能录入自己课程的学生成绩
# ============================================================
@router.post("/grade/add")
def add_score(score_data: AddGrade):
    conn = get_conn()

    # 校验学生存在
    stu_conn = sqlite3.connect(STUDENT_DB)
    stu = stu_conn.execute(
        "SELECT * FROM students WHERE StuNum = ?", (score_data.stu_num,)
    ).fetchone()
    stu_conn.close()
    if not stu:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Student {score_data.stu_num} Not Found")
    
    # 校验课程存在
    cor_conn = sqlite3.connect(COURSE_DB)
    cor = cor_conn.execute(
        "SELECT * FROM course WHERE course_id = ?", (score_data.course_id,)
    ).fetchone()
    cor_conn.close()
    if not cor:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Course {score_data.course_id} Not Found")
    
    # 检查是否已存在
    existing = conn.execute(
        "SELECT id FROM grade WHERE course_id = ? AND stu_num = ? AND semester = ?",
        (score_data.course_id, score_data.stu_num, score_data.semester)
    ).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Course {score_data.course_id} & Student {score_data.stu_num} already exist in semester {score_data.semester}")

    conn.execute(
        "INSERT INTO grade (course_id, stu_num, score, semester, exam_type, remark) VALUES (?, ?, ?, ?, ?, ?)",
        (score_data.course_id, score_data.stu_num, score_data.score, score_data.semester, score_data.exam_type, score_data.remark)
    )

    conn.commit()
    conn.close()

    gp = score_to_grade_point(score_data.score)
    gl = score_to_grade_letter(score_data.score)
    return {
        "message": f"Score added successfully",
        "course_id": score_data.course_id,
        "stu_num": score_data.stu_num,
        "score": score_data.score,
        "grade_point": gp,
        "grade_letter": gl
    }


# ============================================================
# 修改成绩接口
# 调用方式: PATCH /api/grade/modify
# 请求体: { course_id, stu_num, score, semester, exam_type (可选), remark (可选) }
# 功能说明: 根据课程号+学号+学期定位已有记录并更新成绩
# 权限说明: 仅暴露给 teacher 和 admin
# ============================================================
@router.patch("/grade/modify")
def modify_score(new_info: ChangeGrade):
    conn = get_conn()

    # 校验学生存在
    stu_conn = sqlite3.connect(STUDENT_DB)
    stu = stu_conn.execute(
        "SELECT * FROM students WHERE StuNum = ?", (new_info.stu_num,)
    ).fetchone()
    stu_conn.close()
    if not stu:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Student {new_info.stu_num} Not Found")
    
    # 校验课程存在
    cor_conn = sqlite3.connect(COURSE_DB)
    cor = cor_conn.execute(
        "SELECT * FROM course WHERE course_id = ?", (new_info.course_id,)
    ).fetchone()
    cor_conn.close()
    if not cor:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Course {new_info.course_id} Not Found")
    
    # 查找已有记录
    existing = conn.execute(
        "SELECT id FROM grade WHERE course_id = ? AND stu_num = ? AND semester = ?",
        (new_info.course_id, new_info.stu_num, new_info.semester)
    ).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Record not found for Course {new_info.course_id} & Student {new_info.stu_num} & Semester {new_info.semester}")

    conn.execute(
        "UPDATE grade SET score = ?, exam_type = ?, remark = ? WHERE course_id = ? AND stu_num = ? AND semester = ?",
        (new_info.score, new_info.exam_type, new_info.remark, new_info.course_id, new_info.stu_num, new_info.semester)
    )

    conn.commit()
    conn.close()

    gp = score_to_grade_point(new_info.score)
    gl = score_to_grade_letter(new_info.score)
    return {
        "message": "Score modified successfully",
        "course_id": new_info.course_id,
        "stu_num": new_info.stu_num,
        "score": new_info.score,
        "grade_point": gp,
        "grade_letter": gl
    }


# ============================================================
# 删除成绩接口
# 调用方式: DELETE /api/grade/delete?grade_id=5
# 功能说明: 根据 grade 表 id 删除单条成绩记录
# 权限说明: 仅 admin 可调用
# ============================================================
@router.delete("/grade/delete")
def delete_grade(grade_id: int):
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM grade WHERE id = ?", (grade_id,)
    ).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Grade {grade_id} Not Found")

    conn.execute("DELETE FROM grade WHERE id = ?", (grade_id,))
    conn.commit()
    conn.close()
    return {"message": f"Grade {grade_id} deleted successfully"}


# ============================================================
# 查看全部成绩（管理用）接口
# 调用方式: GET /api/grade?semester=2024-2025-1
# 可选参数: semester（不传则返回全部）
# 功能说明: 返回全部成绩记录，按课程号+分数排序
# 权限说明: 仅 admin 可调用
# ============================================================
@router.get("/grade")
def list_all(semester: Optional[str] = None):
    conn = get_conn()
    if semester:
        rows = conn.execute(
            "SELECT * FROM grade WHERE semester = ? ORDER BY course_id, score",
            (semester,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM grade ORDER BY course_id, score",
        ).fetchall()
    conn.close()
    # 附加上绩点和等级
    result = []
    for r in rows:
        d = dict(r)
        d["grade_point"] = score_to_grade_point(r["score"])
        d["grade_letter"] = score_to_grade_letter(r["score"])
        result.append(d)
    return {"grades": result, "count": len(result)}


# ============================================================
# 学生查询个人成绩接口
# 调用方式: GET /api/grade/student/{stu_num}?semester=2024-2025-1
# 可选参数: semester（不传则返回全部学期）
# 功能说明: 返回指定学生的全部成绩，含每门课的课程名、学分、绩点、等级
# 权限说明: student 可查自己，admin 可查任意学生
# ============================================================
@router.get("/grade/student/{stu_num}")
def get_student_grades(stu_num: str, semester: Optional[str] = None):
    # 验证学生存在
    stu_conn = sqlite3.connect(STUDENT_DB)
    stu_conn.row_factory = sqlite3.Row
    student = stu_conn.execute(
        "SELECT Name, Cls FROM students WHERE StuNum = ?", (stu_num,)
    ).fetchone()
    stu_conn.close()
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {stu_num} Not Found!")

    conn = get_conn()
    if semester:
        rows = conn.execute(
            "SELECT * FROM grade WHERE stu_num = ? AND semester = ? ORDER BY course_id",
            (stu_num, semester)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM grade WHERE stu_num = ? ORDER BY semester, course_id",
            (stu_num,)
        ).fetchall()
    conn.close()

    if not rows:
        return {
            "stu_num": stu_num,
            "name": student["Name"],
            "cls": student["Cls"],
            "grades": [],
            "count": 0,
            "semester": semester or "all"
        }

    # 联查课程信息（课程名、学分）
    course_ids = list(set(r["course_id"] for r in rows))
    cor_conn = sqlite3.connect(COURSE_DB)
    cor_conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(course_ids))
    courses = cor_conn.execute(
        f"SELECT course_id, course_name, credit FROM course WHERE course_id IN ({placeholders})", course_ids
    ).fetchall()
    cor_conn.close()
    course_map = {c["course_id"]: {"course_name": c["course_name"], "credit": c["credit"]} for c in courses}

    result = []
    for r in rows:
        info = course_map.get(r["course_id"], {"course_name": "Unknown", "credit": 0})
        result.append({
            "id": r["id"],
            "course_id": r["course_id"],
            "course_name": info["course_name"],
            "credit": info["credit"],
            "score": r["score"],
            "grade_point": score_to_grade_point(r["score"]),
            "grade_letter": score_to_grade_letter(r["score"]),
            "semester": r["semester"],
            "exam_type": r["exam_type"],
            "remark": r["remark"]
        })

    return {
        "stu_num": stu_num,
        "name": student["Name"],
        "cls": student["Cls"],
        "grades": result,
        "count": len(result),
        "semester": semester or "all"
    }


# ============================================================
# 按课程查询成绩接口
# 调用方式: GET /api/grade/course/{course_id}
# 功能说明: 返回某门课程下所有学生的成绩，含学生姓名、班级、绩点等信息
# 权限说明: teacher 可查自己课程的，admin 可查所有
# ============================================================
@router.get("/grade/course/{course_id}")
def get_course_grades(course_id: str):
    # 验证课程存在
    cor_conn = sqlite3.connect(COURSE_DB)
    cor_conn.row_factory = sqlite3.Row
    course = cor_conn.execute(
        "SELECT * FROM course WHERE course_id = ?", (course_id,)
    ).fetchone()
    cor_conn.close()
    if not course:
        raise HTTPException(status_code=404, detail=f"Course {course_id} Not Found!")

    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM grade WHERE course_id = ? ORDER BY score DESC", (course_id,)
    ).fetchall()
    conn.close()

    # 联查学生姓名
    stu_nums = [r["stu_num"] for r in rows]
    stu_map = {}
    if stu_nums:
        stu_conn = sqlite3.connect(STUDENT_DB)
        stu_conn.row_factory = sqlite3.Row
        placeholders = ",".join("?" * len(stu_nums))
        students = stu_conn.execute(
            f"SELECT StuNum, Name, Cls FROM students WHERE StuNum IN ({placeholders})", stu_nums
        ).fetchall()
        stu_conn.close()
        stu_map = {s["StuNum"]: {"name": s["Name"], "cls": s["Cls"]} for s in students}

    result = []
    total_score = 0
    pass_count = 0
    for r in rows:
        info = stu_map.get(r["stu_num"], {"name": "Unknown", "cls": ""})
        total_score += r["score"]
        if r["score"] >= 60:
            pass_count += 1
        result.append({
            "id": r["id"],
            "stu_num": r["stu_num"],
            "name": info["name"],
            "cls": info["cls"],
            "score": r["score"],
            "grade_point": score_to_grade_point(r["score"]),
            "grade_letter": score_to_grade_letter(r["score"]),
            "semester": r["semester"],
            "exam_type": r["exam_type"],
            "remark": r["remark"]
        })

    avg_score = round(total_score / len(result), 1) if result else 0
    pass_rate = round(pass_count / len(result) * 100, 1) if result else 0

    return {
        "course_id": course_id,
        "course_name": course["course_name"],
        "course_credit": course["credit"],
        "teacher_num": course["teacher_num"],
        "semester": course["semester"],
        "students": result,
        "count": len(result),
        "stats": {
            "avg_score": avg_score,
            "max_score": max(r["score"] for r in rows) if rows else 0,
            "min_score": min(r["score"] for r in rows) if rows else 0,
            "pass_rate": pass_rate,
            "pass_count": pass_count
        }
    }


# ============================================================
# 教师查询所教课程成绩接口
# 调用方式: GET /api/grade/teacher/{teacher_num}
# 功能说明: 返回指定教师所有课程的全部学生成绩（按课程分组）
# 权限说明: teacher 可查自己，admin 可查任意教师
# ============================================================
@router.get("/grade/teacher/{teacher_num}")
def get_teacher_grades(teacher_num: str):
    # 验证教师存在
    tea_conn = sqlite3.connect(TEACHER_DB)
    tea_conn.row_factory = sqlite3.Row
    teacher = tea_conn.execute(
        "SELECT Name FROM teacher WHERE Number = ?", (teacher_num,)
    ).fetchone()
    tea_conn.close()
    if not teacher:
        raise HTTPException(status_code=404, detail=f"Teacher {teacher_num} Not Found!")

    # 查找该教师的所有课程
    cor_conn = sqlite3.connect(COURSE_DB)
    cor_conn.row_factory = sqlite3.Row
    courses = cor_conn.execute(
        "SELECT * FROM course WHERE teacher_num = ?", (teacher_num,)
    ).fetchall()
    cor_conn.close()

    if not courses:
        return {
            "teacher_num": teacher_num,
            "teacher_name": teacher["Name"],
            "courses": [],
            "count": 0
        }

    # 对每门课程查询成绩
    conn = get_conn()
    result = []
    for course in courses:
        grade_rows = conn.execute(
            "SELECT * FROM grade WHERE course_id = ? ORDER BY score DESC", (course["course_id"],)
        ).fetchall()

        # 联查学生姓名
        stu_nums = [r["stu_num"] for r in grade_rows]
        stu_map = {}
        if stu_nums:
            stu_conn = sqlite3.connect(STUDENT_DB)
            stu_conn.row_factory = sqlite3.Row
            placeholders = ",".join("?" * len(stu_nums))
            students = stu_conn.execute(
                f"SELECT StuNum, Name, Cls FROM students WHERE StuNum IN ({placeholders})", stu_nums
            ).fetchall()
            stu_conn.close()
            stu_map = {s["StuNum"]: {"name": s["Name"], "cls": s["Cls"]} for s in students}

        students_list = []
        for g in grade_rows:
            info = stu_map.get(g["stu_num"], {"name": "Unknown", "cls": ""})
            students_list.append({
                "stu_num": g["stu_num"],
                "name": info["name"],
                "cls": info["cls"],
                "score": g["score"],
                "grade_point": score_to_grade_point(g["score"]),
                "grade_letter": score_to_grade_letter(g["score"]),
                "semester": g["semester"],
                "exam_type": g["exam_type"],
                "remark": g["remark"]
            })

        total_score = sum(g["score"] for g in grade_rows) if grade_rows else 0
        pass_count = sum(1 for g in grade_rows if g["score"] >= 60) if grade_rows else 0
        avg_score = round(total_score / len(grade_rows), 1) if grade_rows else 0
        pass_rate = round(pass_count / len(grade_rows) * 100, 1) if grade_rows else 0

        result.append({
            "course_id": course["course_id"],
            "course_name": course["course_name"],
            "credit": course["credit"],
            "semester": course["semester"],
            "students": students_list,
            "count": len(students_list),
            "stats": {
                "avg_score": avg_score,
                "max_score": max(g["score"] for g in grade_rows) if grade_rows else 0,
                "min_score": min(g["score"] for g in grade_rows) if grade_rows else 0,
                "pass_rate": pass_rate,
                "pass_count": pass_count
            }
        })

    conn.close()

    return {
        "teacher_num": teacher_num,
        "teacher_name": teacher["Name"],
        "courses": result,
        "count": len(result)
    }


app.include_router(router)