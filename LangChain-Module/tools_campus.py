import requests
from typing import Optional, Dict, Any

from langchain.tools import tool

from tool_config import BACKEND_API_BASE, DAY_NAMES


@tool
def query_student_schedule(stu_num: str, day_of_week: Optional[int] = None) -> str:
    """查询学生的个人课表 参数 stu_num 为学号
    day_of_week为星期几（可选） 1=周一, 2=周二, ..., 7=周日 不传则返回整周课表。"""
    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/class-stu/student/{stu_num}/details",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询课表出错：{str(e)}"

    courses = data.get("courses", [])
    if not courses:
        return f"学号为 {stu_num} 的同学暂无选课记录。"

    if day_of_week is not None:
        courses = [c for c in courses if c.get("day") == day_of_week]
        if not courses:
            return f"学号为 {stu_num} 的同学在{DAY_NAMES[day_of_week]}没有课程。"

    grouped = {}
    for c in courses:
        d = c.get("day", 0)
        grouped.setdefault(d, []).append(c)

    lines = [f" 学号 {stu_num} 的课表："]
    for d in sorted(grouped.keys()):
        lines.append(f"\n  {DAY_NAMES[d]}：")
        for c in grouped[d]:
            lines.append(
                f"    {c.get('course_name', '未知')} | "
                f" {c.get('start_time', '?')}-{c.get('end_time', '?')} | "
                f" {c.get('room_id', '未知')} | "
                f" {c.get('teacher_name', '未知')} | "
                f" 第{c.get('week_start', '?')}-{c.get('week_end', '?')}周"
            )
    return "\n".join(lines)


@tool
def query_course_info(
    course_id: Optional[str] = None,
    course_name: Optional[str] = None,
    teacher_name: Optional[str] = None,
    day_of_week: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    room_id: Optional[str] = None,
    week_start: Optional[int] = None,
    week_end: Optional[int] = None,
    semester: Optional[str] = None,
) -> str:
    """查询课程信息，支持多条件组合筛选。参数全部可选：
    course_id 课程编号（精确匹配，如 'CS101'），course_name 课程名（模糊匹配），
    teacher_name 老师名（模糊匹配），day_of_week 星期几（1-7），
    start_time 开始时间（如 '08:00'），end_time 结束时间（如 '09:30'），
    room_id 教室编号（如 '3-3-201'），week_start 起始周（整数），
    week_end 结束周（整数），semester 学期（如 '2024-2025-1'）。"""
    params: Dict[str, Any] = {}
    if course_id:
        params["course_id"] = course_id
    if course_name:
        params["course_name"] = course_name
    if teacher_name:
        params["teacher_name"] = teacher_name
    if day_of_week is not None:
        params["day"] = day_of_week
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    if room_id:
        params["room_id"] = room_id
    if week_start is not None:
        params["week_start"] = week_start
    if week_end is not None:
        params["week_end"] = week_end
    if semester:
        params["semester"] = semester

    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/course/display",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return "无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询课程出错：{str(e)}"

    courses = data.get("Courses", data.get("courses", []))
    if not courses:
        filters = ", ".join(f"{k}={v}" for k, v in params.items())
        return f"未找到符合条件的课程（筛选条件：{filters or '无'}）。"

    lines = [f"查询结果（共 {len(courses)} 门课程）："]
    for c in courses:
        d = c.get("day", 0)
        day_str = DAY_NAMES[d] if 1 <= d <= 7 else f"星期{d}"
        lines.append(
            f" [{c.get('course_id', '?')}] {c.get('course_name', '未知')} | "
            f"{day_str} {c.get('start_time', '?')}-{c.get('end_time', '?')} | "
            f"{c.get('teacher_name', '未知')} | "
            f"{c.get('room_id', '未知')} | "
            f"第{c.get('week_start', '?')}-{c.get('week_end', '?')}周 | "
            f"{c.get('semester', '未知学期')}"
        )
    return "\n".join(lines)


@tool
def query_class_students(class_name: str) -> str:
    """查询指定班级的学生名单。参数 class_name 为班级名称（如 '软件工程1班' 或班级 ID）。"""
    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/students",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return "无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询班级学生出错：{str(e)}"

    students = data.get("students", [])
    if not students:
        return "学校数据库中暂无学生数据。"

    matched = [
        s for s in students
        if class_name in (s.get("Cls", "") or "")
    ]
    if not matched:
        available = sorted(set(s.get("Cls", "未知") for s in students))
        return f"未找到班级 '{class_name}' 的学生。数据库中的班级：{', '.join(available)}"

    lines = [f"班级 '{class_name}' 学生名单（共 {len(matched)} 人）："]
    for s in matched:
        lines.append(f"  • {s.get('Name', '未知')}（学号：{s.get('StuNum', '未知')}）")
    return "\n".join(lines)


