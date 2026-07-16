from fastapi import FastAPI, HTTPException, APIRouter, Query
from pydantic import BaseModel, Field
import sqlite3
import os
from datetime import datetime, date
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

router = APIRouter(prefix="/api")

DATABASE = os.getenv("TODO_DB", "todo.db")


def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS todo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.commit()
    conn.close()


init_db()

class TodoCreate(BaseModel):
    user_id: str = Field(..., description="用户ID（学号/工号）")
    title: str = Field(..., description="待办标题")
    description: Optional[str] = Field("", description="待办描述")
    date: str = Field(..., description="待办日期，格式 YYYY-MM-DD")
    priority: Optional[str] = Field("medium", description="优先级: low / medium / high")


class TodoUpdate(BaseModel):
    title: Optional[str] = Field(None, description="待办标题")
    description: Optional[str] = Field(None, description="待办描述")
    date: Optional[str] = Field(None, description="待办日期，格式 YYYY-MM-DD")
    priority: Optional[str] = Field(None, description="优先级: low / medium / high")


class TodoStatusUpdate(BaseModel):
    status: str = Field(..., description="待办状态: pending / in_progress / completed")


class BatchStatusUpdate(BaseModel):
    todo_ids: List[int] = Field(..., description="待办ID列表")
    status: str = Field(..., description="目标状态: pending / in_progress / completed")

def _validate_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _validate_status(status: str) -> bool:
    return status in ("pending", "in_progress", "completed")


def _validate_priority(priority: str) -> bool:
    return priority in ("low", "medium", "high")


def _row_to_dict(row: sqlite3.Row) -> dict:
    """将 sqlite3.Row 转为字典"""
    return dict(row)

@router.post("/todo/add")
def add_todo(todo_data: TodoCreate):
    if not todo_data.title.strip():
        raise HTTPException(status_code=400, detail="待办标题不能为空")

    if not _validate_date(todo_data.date):
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    if not _validate_priority(todo_data.priority):
        raise HTTPException(status_code=400, detail="优先级值无效，应为 low / medium / high")

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute(
        """INSERT INTO todo (user_id, title, description, date, status, priority)
           VALUES (?, ?, ?, ?, 'pending', ?)""",
        (todo_data.user_id, todo_data.title.strip(), (todo_data.description or "").strip(),
         todo_data.date, todo_data.priority)
    )
    todo_id = cursor.lastrowid
    conn.commit()

    row = conn.execute("SELECT * FROM todo WHERE id = ?", (todo_id,)).fetchone()
    conn.close()

    return {"message": "待办添加成功", "todo": _row_to_dict(row)}


