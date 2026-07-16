import requests
from typing import Optional

from langchain.tools import tool

from tool_config import BACKEND_API_BASE


@tool
def query_student_grades(stu_num: str, semester: Optional[str] = None) -> str:
    """查询学生个人成绩。参数 stu_num 为学号（必填），semester 为学期筛选（可选，格式如 '2024-2025-1'）。
    返回各科成绩含课程名、学分、平时/期末/总评分数、绩点和等级。
    学生只能查询自己的成绩，教师和管理员可根据需要查询指定学生的成绩。"""
    try:
        params = {}
        if semester:
            params["semester"] = semester
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/grade/student/{stu_num}",
            params=params,
            timeout=10,
        )
        if resp.status_code == 404:
            detail = resp.json().get("detail", "学生不存在")
            return f"查询失败：{detail}"
        if resp.status_code == 400:
            detail = resp.json().get("detail", "参数错误")
            return f"查询失败：{detail}"
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询学生成绩出错：{str(e)}"

    grades = data.get("grades", [])
    name = data.get("name", stu_num)
    cls = data.get("cls", "未知")
    sem_filter = data.get("semester", semester or "全部学期")

    if not grades:
        return f"未查询到学生 {name}（{stu_num}）在 {sem_filter} 的成绩记录。"

    lines = [
        f"  {name} 的成绩单",
        f"学号：{stu_num} | 班级：{cls} | 学期：{sem_filter}",
        f"共 {len(grades)} 门课程：",
        "",
    ]
    for g in grades:
        cname = g.get("course_name", g.get("course_id", "未知"))
        cid = g.get("course_id", "")
        credit = g.get("credit", "?")
        regular = g.get("regular_score", "?")
        final_exam = g.get("final_exam_score", "?")
        total = g.get("final_score", "?")
        gp = g.get("grade_point", "?")
        gl = g.get("grade_letter", "?")
        exam_type = g.get("exam_type", "")
        remark = g.get("remark", "")

        lines.append(f"  {cname}（{cid}）| 学分：{credit}")
        lines.append(f"   平时：{regular} | 期末：{final_exam} | 总评：{total} | 绩点：{gp} | 等级：{gl}")
        if exam_type:
            lines.append(f"   考试类型：{exam_type}")
        if remark:
            lines.append(f"   备注：{remark}")
        lines.append("")

    return "\n".join(lines)


@tool
def query_course_grades(course_id: str) -> str:
    """查询某门课程的全部学生成绩及统计信息。参数 course_id 为课程编号（必填）。
    返回课程基本信息、成绩统计（平均分/最高分/最低分/及格率）和每位学生的成绩。
    适用于教师查看所授课程的成绩分布，或管理员进行教学质量分析。"""
    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/grade/course/{course_id}",
            timeout=10,
        )
        if resp.status_code == 404:
            detail = resp.json().get("detail", "课程不存在")
            return f"查询失败：{detail}"
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询课程成绩出错：{str(e)}"

    course_name = data.get("course_name", course_id)
    credit = data.get("course_credit", "?")
    teacher = data.get("teacher_num", "未知")
    semester = data.get("semester", "未知")
    students = data.get("students", [])
    stats = data.get("stats", {})
    count = data.get("count", len(students))

    if not students:
        return f"课程 {course_name}（{course_id}）暂无成绩记录。"

    lines = [
        f" 课程成绩报告",
        f"课程：{course_name}（{course_id}）| 学分：{credit} | 教师：{teacher} | 学期：{semester}",
        "",
    ]

    if stats:
        lines.append(" 成绩统计：")
        lines.append(f"  平均分：{stats.get('avg_score', '?')} | 最高分：{stats.get('max_score', '?')} | 最低分：{stats.get('min_score', '?')}")
        lines.append(f"  及格人数：{stats.get('pass_count', '?')}/{count} | 及格率：{stats.get('pass_rate', '?')}%")
        lines.append("")

    lines.append(f" 学生成绩列表（共 {count} 人）：")
    lines.append("")
    for s in students:
        sname = s.get("name", "未知")
        snum = s.get("stu_num", "?")
        scls = s.get("cls", "?")
        regular = s.get("regular_score", "?")
        final_exam = s.get("final_exam_score", "?")
        total = s.get("final_score", "?")
        gp = s.get("grade_point", "?")
        gl = s.get("grade_letter", "?")
        lines.append(
            f"  • {sname}（{snum} | {scls}）| "
            f"平时：{regular} | 期末：{final_exam} | 总评：{total} | 绩点：{gp} | 等级：{gl}"
        )

    return "\n".join(lines)


