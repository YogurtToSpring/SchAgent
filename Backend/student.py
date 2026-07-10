"""
    student.py - 学生信息管理模块

    负责学生信息的注册、登录、改密、班级修改等功能。
    绩点计算函数与GPA查询接口也实现在此模块中。
"""

from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import sqlite3
from passlib.hash import pbkdf2_sha256
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

app = FastAPI()

router = APIRouter(prefix="/api")

DATABASE = os.getenv("DATABASE_URL", "students.db")
COURSE_DB = os.getenv("COURSE_DB_PATH", "course.db")


# ============================================================
# 绩点换算函数
# ============================================================

def score_to_grade_point(score: float) -> float:
    """将百分制成绩换算为4.0制绩点"""
    if score >= 90: return 4.0
    if score >= 85: return 3.7
    if score >= 82: return 3.3
    if score >= 78: return 3.0
    if score >= 75: return 2.7
    if score >= 72: return 2.3
    if score >= 68: return 2.0
    if score >= 64: return 1.5
    if score >= 60: return 1.0
    return 0.0

def score_to_grade_letter(score: float) -> str:
    """将百分制成绩换算为等级制"""
    if score >= 90: return "A"
    if score >= 85: return "A-"
    if score >= 82: return "B+"
    if score >= 78: return "B"
    if score >= 75: return "B-"
    if score >= 72: return "C+"
    if score >= 68: return "C"
    if score >= 64: return "D+"
    if score >= 60: return "D"
    return "F"


