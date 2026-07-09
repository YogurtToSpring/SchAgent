"""
图书馆座位管理 (Library Seat Management) 数据库接口
==================================================
提供座位预约、取消预约、历史记录查询、座位状态查询等功能。

数据表:
    library_seat        — 座位列表（初始化时预置，不对外提供管理接口）
    library_reservation — 预约记录（含预约和取消记录）

接口前缀: /api
启动方式: 由 main.py 自动加载注册
"""
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


# ==================== 数据库初始化 ====================

def init_db():
    """初始化图书馆数据库表并预置座位数据"""
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON")

    # 座位表
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

    # 预约记录表
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

    # 预置座位（仅在表为空时插入）
    existing = conn.execute("SELECT COUNT(*) FROM library_seat").fetchone()[0]
    if existing == 0:
        _seed_seats(conn)

    conn.close()


def _seed_seats(conn: sqlite3.Connection):
    """预置图书馆座位数据：A区1F / B区2F / C区3F，各20个座位"""
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


# ==================== Pydantic 模型 ====================

class ReserveRequest(BaseModel):
    """预约座位请求"""
    user_id: str = Field(..., description="用户ID（学号/工号）")
    seat_id: str = Field(..., description="座位编号，如 A-001")
    date: str = Field(..., description="预约日期，格式 YYYY-MM-DD")
    start_time: str = Field(..., description="开始时间，格式 HH:MM，如 09:00")
    end_time: str = Field(..., description="结束时间，格式 HH:MM，如 12:00")


class CancelRequest(BaseModel):
    """取消预约请求"""
    reservation_id: int = Field(..., description="预约记录ID")
    user_id: str = Field(..., description="用户ID，用于校验操作权限")


class SeatStatusOut(BaseModel):
    """座位状态输出（用于响应模型，实际以 dict 返回）"""
    seat_id: str
    area: str
    floor: int
    description: str
    status: str


# ==================== 辅助函数 ====================

def _validate_date(date_str: str) -> bool:
    """校验日期格式 YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _validate_time(time_str: str) -> bool:
    """校验时间格式 HH:MM，且在图书馆开放时间内"""
    try:
        t = datetime.strptime(time_str, "%H:%M").time()
        open_t = datetime.strptime(LIBRARY_OPEN_TIME, "%H:%M").time()
        close_t = datetime.strptime(LIBRARY_CLOSE_TIME, "%H:%M").time()
        return open_t <= t <= close_t
    except ValueError:
        return False


def _time_to_minutes(time_str: str) -> int:
    """将 HH:MM 转为分钟数，方便比较"""
    h, m = time_str.split(":")
    return int(h) * 60 + int(m)


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _check_time_conflict(conn: sqlite3.Connection, seat_id: str, date: str,
                         start_time: str, end_time: str,
                         exclude_reservation_id: Optional[int] = None) -> bool:
    """
    检查指定座位的指定时间段是否与已有预约冲突。
    返回 True 表示有冲突，False 表示无冲突。
    """
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
        # 时间段重叠判断：非 (A结束 <= B开始 或 B结束 <= A开始)
        if not (end_min <= exist_start or start_min >= exist_end):
            return True
    return False


# ==================== 预约接口 ====================

@router.post("/library/reserve")
def reserve_seat(req: ReserveRequest):
    """
    预约座位
    ---
    选择一个座位和时间段进行预约。系统会检查：
    1. 座位是否存在
    2. 时间段是否合法（日期格式、时间格式、时间先后、在开放时间内）
    3. 时间段是否与已有预约冲突
    预约成功后记录预约用户、座位、时间段等信息。
    """
    # 参数校验
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

    # 不能预约过去的日期
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

    # 检查座位是否存在
    seat = conn.execute(
        "SELECT * FROM library_seat WHERE seat_id = ?", (req.seat_id,)
    ).fetchone()
    if not seat:
        conn.close()
        raise HTTPException(status_code=404, detail=f"座位 {req.seat_id} 不存在")

    # 检查时间冲突
    if _check_time_conflict(conn, req.seat_id, req.date, req.start_time, req.end_time):
        conn.close()
        raise HTTPException(status_code=409, detail=f"座位 {req.seat_id} 在 {req.date} {req.start_time}-{req.end_time} 已被预约")

    # 同一用户在同一时间段不能预约多个座位
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

    # 创建预约
    cursor = conn.execute(
        """INSERT INTO library_reservation (user_id, seat_id, date, start_time, end_time, status)
           VALUES (?, ?, ?, ?, ?, 'reserved')""",
        (req.user_id, req.seat_id, req.date, req.start_time, req.end_time)
    )
    reservation_id = cursor.lastrowid

    # 更新座位状态
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


# ==================== 取消预约接口 ====================

@router.post("/library/cancel")
def cancel_reservation(req: CancelRequest):
    """
    取消预约
    ---
    取消指定预约记录，释放座位。
    需要提供预约记录ID和用户ID以校验操作权限。
    取消后会保留记录，状态标记为 cancelled，并记录取消时间。
    """
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

    # 更新预约状态
    conn.execute(
        """UPDATE library_reservation
           SET status = 'cancelled', cancelled_at = datetime('now', 'localtime')
           WHERE id = ?""",
        (req.reservation_id,)
    )

    # 释放座位：检查该座位在当天是否还有其他有效预约
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


# ==================== 历史记录查询 ====================

@router.get("/library/user/{user_id}/history")
def get_user_history(
    user_id: str,
    status: Optional[str] = Query(None, description="按状态过滤: reserved / cancelled / completed / all"),
    date_from: Optional[str] = Query(None, description="起始日期 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=200, description="返回数量上限"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    查询用户历史预约记录
    ---
    返回指定用户的所有预约记录（含预约成功和已取消的记录）。
    支持按状态、日期范围过滤和分页。
    按创建时间倒序排列，最近的在前。
    """
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

    # 获取总数
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


