from fastapi import FastAPI, HTTPException, APIRouter, Query
from pydantic import BaseModel, Field
import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

router = APIRouter(prefix="/api")

DATABASE = os.getenv("LIBRARY_DB", "library.db")

# 图书馆开放时间
LIBRARY_OPEN_TIME = "08:00"
LIBRARY_CLOSE_TIME = "22:00"

def init_db():
    """初始化图书馆数据库表并预置座位数据"""
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS library_seat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seat_id TEXT NOT NULL UNIQUE,
            area TEXT NOT NULL,
            floor INTEGER NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'available'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS library_reservation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            seat_id TEXT NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'reserved',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            cancelled_at TEXT
        )
    """)

    conn.commit()

    existing = conn.execute("SELECT COUNT(*) FROM library_seat").fetchone()[0]
    if existing == 0:
        _seed_seats(conn)

    conn.close()


def _seed_seats(conn: sqlite3.Connection):
    seats = []
    configs = [
        ("A", 1, "A区 一楼自习区"),
        ("B", 2, "B区 二楼阅览区"),
        ("C", 3, "C区 三楼电子阅览区"),
    ]
    for area, floor, desc in configs:
        for i in range(1, 61 + floor * 20):
            seat_id = f"{area}-{i:03d}"
            seats.append((seat_id, area, floor, f"{desc} {i}号座"))
    conn.executemany(
        "INSERT OR IGNORE INTO library_seat (seat_id, area, floor, description) VALUES (?, ?, ?, ?)",
        seats,
    )
    conn.commit()


init_db()



class ReserveRequest(BaseModel):
    user_id: str = Field(..., description="用户ID（学号/工号）")
    seat_id: str = Field(..., description="座位编号，如 A-001")
    date: str = Field(..., description="预约日期，格式 YYYY-MM-DD")
    start_time: str = Field(..., description="开始时间，格式 HH:MM，如 09:00")
    end_time: str = Field(..., description="结束时间，格式 HH:MM，如 12:00")


class CancelRequest(BaseModel):
    reservation_id: int = Field(..., description="预约记录ID")
    user_id: str = Field(..., description="用户ID，用于校验操作权限")


class SeatStatusOut(BaseModel):
    seat_id: str
    area: str
    floor: int
    description: str
    status: str


def _validate_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _validate_time(time_str: str) -> bool:
    try:
        t = datetime.strptime(time_str, "%H:%M").time()
        open_t = datetime.strptime(LIBRARY_OPEN_TIME, "%H:%M").time()
        close_t = datetime.strptime(LIBRARY_CLOSE_TIME, "%H:%M").time()
        return open_t <= t <= close_t
    except ValueError:
        return False


def _time_to_minutes(time_str: str) -> int:
    h, m = time_str.split(":")
    return int(h) * 60 + int(m)


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _check_time_conflict(conn: sqlite3.Connection, seat_id: str, date: str,
                         start_time: str, end_time: str,
                         exclude_reservation_id: Optional[int] = None) -> bool:
    start_min = _time_to_minutes(start_time)
    end_min = _time_to_minutes(end_time)

    query = """
        SELECT id, start_time, end_time FROM library_reservation
        WHERE seat_id = ? AND date = ? AND status = 'reserved'
    """
    params = [seat_id, date]

    rows = conn.execute(query, params).fetchall()

    for row in rows:
        if exclude_reservation_id and row["id"] == exclude_reservation_id:
            continue
        exist_start = _time_to_minutes(row["start_time"])
        exist_end = _time_to_minutes(row["end_time"])
        if not (end_min <= exist_start or start_min >= exist_end):
            return True
    return False

<<<<<<< HEAD
=======

>>>>>>> 088fcf9b914d75bb5cd6513ce43105422667c1ad
@router.post("/library/reserve")
def reserve_seat(req: ReserveRequest):
    if not _validate_date(req.date):
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    if not _validate_time(req.start_time):
        raise HTTPException(status_code=400,
                            detail=f"开始时间格式错误或不在开放时间 {LIBRARY_OPEN_TIME}-{LIBRARY_CLOSE_TIME} 内")

    if not _validate_time(req.end_time):
        raise HTTPException(status_code=400,
                            detail=f"结束时间格式错误或不在开放时间 {LIBRARY_OPEN_TIME}-{LIBRARY_CLOSE_TIME} 内")

    if _time_to_minutes(req.start_time) >= _time_to_minutes(req.end_time):
        raise HTTPException(status_code=400, detail="开始时间必须早于结束时间")

    today = date.today().isoformat()
    if req.date < today:
        raise HTTPException(status_code=400, detail="不能预约过去日期的座位")

    stu_con = sqlite3.connect("students.db")
    stu_con.row_factory = sqlite3.Row
    row1 = stu_con.execute(
        "SELECT * FROM students WHERE StuNum = ?",
        (req.user_id,)
    ).fetchone()
    stu_con.close()

    tea_con = sqlite3.connect("teacher.db")
    tea_con.row_factory = sqlite3.Row
    row2 = tea_con.execute(
        "SELECT * FROM teacher WHERE Number = ?",
        (req.user_id,)
    ).fetchone()
    tea_con.close()

    if not row1:
        if not row2:
            raise HTTPException(status_code=404, detail="User Not Found!")

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    seat = conn.execute(
        "SELECT * FROM library_seat WHERE seat_id = ?", (req.seat_id,)
    ).fetchone()
    if not seat:
        conn.close()
        raise HTTPException(status_code=404, detail=f"座位 {req.seat_id} 不存在")

    if _check_time_conflict(conn, req.seat_id, req.date, req.start_time, req.end_time):
        conn.close()
        raise HTTPException(status_code=409, detail=f"座位 {req.seat_id} 在 {req.date} {req.start_time}-{req.end_time} 已被预约")

    user_conflict = conn.execute(
        """SELECT id, seat_id, start_time, end_time FROM library_reservation
           WHERE user_id = ? AND date = ? AND status = 'reserved'""",
        (req.user_id, req.date)
    ).fetchall()
    req_start = _time_to_minutes(req.start_time)
    req_end = _time_to_minutes(req.end_time)
    for uc in user_conflict:
        uc_start = _time_to_minutes(uc["start_time"])
        uc_end = _time_to_minutes(uc["end_time"])
        if not (req_end <= uc_start or req_start >= uc_end):
            conn.close()
            raise HTTPException(
                status_code=409,
                detail=f"您在 {req.date} {uc['start_time']}-{uc['end_time']} 已预约座位 {uc['seat_id']}，时间段冲突"
            )

    cursor = conn.execute(
        """INSERT INTO library_reservation (user_id, seat_id, date, start_time, end_time, status)
           VALUES (?, ?, ?, ?, ?, 'reserved')""",
        (req.user_id, req.seat_id, req.date, req.start_time, req.end_time)
    )
    reservation_id = cursor.lastrowid

    conn.execute(
        "UPDATE library_seat SET status = 'reserved' WHERE seat_id = ?",
        (req.seat_id,)
    )

    conn.commit()

    row = conn.execute(
        "SELECT * FROM library_reservation WHERE id = ?", (reservation_id,)
    ).fetchone()
    conn.close()

    return {
        "message": "预约成功",
        "reservation": _row_to_dict(row),
    }

<<<<<<< HEAD
=======

>>>>>>> 088fcf9b914d75bb5cd6513ce43105422667c1ad
@router.post("/library/cancel")
def cancel_reservation(req: CancelRequest):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    reservation = conn.execute(
        "SELECT * FROM library_reservation WHERE id = ?", (req.reservation_id,)
    ).fetchone()

    if not reservation:
        conn.close()
        raise HTTPException(status_code=404, detail=f"预约记录 {req.reservation_id} 不存在")

    if reservation["user_id"] != req.user_id:
        conn.close()
        raise HTTPException(status_code=403, detail="无权取消他人的预约")

    if reservation["status"] == "cancelled":
        conn.close()
        raise HTTPException(status_code=400, detail="该预约已被取消，无需重复操作")

    if reservation["status"] == "completed":
        conn.close()
        raise HTTPException(status_code=400, detail="该预约已完成，无法取消")

    conn.execute(
        """UPDATE library_reservation
           SET status = 'cancelled', cancelled_at = datetime('now', 'localtime')
           WHERE id = ?""",
        (req.reservation_id,)
    )

    seat_id = reservation["seat_id"]
    still_reserved = conn.execute(
        """SELECT COUNT(*) FROM library_reservation
           WHERE seat_id = ? AND date = ? AND status = 'reserved' AND id != ?""",
        (seat_id, reservation["date"], req.reservation_id)
    ).fetchone()[0]

    if still_reserved == 0:
        conn.execute(
            "UPDATE library_seat SET status = 'available' WHERE seat_id = ?",
            (seat_id,)
        )

    conn.commit()

    updated = conn.execute(
        "SELECT * FROM library_reservation WHERE id = ?", (req.reservation_id,)
    ).fetchone()
    conn.close()

    return {
        "message": "预约已取消",
        "reservation": _row_to_dict(updated),
    }

<<<<<<< HEAD
=======

>>>>>>> 088fcf9b914d75bb5cd6513ce43105422667c1ad
@router.get("/library/user/{user_id}/history")
def get_user_history(
    user_id: str,
    status: Optional[str] = Query(None, description="按状态过滤: reserved / cancelled / completed / all"),
    date_from: Optional[str] = Query(None, description="起始日期 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=200, description="返回数量上限"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM library_reservation WHERE user_id = ?"
    params = [user_id]

    if status and status != "all":
        if status not in ("reserved", "cancelled", "completed"):
            conn.close()
            raise HTTPException(status_code=400, detail="状态值无效，应为 reserved / cancelled / completed / all")
        query += " AND status = ?"
        params.append(status)

    if date_from:
        if not _validate_date(date_from):
            conn.close()
            raise HTTPException(status_code=400, detail="起始日期格式错误")
        query += " AND date >= ?"
        params.append(date_from)

    if date_to:
        if not _validate_date(date_to):
            conn.close()
            raise HTTPException(status_code=400, detail="结束日期格式错误")
        query += " AND date <= ?"
        params.append(date_to)

    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    total = conn.execute(count_query, params).fetchone()[0]

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return {
        "user_id": user_id,
        "reservations": [_row_to_dict(r) for r in rows],
        "count": len(rows),
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/library/reservation/{reservation_id}")
def get_reservation_detail(reservation_id: int):
    """查询单条预约记录详情"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        "SELECT * FROM library_reservation WHERE id = ?", (reservation_id,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"预约记录 {reservation_id} 不存在")

    return {"reservation": _row_to_dict(row)}