# ============================================================
# 数据库初始化
# ============================================================

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            StuNum TEXT UNIQUE NOT NULL,
            Cls TEXT,
            password_hash TEXT NOT NULL,
            gpa REAL DEFAULT 0.0
        )
    """)
    # 兼容旧数据库：如果 gpa 列不存在则补加
    try:
        conn.execute("ALTER TABLE students ADD COLUMN gpa REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

def hash_password(password: str) -> str:
    return pbkdf2_sha256.hash(password)

def verify_password(password: str, hash_value: str) -> bool:
    return pbkdf2_sha256.verify(password, hash_value)


# ============================================================
# Pydantic 模型
# ============================================================

class StudentRegister(BaseModel):
    Name: str
    StuNum: str
    Cls: str
    password: str

class StudentLogin(BaseModel):
    StuNum: str
    password: str

class PasswordChange(BaseModel):
    old_password: str
    new_password: str


# ============================================================
# 学生注册接口
# 调用方式: POST /api/students/register
# 请求体: { Name, StuNum, Cls, password }
# 功能说明: 注册新学生账号，学号唯一
# 权限说明: 演示时关闭，仅内部开发人员手动调用。可暴露给admin用于手动注册
# ============================================================
@router.post("/students/register")
def register(student_data: StudentRegister):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    existing = conn.execute("SELECT id FROM students WHERE StuNum = ?", (student_data.StuNum,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Hey bro, you have just got your account")
    
    hashed = hash_password(student_data.password)
    conn.execute(
        "INSERT INTO students (Name, StuNum, Cls, password_hash) VALUES (?, ?, ?, ?)",
        (student_data.Name, student_data.StuNum, student_data.Cls, hashed)
    )
    conn.commit()
    conn.close()
    
    return {"message": f"Student {student_data.Name} registered successfully!"}


# ============================================================
# 学生登录接口
# 调用方式: POST /api/students/login
# 请求体: { StuNum, password }
# 功能说明: 学号+密码登录，验证密码哈希
# 权限说明: 对student开放，前端传入学号和密码
# ============================================================
@router.post("/students/login")
def login(student_data: StudentLogin):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM students WHERE StuNum = ?", (student_data.StuNum,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Login Failure")
    if not verify_password(student_data.password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=404, detail="Permmission Denied. Authentification Failure")
    conn.close()
    return {"message": f"Student {row['Name']} login successfully!"}


# ============================================================
# 查看全部学生接口
# 调用方式: GET /api/students
# 功能说明: 返回所有学生列表（不含密码），含GPA字段
# 权限说明: 不对外开放，仅内部开发人员查看。可提供给admin作为参考
# ============================================================
@router.get("/students")
def list_students():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, Name, Cls, StuNum, gpa FROM students").fetchall()
    conn.close()
    return {"students": [dict(row) for row in rows]}


# ============================================================
# 删除学生接口
# 调用方式: DELETE /api/students/delete?student_id=2024001
# 功能说明: 根据学号删除学生
# 权限说明: 不对外开放，仅内部开发人员使用。可提供给admin
# ============================================================
@router.delete("/students/delete")
def delete_student(student_id: str):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM students WHERE StuNum = ?", (student_id,)).fetchone()
    if not rows:
        conn.close()
        raise HTTPException(status_code=404, detail="Student does not exist")
    conn.execute(
        "DELETE FROM students WHERE StuNum = ?", (student_id,)
    )

    conn.commit()
    conn.close()    
    return {"message": f"Student {student_id} deleted successfully"}


# ============================================================
# 修改学生班级接口
# 调用方式: PATCH /api/students/{student_id}/Cls?newcls=CS101
# 功能说明: 修改指定学生的班级，需校验班级是否存在
# 权限说明: 不暴露给student和teacher，仅admin可调用，建议加确认提示
# ============================================================
@router.patch("/students/{student_id}/Cls")
def change_cls(student_id: str, newcls: str):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    student = conn.execute("SELECT * FROM students WHERE StuNum = ?", (student_id,)).fetchone()
    if not student:
        conn.close()
        raise HTTPException(status_code=404, detail="Student does not exist")
    
    class_conn = sqlite3.connect("classi.db")
    class_conn.row_factory = sqlite3.Row
    cls = class_conn.execute(
        "SELECT * FROM classi WHERE class_id = ?", (newcls,)
    ).fetchone()
    class_conn.close()
    if not cls:
        conn.close()
        raise HTTPException(status_code=400, detail="Class Not Found")


    if student["Cls"] == newcls:
        conn.close()
        raise HTTPException(status_code=400, detail="Class number had not been changed")
    
    conn.execute(
        "UPDATE students SET Cls = ? WHERE StuNum = ?",
        (newcls, student_id)
    )
    conn.commit()
    conn.close()

    return {"message": "class changed successfully"}


# ============================================================
# 修改密码接口
# 调用方式: PUT /api/students/{student_num}/password
# 请求体: { old_password, new_password }
# 功能说明: 验证旧密码后更新为新密码
# 权限说明: student_num 由前端自动传入当前登录账号，不暴露给用户手动填写
# ============================================================
@router.put("/students/{student_num}/password")
def change_password(student_num: str, password_data: PasswordChange):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    student = conn.execute("SELECT * FROM students WHERE StuNum = ?", (student_num,)).fetchone()
    if not student:
        conn.close()
        raise HTTPException(status_code=404, detail="Student does not exist")
    
    if not verify_password(password_data.old_password, student["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="Wrong password")
    
    if password_data.new_password == password_data.old_password:
        conn.close()
        raise HTTPException(status_code=400, detail="New password should not be the same with the old one!")
    
    new_hashed = hash_password(password_data.new_password)
    conn.execute(
        "UPDATE students SET password_hash = ? WHERE StuNum = ?",
        (new_hashed, student_num)
    )
    conn.commit()
    conn.close()
    
    return {"message": "Password modified successfully"}

@router.post("/students/{stu_num}/modify1")
def modify1(new_info: StudentRegister):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    # student = conn.execute("SELECT * FROM students WHERE StuNum = ?", (new_info.StuNum,)).fetchone()

    conn.execute(
        "UPDATE students SET Name = ? WHERE StuNum = ?",
        (new_info.Name, new_info.StuNum)
    )
    conn.commit()
    conn.close()
@router.post("/students/{stu_num}/modify2")
def modify2(new_info: StudentRegister):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    # student = conn.execute("SELECT * FROM students WHERE StuNum = ?", (new_info.StuNum,)).fetchone()

    conn.execute(
        "UPDATE students SET StuNum = ? WHERE Name = ?",
        (new_info.StuNum, new_info.Name)
    )
    conn.commit()
    conn.close()

# ============================================================
# 计算学生GPA接口
# 调用方式: GET /api/students/{stu_num}/gpa?semester=2024-2025-1
# 可选参数: semester（不传则计算全部学期的累计GPA）
# 功能说明: 根据 grade.db 中的成绩按学分加权计算 GPA，同时返回各课程明细和学期汇总
#          每次计算结果自动更新 students 表的 gpa 缓存字段
# 响应包含: 总GPA、已修学分、获得学分、各课程详情、各学期GPA
# 权限说明: student可查自己，admin可查任意学生
# ============================================================
@router.get("/students/{stu_num}/gpa")
def calculate_student_gpa(stu_num: str, semester: Optional[str] = None):
    # 验证学生存在
    stu_conn = sqlite3.connect(DATABASE)
    stu_conn.row_factory = sqlite3.Row
    student = stu_conn.execute(
        "SELECT Name, Cls FROM students WHERE StuNum = ?", (stu_num,)
    ).fetchone()
    if not student:
        stu_conn.close()
        raise HTTPException(status_code=404, detail=f"Student {stu_num} Not Found!")
    stu_conn.close()
    
    # 从 grade.db 查询成绩
    grade_conn = sqlite3.connect("grade.db")
    grade_conn.row_factory = sqlite3.Row
    
    if semester:
        grade_rows = grade_conn.execute(
            "SELECT course_id, score, semester FROM grade WHERE stu_num = ? AND semester = ?",
            (stu_num, semester)
        ).fetchall()
    else:
        grade_rows = grade_conn.execute(
            "SELECT course_id, score, semester FROM grade WHERE stu_num = ? ORDER BY semester",
            (stu_num,)
        ).fetchall()
    grade_conn.close()
    
    if not grade_rows:
        return {
            "stu_num": stu_num,
            "name": student["Name"],
            "cls": student["Cls"],
            "gpa": 0.0,
            "total_credits_taken": 0,
            "total_credits_earned": 0,
            "course_count": 0,
            "courses": [],
            "by_semester": {},
            "semester": semester or "all"
        }
    
    # 获取课程学分
    course_ids = [r["course_id"] for r in grade_rows]
    conn = sqlite3.connect(COURSE_DB)
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(course_ids))
    credit_rows = conn.execute(
        f"SELECT course_id, course_name, credit FROM course WHERE course_id IN ({placeholders})", course_ids
    ).fetchall()
    conn.close()
    credit_map = {r["course_id"]: {"credit": r["credit"], "course_name": r["course_name"]} for r in credit_rows}
    
    # 计算GPA
    total_weighted = 0.0
    total_credits_taken = 0.0
    total_credits_earned = 0.0
    detail = []
    
    for g in grade_rows:
        info = credit_map.get(g["course_id"], {"credit": 0, "course_name": "Unknown"})
        gp = score_to_grade_point(g["score"])
        credit = info["credit"]
        total_weighted += gp * credit
        total_credits_taken += credit
        if g["score"] >= 60:
            total_credits_earned += credit
        detail.append({
            "course_id": g["course_id"],
            "course_name": info["course_name"],
            "score": g["score"],
            "grade_point": gp,
            "grade_letter": score_to_grade_letter(g["score"]),
            "credit": credit,
            "semester": g["semester"]
        })
    
    gpa = round(total_weighted / total_credits_taken, 2) if total_credits_taken > 0 else 0.0
    
    # 按学期分组汇总
    semester_summary = {}
    for d in detail:
        sem = d["semester"]
        if sem not in semester_summary:
            semester_summary[sem] = {"gpa": 0.0, "credits_taken": 0, "credits_earned": 0, "count": 0}
        semester_summary[sem]["credits_taken"] += d["credit"]
        semester_summary[sem]["credits_earned"] += d["credit"] if d["grade_point"] > 0 else 0
        semester_summary[sem]["count"] += 1
    
    for sem, stats in semester_summary.items():
        sem_details = [d for d in detail if d["semester"] == sem]
        sem_weighted = sum(d["grade_point"] * d["credit"] for d in sem_details)
        sem_credits = sum(d["credit"] for d in sem_details)
        stats["gpa"] = round(sem_weighted / sem_credits, 2) if sem_credits > 0 else 0.0
    
    # 更新缓存到 students.gpa
    stu_upd = sqlite3.connect(DATABASE)
    stu_upd.execute("UPDATE students SET gpa = ? WHERE StuNum = ?", (gpa, stu_num))
    stu_upd.commit()
    stu_upd.close()
    
    return {
        "stu_num": stu_num,
        "name": student["Name"],
        "cls": student["Cls"],
        "gpa": gpa,
        "total_credits_taken": total_credits_taken,
        "total_credits_earned": total_credits_earned,
        "course_count": len(detail),
        "courses": detail,
        "by_semester": semester_summary,
        "semester": semester or "all"
    }


# ============================================================
# 批量刷新所有学生GPA接口
# 调用方式: POST /api/students/gpa/refresh
# 功能说明: 遍历所有有成绩记录的学生，重新计算GPA并更新students表的gpa字段
#           students.gpa 为汇总缓存字段，方便前端直接展示无需每次实时计算
# 权限说明: 仅admin可调用，通常在每次录入/修改成绩后触发一次
# ============================================================
@router.post("/students/gpa/refresh")
def refresh_all_gpa():
    grade_conn = sqlite3.connect("grade.db")
    grade_conn.row_factory = sqlite3.Row
    stu_nums = grade_conn.execute(
        "SELECT DISTINCT stu_num FROM grade"
    ).fetchall()
    grade_conn.close()
    
    updated_count = 0
    for row in stu_nums:
        stu_num = row["stu_num"]
        
        g_conn = sqlite3.connect("grade.db")
        g_conn.row_factory = sqlite3.Row
        grade_rows = g_conn.execute(
            "SELECT course_id, score FROM grade WHERE stu_num = ?", (stu_num,)
        ).fetchall()
        g_conn.close()
        
        if not grade_rows:
            continue
        
        course_ids = [r["course_id"] for r in grade_rows]
        c_conn = sqlite3.connect(COURSE_DB)
        c_conn.row_factory = sqlite3.Row
        placeholders = ",".join("?" * len(course_ids))
        credit_rows = c_conn.execute(
            f"SELECT course_id, credit FROM course WHERE course_id IN ({placeholders})", course_ids
        ).fetchall()
        c_conn.close()
        credit_map = {r["course_id"]: r["credit"] for r in credit_rows}
        
        total_weighted = 0.0
        total_credit = 0.0
        for g in grade_rows:
            gp = score_to_grade_point(g["score"])
            cr = credit_map.get(g["course_id"], 0)
            total_weighted += gp * cr
            total_credit += cr
        
        gpa = round(total_weighted / total_credit, 2) if total_credit > 0 else 0.0
        stu_conn = sqlite3.connect(DATABASE)
        stu_conn.execute(
            "UPDATE students SET gpa = ? WHERE StuNum = ?", (gpa, stu_num)
        )
        stu_conn.commit()
        stu_conn.close()
        updated_count += 1
    
    return {"message": f"GPA refreshed for {updated_count} students"}


app.include_router(router)