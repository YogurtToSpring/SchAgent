from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

router = APIRouter(prefix="/api")

DATABASE = os.getenv("DATABASE_URL", "classi.db")

def get_conn():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS classi(
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

# 添加端口在演示时封死，仅在我们内部开发人员填充数据库时调用
# 仅管理员admin可添加，teacher可以向admin发出请求（此处实现可能较复杂--关于通信处理）
@router.post("/classi/add")
def add_class(class_data: AddClass):
    conn = get_conn()
    cls = conn.execute(
        "SELECT * FROM classi WHERE class_id = ?", (class_data.class_id,)
    ).fetchone()

    if cls:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Class {class_data.class_id} had existed")

    conn.execute(
        "INSERT INTO classi (class_id, name, master_id, capacity) VALUES (?, ?, ?, ?)",
        (class_data.class_id, class_data.name, class_data.master_id, class_data.capacity)
    )

    conn.commit()
    conn.close()

    return {"message": f"Class {class_data.class_id} added successfully"}

# 仅admin可修改班级信息，班级编号时不可变的，但名字可以变，班主任可以变（用编号映射改变），容量可以变（人数）
@router.patch("/classi/{class_id}/info")
def change_info(class_id: str, newinfo: ModClass):
    conn = get_conn()
    cls = conn.execute(
        "SELECT * FROM classi WHERE class_id = ?", (class_id,)
    ).fetchone()

    if not cls:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Class {class_id} does not exist")    

    tea_conn = sqlite3.connect("teacher.db")
    tea_conn.row_factory = sqlite3.Row
    teach = tea_conn.execute(
        "SELECT * FROM teacher WHERE Number = ?", (newinfo.master_id,)
    ).fetchone()
    tea_conn.close()
    if not teach:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Teacher {newinfo.master_id} Not Found")

    conn.execute(
        """UPDATE classi SET name = ?, master_id = ?, capacity = ? WHERE class_id = ?""",
        (newinfo.name, newinfo.master_id, newinfo.capacity, class_id)
    )
    conn.commit()
    conn.close()

    return {"message": f"Class {class_id} had been modified successfully"}

# 仅admin可删除班级（例如毕业班）
@router.delete("/classi/delete")
def delete_class(class_id: str):
    conn = get_conn()

    rows = conn.execute(
        "SELECT * FROM classi WHERE class_id = ?", (class_id,)
    ).fetchone()

    if not rows:
        conn.close()
        raise HTTPException(status_code=404, detail="Class Not Found 404")

    conn.execute(
        "DELETE FROM classi WHERE class_id = ?", (class_id,)
    )

    conn.commit()
    conn.close()

    return {"message": "Class deleted successfully"}

# 用于查看班级，用于数据库调试
# admin可查看
@router.get("/classi")
def list_all():
    conn = get_conn()
    
    rows = conn.execute(
        "SELECT * FROM classi ORDER BY class_id",
    ).fetchall()

    conn.close()
    return {"Classes": [dict(row) for row in rows], "count": len(rows)}

# 通过给出班级的名字，查询班级的所有信息
# student和teacher不用查询按钮接口，直接能看自己班级的信息
# admin需要查询接口，能看所有信息
@router.get("/classi/info")
def get_class_info_by_name(cls_name: str):
    conn = get_conn()

    rows = conn.execute(
        "SELECT * FROM classi WHERE name = ?", (cls_name,)
    ).fetchone()

    conn1 = sqlite3.connect("teacher.db")
    conn1.row_factory = sqlite3.Row

    if not rows:
        conn.close()
        conn1.close()
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