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

@router.post("/students/login")
def login(student_data: StudentLogin):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM students WHERE StuNum = ?", (student_data.StuNum,)
    ).fetchone()
    if not verify_password(student_data.password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=404, detail="Permmission Denied. Authentification Failure")
    conn.close()
    return {"message": f"Student {row["Name"]} login successfully!"}

@router.get("/students")
def list_students():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, Name, Cls, StuNum FROM students").fetchall()
    conn.close()
    return {"students": [dict(row) for row in rows]}

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


@router.patch("/students/{student_id}/Cls")
def change_cls(student_id: int, newcls: str):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        conn.close()
        raise HTTPException(status_code=404, detail="Student does not exist")
    if student["Cls"] == newcls:
        conn.close()
        raise HTTPException(status_code=400, detail="Class number had not been changed")
    
    conn.execute(
        "UPDATE students SET Cls = ? WHERE id = ?",
        (newcls, student_id)
    )
    conn.commit()
    conn.close()

    return {"message": "class changed successfully"}

@router.put("/students/{student_id}/password")
def change_password(student_id: int, password_data: PasswordChange):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
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
        "UPDATE students SET password_hash = ? WHERE id = ?",
        (new_hashed, student_id)
    )
    conn.commit()
    conn.close()
    
    return {"message": "Password modified successfully"}

app.include_router(router)
