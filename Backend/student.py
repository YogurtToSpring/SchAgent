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

def score_to_grade_point(score: float) -> float:
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


# 学生注册接口
# 注册新学生账号，学号唯一
# 演示时关闭，仅内部开发人员手动调用。可暴露给admin用于手动注册
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


# 学生登录接口
# 对student开放，前端传入学号和密码
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


# 查看全部学生接口
# 不对外开放，仅内部开发人员查看。可提供给admin作为参考
@router.get("/students")
def list_students():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, Name, Cls, StuNum, gpa FROM students").fetchall()
    conn.close()
    return {"students": [dict(row) for row in rows]}


# 根据学号删除学生
# 不对外开放，仅内部开发人员使用。可提供给admin
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


# 修改学生班级接口
# 不暴露给student和teacher，仅admin可调用，建议加确认提示
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


# 修改密码接口
# student_num 由前端自动传入当前登录账号，不暴露给用户手动填写
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

# 计算学生GPA，student可查自己，admin可查任意学生
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


# 批量刷新所有学生GPA接口，仅admin可调用
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