# ==================== 座位状态查询 ====================

@router.get("/library/seats/status")
def get_seats_status(
    area: Optional[str] = Query(None, description="按区域过滤: A / B / C"),
    floor: Optional[int] = Query(None, description="按楼层过滤: 1 / 2 / 3"),
):
    """
    查询当前各个座位状态
    ---
    返回所有座位的基本信息与当前状态（available / reserved）。
    可按区域或楼层过滤。
    同时汇总统计各区域/各状态的座位数量。
    """
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

    # 统计
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

    # 组装统计信息
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
    """
    查询指定时间段内的可用座位
    ---
    返回在指定日期和时间段内未被预约的座位列表。
    适用于用户选择时间后查看有哪些座位可选。
    """
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

    # 查出该日期所有有效预约
    reserved_rows = conn.execute(
        "SELECT seat_id, start_time, end_time FROM library_reservation WHERE date = ? AND status = 'reserved'",
        (date,)
    ).fetchall()

    # 找出冲突的座位
    conflict_seats = set()
    for r in reserved_rows:
        r_start = _time_to_minutes(r["start_time"])
        r_end = _time_to_minutes(r["end_time"])
        if not (req_end <= r_start or req_start >= r_end):
            conflict_seats.add(r["seat_id"])

    # 查询座位
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


# ==================== 管理员补充接口（自动完成过期预约） ====================

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

    # 将今天已经结束的预约标记为 completed
    updated_today = conn.execute(
        """UPDATE library_reservation
           SET status = 'completed'
           WHERE status = 'reserved' AND date = ? AND end_time <= ?""",
        (today_str, now_time)
    ).rowcount

    # 将过去日期的预约标记为 completed
    updated_past = conn.execute(
        """UPDATE library_reservation
           SET status = 'completed'
           WHERE status = 'reserved' AND date < ?""",
        (today_str,)
    ).rowcount

    # 释放已完成预约对应的座位（如果该座位当天无其他有效预约）
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