@router.get("/library/seats/status")
def get_seats_status(
    area: Optional[str] = Query(None, description="按区域过滤: A / B / C"),
    floor: Optional[int] = Query(None, description="按楼层过滤: 1 / 2 / 3"),
):
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM library_seat WHERE 1=1"
    params = []

    if area:
        query += " AND area = ?"
        params.append(area)

    if floor is not None:
        query += " AND floor = ?"
        params.append(floor)

    query += " ORDER BY area, floor, seat_id"

    rows = conn.execute(query, params).fetchall()

    stats_query = "SELECT area, floor, status, COUNT(*) as cnt FROM library_seat"
    stats_params = []
    conditions = []
    if area:
        conditions.append("area = ?")
        stats_params.append(area)
    if floor is not None:
        conditions.append("floor = ?")
        stats_params.append(floor)
    if conditions:
        stats_query += " WHERE " + " AND ".join(conditions)
    stats_query += " GROUP BY area, floor, status ORDER BY area, floor"

    stats_rows = conn.execute(stats_query, stats_params).fetchall()
    conn.close()

    stats = {}
    for sr in stats_rows:
        key = f"{sr['area']}区 {sr['floor']}F"
        if key not in stats:
            stats[key] = {"available": 0, "reserved": 0, "total": 0}
        stats[key][sr["status"]] = sr["cnt"]
        stats[key]["total"] += sr["cnt"]

    return {
        "seats": [_row_to_dict(r) for r in rows],
        "count": len(rows),
        "stats": stats,
    }