@tool
def query_student_info(stu_name: Optional[str] = None, stu_num: Optional[str] = None) -> str:
    """查询学生个人信息。参数 stu_name 学生姓名（模糊匹配），stu_num 学号（精确匹配），至少提供一个。"""
    if not stu_name and not stu_num:
        return "请至少提供学生姓名或学号中的一个条件。"

    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/students",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return "无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询学生信息出错：{str(e)}"

    students = data.get("students", [])
    if not students:
        return "学校数据库中暂无学生数据。"

    matched = students
    if stu_num:
        matched = [s for s in matched if s.get("StuNum") == stu_num]
    if stu_name:
        matched = [s for s in matched if stu_name in (s.get("Name", "") or "")]

    if not matched:
        return "未找到匹配的学生信息。"

    lines = [f"学生信息查询结果（共 {len(matched)} 人）："]
    for s in matched:
        lines.append(
            f"  • 姓名：{s.get('Name', '未知')} | "
            f"学号：{s.get('StuNum', '未知')} | "
            f"班级：{s.get('Cls', '未知')}"
        )
    return "\n".join(lines)


@tool
def query_room_info(room_full: Optional[str] = None, area: Optional[str] = None, building: Optional[str] = None) -> str:
    """查询教室信息。参数全部可选：
    room_full 完整教室号（如 '3-3-201'），area 区域编号，building 楼栋编号。"""
    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/room",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return "无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询教室信息出错：{str(e)}"

    rooms = data.get("rooms", [])
    if not rooms:
        return "学校数据库中暂无教室数据。"

    matched = rooms
    if room_full:
        parts = room_full.split("-")
        if len(parts) == 3:
            matched = [
                r for r in matched
                if r.get("area") == parts[0]
                and r.get("building") == parts[1]
                and r.get("room_id") == parts[2]
            ]
        else:
            matched = [r for r in matched if room_full in (r.get("room_full", "") or "")]
    if area:
        matched = [r for r in matched if r.get("area") == area]
    if building:
        matched = [r for r in matched if r.get("building") == building]

    if not matched:
        return "未找到匹配的教室信息。"

    lines = [f"教室查询结果（共 {len(matched)} 间）："]
    for r in matched:
        full = r.get("room_full", f"{r.get('area', '?')}-{r.get('building', '?')}-{r.get('room_id', '?')}")
        lines.append(f"  • {full} | 容量：{r.get('capacity', '未知')}人")
    return "\n".join(lines)


@tool
def query_teacher_students(teacher_num: str) -> str:
    """查询教师所教课程及每门课的学生名单（跨库 JOIN）。参数 teacher_num 为教师工号。
    适用于教师查看自己授课安排和学生情况，也适用于管理员进行教学管理。"""
    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/course/teacher/{teacher_num}/students",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return "无法连接到学校数据库服务，请确认 Backend 已启动。"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"未找到工号为 {teacher_num} 的教师，请确认工号是否正确。"
        return f"查询教师学生信息出错：{str(e)}"
    except Exception as e:
        return f"查询教师学生信息出错：{str(e)}"

    courses = data.get("courses", [])
    if not courses:
        teacher_name = data.get("teacher_name", teacher_num)
        return f"{teacher_name}（工号：{teacher_num}）目前没有授课安排。"

    teacher_name = data.get("teacher_name", "未知")
    lines = [f"{teacher_name}（工号：{teacher_num}）的授课情况（共 {data.get('count', len(courses))} 门课程）："]
    for course in courses:
        d = course.get("day", 0)
        day_str = DAY_NAMES[d] if 1 <= d <= 7 else f"星期{d}"
        lines.append(
            f"\n {course.get('course_name', '未知')} | "
            f" {day_str} {course.get('start_time', '?')}-{course.get('end_time', '?')} | "
            f" {course.get('room_id', '未知')} | "
            f" 第{course.get('week_start', '?')}-{course.get('week_end', '?')}周"
        )
        students = course.get("students", [])
        if students:
            lines.append(f"    选课学生（共 {len(students)} 人）：")
            for stu in students:
                lines.append(
                    f"      • {stu.get('name', '未知')}（学号：{stu.get('stu_num', '?')} | "
                    f"班级：{stu.get('cls', '未知')}）"
                )
        else:
            lines.append("    （暂无学生选课）")
    return "\n".join(lines)


