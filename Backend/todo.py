"""
待办管理 (Todo Management) 数据库接口
=====================================
提供待办的增删改查及状态管理功能，向前端和 LangChain Agent 提供服务。

数据表: todo (SQLite)
接口前缀: /api

启动方式: 由 main.py 自动加载注册
"""
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
    """初始化待办数据库表"""
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


# ==================== Pydantic 模型 ====================

class TodoCreate(BaseModel):
    """创建待办请求体"""
    user_id: str = Field(..., description="用户ID（学号/工号）")
    title: str = Field(..., description="待办标题")
    description: Optional[str] = Field("", description="待办描述")
    date: str = Field(..., description="待办日期，格式 YYYY-MM-DD")
    priority: Optional[str] = Field("medium", description="优先级: low / medium / high")


class TodoUpdate(BaseModel):
    """更新待办请求体"""
    title: Optional[str] = Field(None, description="待办标题")
    description: Optional[str] = Field(None, description="待办描述")
    date: Optional[str] = Field(None, description="待办日期，格式 YYYY-MM-DD")
    priority: Optional[str] = Field(None, description="优先级: low / medium / high")


class TodoStatusUpdate(BaseModel):
    """更新待办状态请求体"""
    status: str = Field(..., description="待办状态: pending / in_progress / completed")


class BatchStatusUpdate(BaseModel):
    """批量更新待办状态请求体"""
    todo_ids: List[int] = Field(..., description="待办ID列表")
    status: str = Field(..., description="目标状态: pending / in_progress / completed")


# ==================== 辅助函数 ====================

def _validate_date(date_str: str) -> bool:
    """校验日期格式 YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _validate_status(status: str) -> bool:
    """校验状态值"""
    return status in ("pending", "in_progress", "completed")


def _validate_priority(priority: str) -> bool:
    """校验优先级值"""
    return priority in ("low", "medium", "high")


def _row_to_dict(row: sqlite3.Row) -> dict:
    """将 sqlite3.Row 转为字典"""
    return dict(row)


# ==================== 待办接口 ====================

@router.post("/todo/add")
def add_todo(todo_data: TodoCreate):
    """
    添加待办事项
    ---
    前端调用: 用户在待办页面新建待办
    LangChain Agent 调用: 通过工具函数 add_todo(user_id, title, date, ...) 添加
    """
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
    """
    删除待办事项
    ---
    前端调用: 用户在待办页面删除待办
    LangChain Agent 调用: 通过工具函数 delete_todo(todo_id) 删除
    """
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
    """
    查询某个日期的待办
    ---
    前端调用: 用户在日历/待办页面按日期查看
    LangChain Agent 调用: 通过工具函数 query_todos_by_date(date) 查询
    """
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
    """
    查询某个用户的全部待办（支持按状态和日期范围过滤）
    ---
    前端调用: 用户在"我的待办"页面查看
    LangChain Agent 调用: 通过工具函数 query_user_todos(user_id) 查询
    """
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
    """
    查询单个待办详情
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    row = conn.execute("SELECT * FROM todo WHERE id = ?", (todo_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"待办 {todo_id} 不存在")

    return {"todo": _row_to_dict(row)}


@router.patch("/todo/{todo_id}/status")
def update_todo_status(todo_id: int, status_data: TodoStatusUpdate):
    """
    管理待办状态（标记完成/进行中等）
    ---
    前端调用: 用户勾选/切换待办状态
    LangChain Agent 调用: 通过工具函数 update_todo_status(todo_id, status) 更新
    """
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
    """
    更新待办信息（标题、描述、日期、优先级）
    ---
    前端调用: 用户编辑待办内容
    LangChain Agent 调用: 通过工具函数 update_todo(todo_id, ...) 更新
    """
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
    """
    列出所有待办（管理员视角，支持分页和过滤）
    ---
    前端调用: 管理员查看全校待办概览
    """
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


# ==================== 批量操作接口（供 LangChain Agent 使用） ====================

@router.post("/todo/batch/status")
def batch_update_status(data: BatchStatusUpdate):
    """
    批量更新待办状态
    ---
    LangChain Agent 调用: 一次性将多个待办标记为完成
    """
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
    """
    获取用户待办统计（各状态数量）
    ---
    前端调用: 仪表盘/待办页面展示统计卡片
    LangChain Agent 调用: 智能分析用户待办完成情况
    """
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