@router.get("/library/seats/available")
def get_available_seats(
    date: str = Query(..., description="查询日期 YYYY-MM-DD"),
    start_time: str = Query(..., description="开始时间 HH:MM"),
    end_time: str = Query(..., description="结束时间 HH:MM"),
    area: Optional[str] = Query(None, description="按区域过滤"),
):
    
    if not _validate_date(date):
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    if not _validate_time(start_time) or not _validate_time(end_time):
        raise HTTPException(status_code=400, detail="时间格式错误或不在开放时间内")

    if _time_to_minutes(start_time) >= _time_to_minutes(end_time):
        raise HTTPException(status_code=400, detail="开始时间必须早于结束时间")

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    req_start = _time_to_minutes(start_time)
    req_end = _time_to_minutes(end_time)

    reserved_rows = conn.execute(
        "SELECT seat_id, start_time, end_time FROM library_reservation WHERE date = ? AND status = 'reserved'",
        (date,)
    ).fetchall()

    conflict_seats = set()
    for r in reserved_rows:
        r_start = _time_to_minutes(r["start_time"])
        r_end = _time_to_minutes(r["end_time"])
        if not (req_end <= r_start or req_start >= r_end):
            conflict_seats.add(r["seat_id"])

    seat_query = "SELECT * FROM library_seat WHERE 1=1"
    params = []
    if area:
        seat_query += " AND area = ?"
        params.append(area)

    seat_query += " ORDER BY area, floor, seat_id"
    all_seats = conn.execute(seat_query, params).fetchall()
    conn.close()

    available = []
    unavailable = []
    for seat in all_seats:
        sd = _row_to_dict(seat)
        if seat["seat_id"] in conflict_seats:
            sd["available"] = False
            unavailable.append(sd)
        else:
            sd["available"] = True
            available.append(sd)

    return {
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "available_seats": available,
        "available_count": len(available),
        "unavailable_seats": unavailable,
        "unavailable_count": len(unavailable),
    }

