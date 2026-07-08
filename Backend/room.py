"""
    declaration: Tips for room database
        This so-called room could be made just as "智慧珞珈".
        Room includes area, building, room_id, which synthetically integrates into so-called "3区1教301"
        To store in another way, we use this format "area-building-room_id", which can be interpreted as "3-1-301", same as "3区1教301"
        And this way of storage will be used in course module.
"""

from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

router = APIRouter(prefix="/api")

DATABASE = os.getenv("DATABASE_URL", "room.db")

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS room(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area TEXT NOT NULL,
            building TEXT NOT NULL,
            room_id TEXT NOT NULL,
            capacity TEXT NOT NULL,
            UNIQUE(area, building, room_id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

class roomReg(BaseModel):
    area: str
    building: str
    room_id: str
    capacity: str

# 不提供接口，仅填充数据库时使用
@router.post("/room/add")
def addroom(room_data: roomReg):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    room = conn.execute("SELECT * FROM room WHERE room_id = ?", (room_data.room_id,)).fetchone()
    if room:
        room_all = room["area"] + room["building"] + room["room_id"]
        new_room = room_data.area + room_data.building + room_data.room_id
        if room_all == new_room:
            conn.close()
            raise HTTPException(status_code=400, detail="Room has existed")
    
    conn.execute(
        "INSERT INTO room (area, building, room_id, capacity) VALUES (?, ?, ?, ?)",
        (room_data.area, room_data.building, room_data.room_id, room_data.capacity)
    )
    conn.commit()
    conn.close()

    return {"message": f"Room {room_data.area}区{room_data.building}教{room_data.room_id} added successfully"}

# 提供给所有人这个接口，让所有用户都可以查看教室
@router.get("/room")
def list_rooms():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, area, building, room_id FROM room").fetchall()
    conn.close()
    rooms = [dict(row) for row in rows]
    for r in rooms:
        r["room_full"] = f"{r["area"]}-{r["building"]}-{r["room_id"]}"
    return {"rooms": rooms}

app.include_router(router)

def seed_trial():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    data = [
        ("3", "1", "209", "60"),
        ("3", "1", "415", "90"),
        ("3", "1", "512", "40"),
        ("3", "1", "709", "100"),
        ("3", "2", "402", "60"),
        ("3", "2", "108", "40"),
        ("3", "3", "301", "90"),
        ("3", "3", "201", "80"),
        ("1", "5", "107", "40"),
        ("1", "6", "103", "45"),
    ]

    for ar, bu, rid, cap in data:
        conn.execute(
            "INSERT INTO room (area, building, room_id, capacity) VALUES (?, ?, ?, ?)",
            (ar, bu, rid, cap)
        )
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    seed_trial()
