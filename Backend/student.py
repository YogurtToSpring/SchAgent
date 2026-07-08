from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import sqlite3
from passlib.hash import pbkdf2_sha256
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

router = APIRouter(prefix="/api")

DATABASE = os.getenv("DATABASE_URL", "students.db")

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            StuNum TEXT UNIQUE NOT NULL,
            Cls TEXT,
            password_hash TEXT NOT NULL
        )
    """)
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

# 注册端口在演示时封死，仅在我们内部开发人员填充数据库时调用
# 可以暴露给admin，让admin手动注册
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

# 此登陆端口对student开放，传入学号和密码
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
    return {"message": f"Student {row["Name"]} login successfully!"}

# 此端口不对外开放，仅在内部开发人员查看数据库时调用
# 可以提供给admin作为参看
@router.get("/students")
def list_students():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, Name, Cls, StuNum FROM students").fetchall()
    conn.close()
    return {"students": [dict(row) for row in rows]}

# 此端口不对外开放，仅在内部开发人员查看数据库时调用
# 可以提供给admin作为增删改查，同register
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

# 此端口不可暴露给student和teacher，仅暴露给admin
# admin有权限修改所有学生的班级信息，此处建议加上确认提示
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

# 此修改密码端口，仅对student开放，前端使用新密码与旧密码的端口
# student_num不应该暴露给用户，在发送请求时自动导入当前登录账号的student_num（学号）
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

app.include_router(router)
