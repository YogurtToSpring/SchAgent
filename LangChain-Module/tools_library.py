import requests

from langchain.tools import tool

from tool_config import BACKEND_API_BASE


@tool
def reserve_seat(user_id: str, seat_id: str, date: str, start_time: str, end_time: str) -> str:
    """预约图书馆座位。参数 user_id 为用户ID/学号（必填），seat_id 为座位编号如 A-001（必填），
    date 为日期 YYYY-MM-DD（必填），start_time 和 end_time 为时间段 HH:MM（必填，如 09:00-12:00）。
    图书馆开放时间 08:00-22:00。"""
    try:
        resp = requests.post(
            f"{BACKEND_API_BASE}/api/library/reserve",
            json={
                "user_id": user_id,
                "seat_id": seat_id,
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
            },
            timeout=10,
        )
        if resp.status_code == 400:
            detail = resp.json().get("detail", "参数错误")
            return f"预约失败：{detail}"
        if resp.status_code == 409:
            detail = resp.json().get("detail", "时间冲突")
            return f"预约失败：{detail}"
        if resp.status_code == 404:
            return f"预约失败：座位 {seat_id} 不存在"
        resp.raise_for_status()
        data = resp.json()
        r = data.get("reservation", {})
        return (
            f"预约成功！\n"
            f"  座位：{r.get('seat_id')}\n"
            f"  日期：{r.get('date')}\n"
            f"  时间：{r.get('start_time')}-{r.get('end_time')}\n"
            f"  预约编号：{r.get('id')}"
        )
    except requests.exceptions.ConnectionError:
        return "无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"预约座位出错：{str(e)}"


@tool
def cancel_reservation(reservation_id: int, user_id: str) -> str:
    """取消图书馆座位预约。参数 reservation_id 为预约记录ID（整数，必填），
    user_id 为用户ID/学号（必填），用于校验是否为本人操作。"""
    try:
        resp = requests.post(
            f"{BACKEND_API_BASE}/api/library/cancel",
            json={"reservation_id": reservation_id, "user_id": user_id},
            timeout=10,
        )
        if resp.status_code == 404:
            return f"预约记录 {reservation_id} 不存在。"
        if resp.status_code == 403:
            return "无权取消他人的预约，只能取消自己的预约。"
        if resp.status_code == 400:
            detail = resp.json().get("detail", "操作失败")
            return f"取消失败：{detail}"
        resp.raise_for_status()
        data = resp.json()
        r = data.get("reservation", {})
        return f" 预约已取消：座位 {r.get('seat_id')}，{r.get('date')} {r.get('start_time')}-{r.get('end_time')}"
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f" 取消预约出错：{str(e)}"


@tool
def get_user_reservations(user_id: str, status: str = "all") -> str:
    """查询用户的历史预约记录（含预约成功和已取消的记录）。
    参数 user_id 为用户ID/学号（必填），status 可选 'reserved'/'cancelled'/'completed'/'all'（默认 all）。"""
    try:
        params = {}
        if status and status != "all":
            params["status"] = status
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/library/user/{user_id}/history",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        reservations = data.get("reservations", [])
        if not reservations:
            return f"{user_id} 暂无预约记录。"
        lines = [f"{user_id} 的预约记录（共 {len(reservations)} 条）："]
        for r in reservations:
            status_label = {"reserved": "[已预约]", "cancelled": "[已取消]", "completed": "[已完成]"}.get(r.get("status"), "[未知]")
            lines.append(
                f"  {status_label} [{r.get('id')}] {r.get('seat_id')} | "
                f"{r.get('date')} {r.get('start_time')}-{r.get('end_time')} | "
                f"{r.get('status')}"
            )
        return "\n".join(lines)
    except requests.exceptions.ConnectionError:
        return "无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询预约记录出错：{str(e)}"


@tool
def get_seats_status(area: str = "") -> str:
    """查询图书馆当前各座位状态。参数 area 可选，按区域过滤（A/B/C），不传则返回全部。"""
    try:
        params = {}
        if area:
            params["area"] = area
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/library/seats/status",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        seats = data.get("seats", [])
        stats = data.get("stats", {})

        lines = ["图书馆座位状态："]
        for key, s in stats.items():
            lines.append(
                f"  {key}：可用 {s.get('available', 0)} / 已预约 {s.get('reserved', 0)} "
                f"（共 {s.get('total', 0)} 座）"
            )

        lines.append(f"\n 座位详情（显示前20个，共 {len(seats)} 个）：")
        for seat in seats[:20]:
            status_label = "[可用]" if seat.get("status") == "available" else "[已占用]"
            lines.append(f"  {status_label} {seat.get('seat_id')} | {seat.get('area')}区 {seat.get('floor')}F | {seat.get('status')}")
        if len(seats) > 20:
            lines.append(f"  ... 还有 {len(seats) - 20} 个座位")
        return "\n".join(lines)
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询座位状态出错：{str(e)}"


@tool
def get_available_seats(date: str, start_time: str, end_time: str, area: str = "") -> str:
    """查询指定时间段内的可用座位。参数 date 为日期 YYYY-MM-DD（必填），
    start_time/end_time 为时间段 HH:MM（必填），area 可选按区域过滤（A/B/C）。
    用于用户确定时间后查找可预约的座位。"""
    try:
        params = {"date": date, "start_time": start_time, "end_time": end_time}
        if area:
            params["area"] = area
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/library/seats/available",
            params=params,
            timeout=10,
        )
        if resp.status_code == 400:
            detail = resp.json().get("detail", "参数错误")
            return f"查询失败：{detail}"
        resp.raise_for_status()
        data = resp.json()
        available = data.get("available_seats", [])
        unavailable_count = data.get("unavailable_count", 0)

        lines = [f" {date} {start_time}-{end_time} 可用座位："]
        if not available:
            lines.append("  该时段暂无可用座位，请尝试其他时间段。")
        else:
            lines.append(f"  可用 {len(available)} 个 / 已占用 {unavailable_count} 个")
            lines.append("")
            by_area = {}
            for s in available:
                by_area.setdefault(s.get("area", "?"), []).append(s.get("seat_id"))
            for a, seats in by_area.items():
                lines.append(f"  {a}区（{len(seats)} 座）：{', '.join(seats[:10])}")
                if len(seats) > 10:
                    lines.append(f"       ... 还有 {len(seats) - 10} 个")
        return "\n".join(lines)
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询可用座位出错：{str(e)}"