@router.post("/library/refresh")
def refresh_completed_reservations():
    """
    刷新预约状态：将已过期的预约自动标记为 completed
    ---
    供前端定时调用或管理员手动触发。
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    now_time = now.strftime("%H:%M")

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    updated_today = conn.execute(
        """UPDATE library_reservation
           SET status = 'completed'
           WHERE status = 'reserved' AND date = ? AND end_time <= ?""",
        (today_str, now_time)
    ).rowcount

    updated_past = conn.execute(
        """UPDATE library_reservation
           SET status = 'completed'
           WHERE status = 'reserved' AND date < ?""",
        (today_str,)
    ).rowcount

    completed_seats = conn.execute(
        """SELECT DISTINCT seat_id, date FROM library_reservation
           WHERE status = 'completed'"""
    ).fetchall()

    for cs in completed_seats:
        still_reserved = conn.execute(
            """SELECT COUNT(*) FROM library_reservation
               WHERE seat_id = ? AND date = ? AND status = 'reserved'""",
            (cs["seat_id"], cs["date"])
        ).fetchone()[0]
        if still_reserved == 0:
            conn.execute(
                "UPDATE library_seat SET status = 'available' WHERE seat_id = ?",
                (cs["seat_id"],)
            )

    conn.commit()
    conn.close()

    return {
        "message": "预约状态已刷新",
        "completed_today": updated_today,
        "completed_past": updated_past,
    }


app.include_router(router)
