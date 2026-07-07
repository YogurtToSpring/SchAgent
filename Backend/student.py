from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from passlib.hash import pbkdf2_sha256
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

app = FastAPI()

DATABASE = os.getenv("DATABASE_URL", "students.db")

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            StuNum TEXT UNIQUE NOT NULL,
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
    password: str

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

# ================== 注册新学生 ==================
@app.post("/register")
def register(student_data: StudentRegister):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    # 检查学号是否已被注册
    existing = conn.execute("SELECT id FROM students WHERE StuNum = ?", (student_data.StuNum,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Hey bro, you have just got your account")
    
    # 加密密码并存入数据库
    hashed = hash_password(student_data.password)
    conn.execute(
        "INSERT INTO students (Name, StuNum, password_hash) VALUES (?, ?, ?)",
        (student_data.Name, student_data.StuNum, hashed)
    )
    conn.commit()
    conn.close()
    
    return {"message": f"Student {student_data.Name} registered successfully!"}

# ================== 查看所有学生（网址改成 /students） ==================
@app.get("/students")
def list_students():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, Name, StuNum FROM students").fetchall()
    conn.close()
    return {"students": [dict(row) for row in rows]}

# ================== 修改学生密码（网址改成 /students/{student_id}/password） ==================
@app.put("/students/{student_id}/password")
def change_password(student_id: int, password_data: PasswordChange):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    # 查询该学生
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        conn.close()
        raise HTTPException(status_code=404, detail="student does not exist")
    
    # 验证旧密码
    if not verify_password(password_data.old_password, student["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="password wrong!!!")
    
    # 更新为新密码（加密后存储）
    new_hashed = hash_password(password_data.new_password)

    if password_data.new_password == password_data.old_password:
        conn.close()
        raise HTTPException(status_code=400, detail="New password should not be the same with the old one!")
    
    conn.execute(
        "UPDATE students SET password_hash = ? WHERE id = ?",
        (new_hashed, student_id)
    )
    conn.commit()
    conn.close()
    
    return {"message": "密码修改成功（已永久写入数据库）！"}