@router.delete("/todo/delete")
def delete_todo(todo_id: int = Query(..., description="待办ID")):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    row = conn.execute("SELECT * FROM todo WHERE id = ?", (todo_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"待办 {todo_id} 不存在")

    conn.execute("DELETE FROM todo WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()

    return {"message": f"待办 {todo_id} 已删除", "deleted": _row_to_dict(row)}


@router.get("/todo/date/{query_date}")
def get_todos_by_date(query_date: str, user_id: Optional[str] = Query(None, description="可选，按用户过滤")):
    if not _validate_date(query_date):
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    if user_id:
        rows = conn.execute(
            "SELECT * FROM todo WHERE date = ? AND user_id = ? ORDER BY priority DESC, created_at ASC",
            (query_date, user_id)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM todo WHERE date = ? ORDER BY priority DESC, created_at ASC",
            (query_date,)
        ).fetchall()

    conn.close()

    return {
        "date": query_date,
        "user_id": user_id,
        "todos": [_row_to_dict(r) for r in rows],
        "count": len(rows)
    }


@router.get("/todo/user/{user_id}")
def get_todos_by_user(
    user_id: str,
    status: Optional[str] = Query(None, description="可选，按状态过滤: pending / in_progress / completed"),
    date_from: Optional[str] = Query(None, description="可选，起始日期 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="可选，结束日期 YYYY-MM-DD"),
):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM todo WHERE user_id = ?"
    params = [user_id]

    if status:
        if not _validate_status(status):
            conn.close()
            raise HTTPException(status_code=400, detail="状态值无效，应为 pending / in_progress / completed")
        query += " AND status = ?"
        params.append(status)

    if date_from:
        if not _validate_date(date_from):
            conn.close()
            raise HTTPException(status_code=400, detail="起始日期格式错误，应为 YYYY-MM-DD")
        query += " AND date >= ?"
        params.append(date_from)

    if date_to:
        if not _validate_date(date_to):
            conn.close()
            raise HTTPException(status_code=400, detail="结束日期格式错误，应为 YYYY-MM-DD")
        query += " AND date <= ?"
        params.append(date_to)

    query += " ORDER BY date ASC, priority DESC, created_at ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return {
        "user_id": user_id,
        "todos": [_row_to_dict(r) for r in rows],
        "count": len(rows)
    }


@router.get("/todo/{todo_id}")
def get_todo_detail(todo_id: int):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    row = conn.execute("SELECT * FROM todo WHERE id = ?", (todo_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"待办 {todo_id} 不存在")

    return {"todo": _row_to_dict(row)}


@router.patch("/todo/{todo_id}/status")
def update_todo_status(todo_id: int, status_data: TodoStatusUpdate):
    if not _validate_status(status_data.status):
        raise HTTPException(status_code=400, detail="状态值无效，应为 pending / in_progress / completed")

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    row = conn.execute("SELECT * FROM todo WHERE id = ?", (todo_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"待办 {todo_id} 不存在")

    conn.execute(
        "UPDATE todo SET status = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
        (status_data.status, todo_id)
    )
    conn.commit()

    updated = conn.execute("SELECT * FROM todo WHERE id = ?", (todo_id,)).fetchone()
    conn.close()

    return {"message": f"待办 {todo_id} 状态已更新为 {status_data.status}", "todo": _row_to_dict(updated)}


@router.patch("/todo/{todo_id}/info")
def update_todo_info(todo_id: int, todo_data: TodoUpdate):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    row = conn.execute("SELECT * FROM todo WHERE id = ?", (todo_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"待办 {todo_id} 不存在")

    updates = []
    params = []

    if todo_data.title is not None:
        if not todo_data.title.strip():
            conn.close()
            raise HTTPException(status_code=400, detail="待办标题不能为空")
        updates.append("title = ?")
        params.append(todo_data.title.strip())

    if todo_data.description is not None:
        updates.append("description = ?")
        params.append(todo_data.description.strip())

    if todo_data.date is not None:
        if not _validate_date(todo_data.date):
            conn.close()
            raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")
        updates.append("date = ?")
        params.append(todo_data.date)

    if todo_data.priority is not None:
        if not _validate_priority(todo_data.priority):
            conn.close()
            raise HTTPException(status_code=400, detail="优先级值无效，应为 low / medium / high")
        updates.append("priority = ?")
        params.append(todo_data.priority)

    if not updates:
        conn.close()
        raise HTTPException(status_code=400, detail="没有提供需要更新的字段")

    updates.append("updated_at = datetime('now', 'localtime')")
    params.append(todo_id)

    conn.execute(
        f"UPDATE todo SET {', '.join(updates)} WHERE id = ?",
        params
    )
    conn.commit()

    updated = conn.execute("SELECT * FROM todo WHERE id = ?", (todo_id,)).fetchone()
    conn.close()

    return {"message": f"待办 {todo_id} 信息已更新", "todo": _row_to_dict(updated)}


@router.get("/todo")
def list_all_todos(
    user_id: Optional[str] = Query(None, description="可选，按用户过滤"),
    status: Optional[str] = Query(None, description="可选，按状态过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量上限"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM todo WHERE 1=1"
    params = []

    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)

    if status:
        if not _validate_status(status):
            conn.close()
            raise HTTPException(status_code=400, detail="状态值无效")
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY date DESC, priority DESC, created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return {
        "todos": [_row_to_dict(r) for r in rows],
        "count": len(rows),
        "limit": limit,
        "offset": offset
    }

@router.post("/todo/batch/status")
def batch_update_status(data: BatchStatusUpdate):
    if not _validate_status(data.status):
        raise HTTPException(status_code=400, detail="状态值无效，应为 pending / in_progress / completed")

    if not data.todo_ids:
        raise HTTPException(status_code=400, detail="待办ID列表不能为空")

    todo_ids = data.todo_ids
    status = data.status

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    placeholders = ",".join("?" * len(todo_ids))
    existing = conn.execute(
        f"SELECT id FROM todo WHERE id IN ({placeholders})", todo_ids
    ).fetchall()
    existing_ids = {row["id"] for row in existing}

    not_found = [tid for tid in todo_ids if tid not in existing_ids]
    if not_found:
        conn.close()
        raise HTTPException(status_code=404, detail=f"待办 {not_found} 不存在")

    conn.execute(
        f"UPDATE todo SET status = ?, updated_at = datetime('now', 'localtime') WHERE id IN ({placeholders})",
        [status] + todo_ids
    )
    conn.commit()
    conn.close()

    return {"message": f"已将 {len(todo_ids)} 个待办状态更新为 {status}", "updated_ids": todo_ids}


@router.get("/todo/stats/{user_id}")
def get_todo_stats(user_id: str):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM todo WHERE user_id = ? GROUP BY status",
        (user_id,)
    ).fetchall()

    today = date.today().isoformat()
    today_count = conn.execute(
        "SELECT COUNT(*) FROM todo WHERE user_id = ? AND date = ?",
        (user_id, today)
    ).fetchone()[0]

    overdue_count = conn.execute(
        "SELECT COUNT(*) FROM todo WHERE user_id = ? AND date < ? AND status != 'completed'",
        (user_id, today)
    ).fetchone()[0]

    conn.close()

    stats = {"pending": 0, "in_progress": 0, "completed": 0}
    for row in rows:
        stats[row["status"]] = row["cnt"]
    stats["total"] = sum(stats.values())
    stats["today"] = today_count
    stats["overdue"] = overdue_count

    return {"user_id": user_id, "stats": stats}


app.include_router(router)
