from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import sqlite3
from passlib.hash import pbkdf2_sha256
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

router = APIRouter(prefix="/api")

DATABASE = os.getenv("DATABASE_URL", "admin.db")

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin (
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

class AdminRegister(BaseModel):
    Name: str
    Number: str
    password: str

class AdminLogin(BaseModel):
    Number: str
    password: str

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

@router.post("/admin/register")
def register(admin_data: AdminRegister):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    existing = conn.execute("SELECT id FROM admin WHERE Number = ?", (admin_data.Number,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Hey bro, you have just got your account")
    
    hashed = hash_password(admin_data.password)
    conn.execute(
        "INSERT INTO admin (Name, Number, password_hash) VALUES (?, ?, ?)",
        (admin_data.Name, admin_data.Number, hashed)
    )
    conn.commit()
    conn.close()
    
    return {"message": f"Admin {admin_data.Name} registered successfully!"}

@router.post("/admin/login")
def login(admin_data: AdminLogin):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM admin WHERE Number = ?", (admin_data.Number,)
    ).fetchone()
    if not verify_password(admin_data.password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=404, detail="Permmission Denied. Authentification Failure")
    conn.close()
    return {"message": f"Admin {row["Name"]} login successfully!"}


@router.get("/admin")
def list_admin():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, Name, Number FROM admin").fetchall()
    conn.close()
    return {"admin": [dict(row) for row in rows]}

@router.put("/admin/{admin_id}/password")
def change_password(admin_id: int, password_data: PasswordChange):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    admin = conn.execute("SELECT * FROM admin WHERE id = ?", (admin_id,)).fetchone()
    if not admin:
        conn.close()
        raise HTTPException(status_code=404, detail="Admin does not exist")
    
    if not verify_password(password_data.old_password, admin["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="Wrong password")
    
    if password_data.new_password == password_data.old_password:
        conn.close()
        raise HTTPException(status_code=400, detail="New password should not be the same with the old one!")
    
    new_hashed = hash_password(password_data.new_password)
    conn.execute(
        "UPDATE admin SET password_hash = ? WHERE id = ?",
        (new_hashed, admin_id)
    )
    conn.commit()
    conn.close()
    
    return {"message": "Password modified successfully"}

app.include_router(router)
