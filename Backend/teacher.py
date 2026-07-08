from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import sqlite3
from passlib.hash import pbkdf2_sha256
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

router = APIRouter(prefix="/api")

DATABASE = os.getenv("DATABASE_URL", "teacher.db")

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS teacher (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Number TEXT UNIQUE NOT NULL,
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

class TeacherRegister(BaseModel):
    Name: str
    Number: str
    password: str

class TeacherLogin(BaseModel):
    Number: str
    password: str

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

# 注册端口在演示时封死，仅在我们内部开发人员填充数据库时调用
# 可以暴露给admin，让admin手动注册
@router.post("/teacher/register")
def register(teacher_data: TeacherRegister):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    existing = conn.execute("SELECT id FROM teacher WHERE Number = ?", (teacher_data.Number,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Hey bro, you have just got your account")
    
    hashed = hash_password(teacher_data.password)
    conn.execute(
        "INSERT INTO teacher (Name, Number, password_hash) VALUES (?, ?, ?)",
        (teacher_data.Name, teacher_data.Number, hashed)
    )
    conn.commit()
    conn.close()
    
    return {"message": f"Teacher {teacher_data.Name} registered successfully!"}

# 此登陆端口对teacher开放，传入工号和密码
@router.post("/teacher/login")
def login(teacher_data: TeacherLogin):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM teacher WHERE Number = ?", (teacher_data.Number,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Login Failure")
    if not verify_password(teacher_data.password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=404, detail="Permmission Denied. Authentification Failure")
    conn.close()
    return {"message": f"Teacher {row["Name"]} login successfully!"}

# 此端口不对外开放，仅在内部开发人员查看数据库时调用
# 可以提供给admin作为参看
@router.get("/teacher")
def list_teacher():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, Name, Number FROM teacher").fetchall()
    conn.close()
    return {"teacher": [dict(row) for row in rows]}

# 此端口不对外开放，仅在内部开发人员查看数据库时调用
# 可以提供给admin作为增删改查，同register
@router.delete("/teacher/delete")
def delete_teacher(teacher_num: str):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM teacher WHERE Number = ?", (teacher_num,)).fetchone()
    if not rows:
        conn.close()
        raise HTTPException(status_code=404, detail="Teacher does not exist")
    conn.execute(
        "DELETE FROM teacher WHERE Number = ?", (teacher_num,)
    )

    conn.commit()
    conn.close()    
    return {"message": f"teacher {teacher_num} deleted successfully"}

# 此修改密码端口，仅对teacher开放，前端使用新密码与旧密码的端口
# teacher_num不应该暴露给用户，在发送请求时自动导入当前登录账号的teacher_num（工号）
@router.put("/teacher/{teacher_num}/password")
def change_password(teacher_num: str, password_data: PasswordChange):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    teacher = conn.execute("SELECT * FROM teacher WHERE Number = ?", (teacher_num,)).fetchone()
    if not teacher:
        conn.close()
        raise HTTPException(status_code=404, detail="Teacher does not exist")
    
    if not verify_password(password_data.old_password, teacher["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="Wrong password")
    
    if password_data.new_password == password_data.old_password:
        conn.close()
        raise HTTPException(status_code=400, detail="New password should not be the same with the old one!")
    
    new_hashed = hash_password(password_data.new_password)
    conn.execute(
        "UPDATE teacher SET password_hash = ? WHERE Number = ?",
        (new_hashed, teacher_num)
    )
    conn.commit()
    conn.close()
    
    return {"message": "Password modified successfully"}

app.include_router(router)