@tool
def query_free_room(
    week: int,
    day: int,
    start_time: str,
    end_time: str,
    area: str,
    building: str,
    room_id: str,
) -> str:
    """检查指定教室在指定时间段是否空闲。参数：week 第几周（整数），day 星期几（1-7），
    start_time 开始时间（如 '08:00'），end_time 结束时间（如 '09:30'），
    area 区域编号（如 '3'），building 楼栋编号（如 '3'），room_id 教室号（如 '201'）。
    适用于师生查询空闲自习室、调课排课等场景。"""
    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/course/free-room",
            params={
                "week": str(week),
                "day": str(day),
                "st_time": start_time,
                "ed_time": end_time,
                "area": area,
                "building": building,
                "roomid": room_id,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        room_full = f"{area}-{building}-{room_id}"
        day_str = DAY_NAMES[day] if 1 <= day <= 7 else f"星期{day}"
        return (
            f" 教室 {room_full} 在第{week}周 {day_str} "
            f"{start_time}-{end_time} 时段空闲，可以使用。"
        )
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = str(e)
            room_full = f"{area}-{building}-{room_id}"
            day_str = DAY_NAMES[day] if 1 <= day <= 7 else f"星期{day}"
            return (
                f" 教室 {room_full} 在第{week}周 {day_str} "
                f"{start_time}-{end_time} 时段已被占用。\n"
                f"详情：{detail}"
            )
        elif e.response.status_code == 404:
            return f"未找到教室 {area}-{building}-{room_id}，请确认区域、楼栋和教室编号是否正确。"
        return f"查询空闲教室出错：{str(e)}"
    except Exception as e:
        return f"查询空闲教室出错：{str(e)}"


@tool
def query_course_students(course_id: str) -> str:
    """查询某课程的所有选课学生（含姓名和班级）。参数 course_id 为课程编号（如 'CS101'）。
    适用于教师查看自己课程的学生名单、管理员进行教学统计等场景。"""
    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/class-stu/course/{course_id}",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"未找到课程编号为 {course_id} 的课程，请确认编号是否正确。"
        return f"查询课程学生出错：{str(e)}"
    except Exception as e:
        return f"查询课程学生出错：{str(e)}"

    stu_list = data.get("students", [])
    if not stu_list:
        return f" 课程 {course_id} 目前没有学生选课。"

    stu_nums = [s["stu_num"] for s in stu_list]
    try:
        resp2 = requests.get(
            f"{BACKEND_API_BASE}/api/students",
            timeout=10,
        )
        resp2.raise_for_status()
        all_students = resp2.json().get("students", [])
        stu_map = {s["StuNum"]: s for s in all_students}
    except Exception:
        stu_map = {}

    lines = [f" 课程 {course_id} 选课学生名单（共 {len(stu_list)} 人）："]
    for s in stu_list:
        snum = s["stu_num"]
        info = stu_map.get(snum, {})
        name = info.get("Name", "未知")
        cls = info.get("Cls", "未知")
        lines.append(f"  • {name}（学号：{snum} | 班级：{cls}）")
    return "\n".join(lines)


@tool
def query_all_teachers() -> str:
    """列出学校数据库中所有教师的基本信息（姓名和工号）。不需要任何参数。
    适用于学生查找老师、管理员管理师资等场景。"""
    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/teacher",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询教师列表出错：{str(e)}"

    teachers = data.get("teacher", [])
    if not teachers:
        return "学校数据库中暂无教师数据。"

    lines = [f" 教师列表（共 {len(teachers)} 人）："]
    for t in teachers:
        lines.append(f"  • {t.get('Name', '未知')}（工号：{t.get('Number', '未知')}）")
    return "\n".join(lines)


@tool
def query_all_enrollments() -> str:
    """列出学校数据库中所有选课记录（课程编号 + 学号）。不需要任何参数。
    适用于管理员查看全景选课数据、统计分析等场景。"""
    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/class-stu",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询选课记录出错：{str(e)}"

    enrollments = data.get("enrollments", [])
    if not enrollments:
        return "学校数据库中暂无选课记录。"

    lines = [f" 全部选课记录（共 {len(enrollments)} 条）："]
    for e in enrollments:
        lines.append(f"  • 课程：{e.get('course_id', '?')} → 学生学号：{e.get('stu_num', '?')}")
    return "\n".join(lines)
