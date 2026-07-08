from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import sqlite3
import os
from student import change_cls

app = FastAPI()

router = APIRouter(prefix="/api")

DATABASE = os.getenv("CLASSMATE_DB", "classmate.db")
STUDENTS_DB = os.getenv("STUDENTS_DB_PATH", "students.db")


def get_conn():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS classmate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id TEXT NOT NULL,
            stu_num TEXT NOT NULL UNIQUE
        );
    """)
    conn.commit()
    conn.close()

init_db()

class AddRela(BaseModel):
    class_id: str
    stu_num: str

class ChangeRela(BaseModel):
    class_id: str
    stu_num: str

@router.post("/classmate/add")
def add_func(addinfo: AddRela):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM classmate WHERE stu_num = ?", (addinfo.stu_num, )
    ).fetchone()
    if rows:
        conn.close()
        raise HTTPException(status_code=404, detail="Failure to add, already existed")
    
    stu_conn = sqlite3.connect(STUDENTS_DB)
    stu_conn.row_factory = sqlite3.Row
    stu = stu_conn.execute(
        "SELECT * FROM students WHERE StuNum = ?", (addinfo.stu_num,)
    ).fetchone()

    stu_conn.close()
    if not stu:
        conn.close()
        raise HTTPException(status_code=404, detail="Student Not Found!")

    class_conn = sqlite3.connect("classi.db")
    class_conn.row_factory = sqlite3.Row
    cls = class_conn.execute(
        "SELECT * FROM classi WHERE class_id = ?", (addinfo.class_id,)
    ).fetchone()
    class_conn.close()
    if not cls:
        conn.close()
        raise HTTPException(status_code=404, detail="Class Not Found")

    conn.execute(
        "INSERT INTO classmate (class_id, stu_num) VALUES (?, ?)", 
        (addinfo.class_id, addinfo.stu_num)
    )
    conn.commit()
    conn.close()
    return {"message": f"Add student {addinfo.stu_num} successfully"}

@router.get("/classmate/{class_id}")
def get_peer_name(cls_id: str):
    conn = get_conn()
    class_conn = sqlite3.connect("classi.db")
    class_conn.row_factory = sqlite3.Row
    cls = class_conn.execute(
        "SELECT * FROM classi WHERE class_id = ?", (cls_id,)
    ).fetchone()
    class_conn.close()
    if not cls:
        conn.close()
        raise HTTPException(status_code=404, detail="Class Not Found")
    
    rows = conn.execute(
        "SELECT * FROM classmate WHERE class_id = ?", (cls_id,)
    ).fetchall()

    if not rows:
        conn.close()
        raise HTTPException(status_code=404, detail="Class Not Found")

    stu_nums = [row["stu_num"] for row in rows]
    conn_stu = sqlite3.connect(STUDENTS_DB)
    conn_stu.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(stu_nums))
    students = conn_stu.execute(
        f"SELECT * FROM students WHERE StuNum IN ({placeholders})", stu_nums
    ).fetchall()
    student_map = {s["StuNum"]: dict(s) for s in students}
    conn_stu.close()

    conn.close()
    enriched = []
    for row in rows:
        info = student_map.get(row["stu_num"])
        if info is None:
            continue
        enriched.append({"StuNum": info["StuNum"], "Name": info["Name"]})
    return {"class_id": cls_id, "student_info": enriched, "count": len(enriched)}

@router.get("/classmate")
def list_all():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM classmate ORDER BY class_id, stu_num"
    ).fetchall()

    conn.close()
    return {"alls": [dict(row) for row in rows], "count": len(rows)}

@router.patch("/classmate/change_info")
def change_info(newinfo: ChangeRela):
    conn = get_conn()
    stu_conn = sqlite3.connect(STUDENTS_DB)
    stu_conn.row_factory = sqlite3.Row
    stu = stu_conn.execute(
        "SELECT * FROM students WHERE StuNum = ?", (newinfo.stu_num,)
    ).fetchone()

    stu_conn.close()
    if not stu:
        conn.close()
        raise HTTPException(status_code=404, detail="Student Not Found!")

    class_conn = sqlite3.connect("classi.db")
    class_conn.row_factory = sqlite3.Row
    cls = class_conn.execute(
        "SELECT * FROM classi WHERE class_id = ?", (newinfo.class_id,)
    ).fetchone()
    class_conn.close()
    if not cls:
        conn.close()
        raise HTTPException(status_code=404, detail="Class Not Found")
    
    row = conn.execute(
        "SELECT * FROM classmate WHERE stu_num = ?",
        (newinfo.stu_num,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Student ID Not Found")
    
    conn.execute(
        "UPDATE classmate SET class_id = ? WHERE stu_num = ?",
        (newinfo.class_id, newinfo.stu_num)
    )
    change_cls(newinfo.stu_num, newinfo.class_id)
    conn.commit()
    conn.close()
    return {"message": "Student Info changed successfully"}

app.include_router(router)
