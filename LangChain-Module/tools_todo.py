import requests

from langchain.tools import tool

from tool_config import BACKEND_API_BASE


@tool
def add_todo(user_id: str, title: str, date: str, description: str = "", priority: str = "medium") -> str:
    """添加待办事项。参数 user_id 为用户ID（学号/工号），title 为待办标题（必填），
    date 为日期格式 YYYY-MM-DD（必填），description 为详细描述（可选），
    priority 为优先级 low/medium/high（可选，默认 medium）。"""
    try:
        resp = requests.post(
            f"{BACKEND_API_BASE}/api/todo/add",
            json={
                "user_id": user_id,
                "title": title,
                "date": date,
                "description": description,
                "priority": priority,
            },
            timeout=10,
        )
        if resp.status_code == 400:
            detail = resp.json().get("detail", "参数错误")
            return f"添加待办失败：{detail}"
        resp.raise_for_status()
        data = resp.json()
        todo = data.get("todo", {})
        return f" 待办添加成功！\n  {todo.get('title')}\n  {todo.get('date')} | {todo.get('priority')} | {todo.get('status')}\n  ID: {todo.get('id')}"
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"添加待办出错：{str(e)}"


@tool
def delete_todo(todo_id: int) -> str:
    """删除待办事项。参数 todo_id 为待办的唯一ID（整数）。"""
    try:
        resp = requests.delete(
            f"{BACKEND_API_BASE}/api/todo/delete",
            params={"todo_id": todo_id},
            timeout=10,
        )
        if resp.status_code == 404:
            return f"待办 {todo_id} 不存在，可能已被删除。"
        resp.raise_for_status()
        data = resp.json()
        deleted = data.get("deleted", {})
        return f" 已删除待办：{deleted.get('title', '未知')}（日期：{deleted.get('date', '?')}）"
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"删除待办出错：{str(e)}"


@tool
def query_todos_by_date(date: str, user_id: str = "") -> str:
    """查询某个日期的待办事项。参数 date 为日期格式 YYYY-MM-DD（必填），
    user_id 为可选的用户ID，传入则只查该用户的待办。"""
    try:
        params = {}
        if user_id:
            params["user_id"] = user_id
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/todo/date/{date}",
            params=params,
            timeout=10,
        )
        if resp.status_code == 400:
            return f"查询失败：日期格式错误，应为 YYYY-MM-DD"
        resp.raise_for_status()
        data = resp.json()
        todos = data.get("todos", [])
        if not todos:
            who = f"{user_id} 在" if user_id else ""
            return f" {who}{date} 暂无待办事项。"
        lines = [f" {date} 待办事项（共 {len(todos)} 个）："]
        for t in todos:
            status_label = {"pending": "[待办]", "in_progress": "[进行中]", "completed": "[已完成]"}.get(t.get("status"), "[未知]")
            lines.append(
                f"  {status_label} [{t.get('id')}] {t.get('title')} | "
                f"  {t.get('priority', '?')} | "
                f"  {t.get('user_id', '?')}"
            )
        return "\n".join(lines)
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询待办出错：{str(e)}"


@tool
def query_user_todos(user_id: str, status: str = "", date_from: str = "", date_to: str = "") -> str:
    """查询某个用户的全部待办。参数 user_id 为用户ID/学号（必填），
    status 可选按状态过滤（pending/in_progress/completed），
    date_from/date_to 可选按日期范围过滤（YYYY-MM-DD）。"""
    try:
        params = {}
        if status:
            params["status"] = status
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/todo/user/{user_id}",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        todos = data.get("todos", [])
        if not todos:
            return f" {user_id} 暂无待办事项。"
        lines = [f" {user_id} 的待办事项（共 {len(todos)} 个）："]
        for t in todos:
            status_label = {"pending": "[待办]", "in_progress": "[进行中]", "completed": "[已完成]"}.get(t.get("status"), "[未知]")
            lines.append(
                f"  {status_label} [{t.get('id')}] {t.get('title')} | "
                f"  {t.get('date')} | 优先级:{t.get('priority', '?')}"
            )
        return "\n".join(lines)
    except requests.exceptions.ConnectionError:
        return "  无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询用户待办出错：{str(e)}"


@tool
def update_todo_status(todo_id: int, status: str) -> str:
    """更新待办状态。参数 todo_id 为待办ID（整数），
    status 为新状态：pending（待办）/ in_progress（进行中）/ completed（已完成）。"""
    try:
        resp = requests.patch(
            f"{BACKEND_API_BASE}/api/todo/{todo_id}/status",
            json={"status": status},
            timeout=10,
        )
        if resp.status_code == 400:
            detail = resp.json().get("detail", "状态值无效")
            return f"更新失败：{detail}"
        if resp.status_code == 404:
            return f"待办 {todo_id} 不存在。"
        resp.raise_for_status()
        data = resp.json()
        todo = data.get("todo", {})
        status_label = {"pending": "[待办]", "in_progress": "[进行中]", "completed": "[已完成]"}.get(status, "[未知]")
        return f"{status_label} 待办 [{todo_id}]「{todo.get('title', '?')}」状态已更新为：{status}"
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"更新待办状态出错：{str(e)}"


@tool
def get_todo_stats(user_id: str) -> str:
    """获取用户待办统计信息。参数 user_id 为用户ID/学号（必填）。
    返回各状态数量、今日待办数、逾期未完成数等统计数据。"""
    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/todo/stats/{user_id}",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        stats = data.get("stats", {})
        lines = [
            f" {user_id} 的待办统计：",
            f"  总计：{stats.get('total', 0)} 个",
            f"  待办：{stats.get('pending', 0)} 个",
            f"  进行中：{stats.get('in_progress', 0)} 个",
            f"  已完成：{stats.get('completed', 0)} 个",
            f"  今日待办：{stats.get('today', 0)} 个",
            f"  逾期未完成：{stats.get('overdue', 0)} 个",
        ]
        return "\n".join(lines)
    except requests.exceptions.ConnectionError:
        return "无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"获取待办统计出错：{str(e)}"
