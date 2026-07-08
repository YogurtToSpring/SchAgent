from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

router = APIRouter(prefix="/api")

DATABASE = os.getenv("DATABASE_URL", "class.db")

def get_conn():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS class(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            master_id TEXT NOT NULL,
            capacity INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

class AddClass(BaseModel):
    class_id: str
    name: str
    master_id: str
    capacity: int

class ModClass(BaseModel):
    name: str
    master_id: str
    capacity: int

@router.post("/class/add")
def add_class(class_data: AddClass):
    conn = get_conn()
    cls = conn.execute(
        "SELECT * FROM class WHERE class_id = ?", (class_data.class_id,)
    ).fetchone()

    if cls:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Class {class_data.class_id} had existed")

    conn.execute(
        "INSERT INTO class (class_id, name, master_id, capacity) VALUES (?, ?, ?, ?)",
        (class_data.class_id, class_data.name, class_data.master_id, class_data.capacity)
    )

    conn.commit()
    conn.close()

    return {"message": f"Class {class_data.class_id} added successfully"}

@router.patch("/class/{class_id}/info")
def change_info(class_id: str, newinfo: ModClass):
    conn = get_conn()
    cls = conn.execute(
        "SELECT * FROM class WHERE class_id = ?", (class_id,)
    ).fetchone()

    if not cls:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Class {class_id} does not exist")    

    conn.execute(
        """UPDATE class SET name = ?, master_id = ?, capacity = ? WHERE class_id = ?""",
        (newinfo.name, newinfo.master_id, newinfo.capacity, class_id)
    )
    conn.commit()
    conn.close()

    return {"message": f"Class {class_id} had been modified successfully"}

@router.delete("/class/delete")
def delete_class(class_id: str):
    conn = get_conn()

    rows = conn.execute(
        "SELECT * FROM class WHERE class_id = ?", (class_id,)
    ).fetchone()

    if not rows:
        conn.close()
        raise HTTPException(status_code=404, detail="Class Not Found 404")

    conn.execute(
        "DELETE FROM class WHERE class_id = ?", (class_id,)
    )

    conn.commit()
    conn.close()

    return {"mesasge": "Class deleted successfully"}

@router.get("/class")
def list_all():
    conn = get_conn()
    
    rows = conn.execute(
        "SELECT * FROM class ORDER BY class_id",
    ).fetchall()

    conn.close()
    return {"Classes": [dict(row) for row in rows], "count": len(rows)}

@router.get("/class/info")
def get_class_info_by_name(cls_name: str):
    conn = get_conn()

    rows = conn.execute(
        "SELECT * FROM class WHERE name = ?", (cls_name,)
    ).fetchone()

    conn1 = sqlite3.connect("teacher.db")
    conn1.row_factory = sqlite3.Row

    if not rows:
        conn.close()
        raise HTTPException(status_code=404, detail="Class Not Found")
    
    teacher = conn1.execute(
        "SELECT * FROM teacher WHERE Number = ?", (rows["master_id"],)
    ).fetchone()

    if not teacher:
        conn.close()
        conn1.close()
        raise HTTPException(status_code=404, detail="Teacher Not Found")

    conn.close()
    conn1.close()

    return {"message": f"Class {cls_name} info: [name: {cls_name}, id: {rows['class_id']}, master_id: {teacher['Number']}, master_name: {teacher['Name']}]"}

app.include_router(router)