@tool
def query_teacher_grades(teacher_num: str) -> str:
    """查询某位教师所教全部课程的成绩。参数 teacher_num 为教师工号（必填）。
    返回教师名下每门课程的学生成绩列表及统计信息（平均分/最高分/最低分/及格率）。
    适用于教师查看自己所授全部课程的成绩概况。"""
    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/grade/teacher/{teacher_num}",
            timeout=10,
        )
        if resp.status_code == 404:
            detail = resp.json().get("detail", "教师不存在")
            return f"查询失败：{detail}"
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询教师课程成绩出错：{str(e)}"

    teacher_name = data.get("teacher_name", teacher_num)
    courses = data.get("courses", [])
    course_count = data.get("count", len(courses))

    if not courses:
        return f"教师 {teacher_name}（{teacher_num}）暂无课程成绩记录。"

    lines = [
        f" {teacher_name}（{teacher_num}）所授课程成绩报告",
        f"共 {course_count} 门课程：",
        "",
    ]

    for idx, course in enumerate(courses, 1):
        cid = course.get("course_id", "?")
        cname = course.get("course_name", "未知")
        credit = course.get("credit", "?")
        semester = course.get("semester", "未知")
        students = course.get("students", [])
        ccount = course.get("count", len(students))
        stats = course.get("stats", {})

        lines.append(f"{'─' * 50}")
        lines.append(f"  [{idx}] {cname}（{cid}）| 学分：{credit} | 学期：{semester}")

        if stats:
            lines.append(f"  平均分：{stats.get('avg_score', '?')} | 最高：{stats.get('max_score', '?')} | 最低：{stats.get('min_score', '?')} | 及格率：{stats.get('pass_rate', '?')}%（{stats.get('pass_count', '?')}/{ccount}）")

        if students:
            lines.append(f"  学生成绩（{ccount} 人）：")
            for s in students:
                sname = s.get("name", "未知")
                snum = s.get("stu_num", "?")
                total = s.get("final_score", "?")
                gp = s.get("grade_point", "?")
                gl = s.get("grade_letter", "?")
                lines.append(f"      {sname}（{snum}）| 总评：{total} | 绩点：{gp} | 等级：{gl}")

        lines.append("")

    return "\n".join(lines)


@tool
def query_all_grades(semester: Optional[str] = None) -> str:
    """查询全校全部成绩记录（管理员专用）。参数 semester 为学期筛选（可选，格式如 '2024-2025-1'）。
    返回所有成绩记录的列表，最多展示 50 条。"""
    try:
        params = {}
        if semester:
            params["semester"] = semester
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/grade",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return " 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询全部成绩出错：{str(e)}"

    grades = data.get("grades", [])
    total_count = data.get("count", len(grades))

    if not grades:
        sem_hint = f"（学期：{semester}）" if semester else ""
        return f"学校数据库中暂无成绩记录{sem_hint}。"

    sem_hint = f" | 学期：{semester}" if semester else ""
    lines = [f" 全校成绩记录（共 {total_count} 条）{sem_hint}：", ""]

    display_count = min(len(grades), 50)
    for g in grades[:display_count]:
        cid = g.get("course_id", "?")
        snum = g.get("stu_num", "?")
        regular = g.get("regular_score", "?")
        final_exam = g.get("final_exam_score", "?")
        total = g.get("final_score", "?")
        gp = g.get("grade_point", "?")
        gl = g.get("grade_letter", "?")
        sem = g.get("semester", "?")
        lines.append(
            f"  • 课程：{cid} | 学号：{snum} | "
            f"平时：{regular} | 期末：{final_exam} | 总评：{total} | 绩点：{gp} | 等级：{gl} | 学期：{sem}"
        )

    if total_count > 50:
        lines.append("")
        lines.append(f"... 仅展示前 50 条，共 {total_count} 条记录。如需更精确的查询，请使用学期筛选或按学生/课程查询。")

    return "\n".join(lines)
