"""
SchAgent LangChain 核心模块
============================
使用 LangGraph + DeepSeek 构建带记忆的智能体，向外提供函数级接口。

相比原版的改进：
1. ★ LangGraph MemorySaver 自动管理会话记忆（不再需要手动写 txt）
2. ★ UserMemoryStore 管理长期记忆（课表、偏好等跨会话数据）
3. ★ 修复 list_files 的 os.listdir 参数错误
4. ★ 修复 init_userinfo 全局变量遮蔽问题
5. ★ 替换危险的 eval() 为安全数学计算
6. ★ 添加路径遍历防护
7. ★ 提供清晰的函数接口供 API 层调用
"""

import os
import re
import json
import math
import requests
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from langchain.tools import tool
from langchain_deepseek import ChatDeepSeek
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from langchain_core.callbacks import BaseCallbackHandler


# ============================================================
# 配置（通过环境变量覆盖默认值）
# ============================================================

load_dotenv()
WORKSPACE_DIR = Path(os.getenv("SCHAGENT_WORKSPACE", str(Path(__file__).parent / "workspace")))
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

API_KEY = os.getenv("DEEPSEEK_API_KEY")
MODEL_NAME = os.getenv("DEEPSEEK_MODEL")
BACKEND_API_BASE = os.getenv("SCHAGENT_BACKEND_URL")

SYSTEM_PROMPT = """你是一个有用的校园生活智能助手，名为 SchAgent。
与用户对话时务必保持严格的Markdown格式输出，前端会将你的回答直接渲染为网页内容。
对话/生成的PDF中尽量不要使用emoji表情。
请遵循以下规则：

## 通用工具：
- get_weather: 查询城市天气
- calculator: 安全地执行数学计算
- query_day_of_week: 查询指定日期是星期几
- get_current_time: 获取当前日期和时间
- read_file: 读取工作区中的文件
- write_file: 将内容写入工作区文件
- list_files: 列出工作区目录下的内容
- save_memory: 保存用户的长期记忆（课表、偏好、笔记等）
- recall_memory: 读取用户的长期记忆
- markdown_to_html: 将 Markdown 文本转换为 HTML
- markdown_to_pdf: 将 Markdown 文本转换为 PDF 文件
- use_python_pptx: 使用 python-pptx 库操作 PPTX 文件（创建/编辑幻灯片）

## 校园信息查询工具（从学校数据库获取真实数据）：
- query_student_schedule: 查询学生个人课表（按学号 + 可选星期几）
- query_course_info: 多条件查询课程信息（可按课程编号、课程名、老师、星期、时间、教室、周次、学期等组合筛选）
- query_class_students: 查询班级学生名单（按班级名称）
- query_student_info: 查询学生个人信息（按姓名或学号）
- query_room_info: 查询教室信息（按教室编号、区域、楼栋）
- query_teacher_students: 查询教师所教课程及每门课的学生名单（按教师工号）
- query_free_room: 检查指定教室在指定时间段是否空闲（按周次、星期、时间、教室）
- query_course_students: 查询某课程的选课学生名单（按课程编号，含姓名班级）
- query_all_teachers: 列出全校教师列表（姓名和工号）
- query_all_enrollments: 列出全部选课记录（管理员全景视图）

## 待办管理工具（个人任务管理）：
- add_todo: 添加待办事项（需提供 user_id、标题、日期，可选描述和优先级）
- delete_todo: 删除指定ID的待办事项
- query_todos_by_date: 查询某个日期的待办（可按用户过滤）
- query_user_todos: 查询某用户的全部待办（支持按状态、日期范围过滤）
- update_todo_status: 更新待办状态（pending / in_progress / completed）
- get_todo_stats: 获取用户待办统计（各状态数量、今日待办、逾期数）

## 图书馆座位管理工具：
- reserve_seat: 预约图书馆座位（需提供 user_id、seat_id、日期、时间段）
- cancel_reservation: 取消预约（需提供 reservation_id 和 user_id 校验身份）
- get_user_reservations: 查询用户历史预约记录（预约成功和已取消的）
- get_seats_status: 查询当前各座位状态概览（可用/已预约数量，按区域）
- get_available_seats: 查询指定时间段内的可用座位列表

## 使用原则：
1. 维护对话上下文，记住用户在当前会话中说过的信息
2. 对于需要长期记住的信息（如课表），主动使用 save_memory 保存
3. 对于课表、课程、班级、学生、教室等校园信息查询，必须使用对应的 query_ 系列工具从学校数据库获取准确数据，不要凭猜测回答
4. 对于需要制作PPT的请求，请使用 use_python_pptx 工具生成 PPTX 文件，色调以浅色系为主，可以结合用户制作的PPT调整，这个工具已经预导入了所需的模块，直接使用预导入的对象即可。
5. 如果不需要调用工具就直接生成回答
6. 回答简洁、友好

## 角色感知原则：
- 每条消息开头会附带 [用户信息] 块，包含当前用户的姓名、身份、班级等信息
- 不允许查询其他人的课程、课表、成绩等隐私信息
- 不随意调用查询数据库的tools，仅在用户明确查询**自己**的课表、课程、班级、学生、教室等信息时才使用
- 学生（student）：可查询个人课表、课程信息、同班同学，不允许查询其他班级或其他学生的隐私信息
- 教师（teacher）：可查询授课安排、班级学生名单、教室信息，不允许查询其他教师或学生的隐私信息
- 管理员（admin）：可查询全部数据，帮助进行系统管理和数据统计分析
- 使用 query_ 系列工具时，应优先利用用户信息中的班级、学号等限定查询范围，提高准确性

## 错误处理规则
- 若工具返回空结果，应告知用户"未查询到相关数据，请检查查询条件"
- 若工具调用失败，应重试一次，仍失败则提示"系统繁忙，请稍后重试"
- 不得编造数据库查询结果
"""


# ============================================================
# 长期记忆存储（JSON 文件，跨会话持久化）
# ============================================================
# 注意：这与 LangGraph 的 MemorySaver（对话历史检查点）是两回事。
# MemorySaver → 自动保存会话内的对话历史
# UserMemoryStore → 手动保存需要长期记住的信息（课表、偏好等）

class UserMemoryStore:
    """基于 JSON 文件的用户长期记忆存储"""

    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, username: str) -> Path:
        safe_name = "".join(c for c in username if c.isalnum() or c in "_-")
        return self.storage_dir / f"{safe_name}.json"

    def get_all(self, username: str) -> dict:
        path = self._get_path(username)
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get(self, username: str, key: str) -> Optional[Any]:
        return self.get_all(username).get(key)

    def set(self, username: str, key: str, value: Any) -> None:
        path = self._get_path(username)
        data = self.get_all(username)
        data[key] = value
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def delete(self, username: str, key: Optional[str] = None) -> None:
        path = self._get_path(username)
        if key is None:
            path.unlink(missing_ok=True)
        elif path.exists():
            data = self.get_all(username)
            data.pop(key, None)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def list_keys(self, username: str) -> List[str]:
        return list(self.get_all(username).keys())


memory_store = UserMemoryStore(WORKSPACE_DIR / "user_data")


# ============================================================
# 工具定义
# ============================================================

class ToolCallHandler(BaseCallbackHandler):
    """Agent 调用工具时打印日志"""
    def on_tool_start(self, serialized, input_str, **kwargs):
        print(f"[Tool] {serialized['name']}({input_str})")


@tool
def get_weather(city: str) -> str:
    """查询指定城市的实时天气情况。参数 city 为城市名称（中文或英文），如 '北京'、'上海'、'Tokyo'。
    通过 uapis.cn 免费天气 API 获取真实数据。"""
    API_URL = "https://uapis.cn/api/v1/misc/weather"

    try:
        resp = requests.get(
            API_URL,
            params={"city": city, "extended": True, "indices": True},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return f"查询 {city} 天气超时，请稍后重试。"
    except requests.exceptions.ConnectionError:
        return "⚠️ 天气服务暂时无法连接，请检查网络后重试。"
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 404:
            return f"未找到城市 '{city}' 的天气数据，请检查城市名称是否正确。"
        return f"查询天气失败（HTTP {resp.status_code}），请稍后重试。"
    except Exception as e:
        return f"查询天气出错：{str(e)}"

    # 检查是否有错误字段
    if "code" in data and data["code"] != 200:
        return f"查询天气失败：{data.get('message', '未知错误')}"

    # ---- 构建友好的天气报告 ----
    province = data.get("province", "")
    district = data.get("district", "")
    location = f"{province} {city}"
    if district:
        location += f" {district}"

    lines = [f"📍 {location} 实时天气（{data.get('report_time', '')}）"]
    lines.append(f"🌤 天气：{data.get('weather', '未知')}")
    lines.append(f"🌡 温度：{data.get('temperature', '--')}°C"
                 f"（体感 {data.get('feels_like', '--')}°C）")
    lines.append(f"💧 湿度：{data.get('humidity', '--')}%")
    lines.append(f"💨 风力：{data.get('wind_direction', '--')} {data.get('wind_power', '--')}")

    # 空气质量
    aqi = data.get("aqi")
    if aqi is not None:
        aqi_level = data.get("aqi_category", "")
        primary = data.get("aqi_primary", "")
        lines.append(f"🍃 空气质量：AQI {aqi}（{aqi_level}）"
                     + (f"，主要污染物 {primary}" if primary else ""))

    # 能见度 & 紫外线
    vis = data.get("visibility")
    if vis:
        lines.append(f"👁 能见度：{vis} km")
    uv = data.get("uv")
    if uv:
        uv_desc = "低" if uv < 3 else ("中等" if uv < 6 else ("高" if uv < 8 else "极高"))
        lines.append(f"☀ 紫外线：{uv}（{uv_desc}）")

    # 生活指数精选（穿衣、运动、雨伞）
    indices = data.get("life_indices", {})
    if indices:
        clothing = indices.get("clothing", {})
        if clothing:
            lines.append(f"👔 穿衣建议：{clothing.get('advice', clothing.get('brief', ''))}")
        umbrella = indices.get("umbrella", {})
        if umbrella:
            lines.append(f"☂ 雨伞：{umbrella.get('brief', umbrella.get('advice', ''))}")
        exercise = indices.get("exercise", {})
        if exercise:
            lines.append(f"🏃 运动：{exercise.get('brief', exercise.get('advice', ''))}")

    # 预警信息
    alerts = data.get("alerts", [])
    if alerts:
        lines.append(f"\n⚠️ 气象预警（{len(alerts)}条）：")
        for alert in alerts[:3]:  # 最多显示3条
            lines.append(f"  • {alert.get('type', '')} {alert.get('level', '')}预警：{alert.get('title', '')}")

    return "\n".join(lines)

@tool
def query_day_of_week(date_str: str) -> str:
    """查询指定日期是星期几。参数 date_str 为日期字符串，支持 'YYYY-MM-DD' 或 'YYYY/MM/DD' 格式。"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            date_obj = datetime.strptime(date_str, "%Y/%m/%d")
        except ValueError:
            return "日期格式错误，请使用 'YYYY-MM-DD' 或 'YYYY/MM/DD' 格式。"

    weekday = date_obj.isoweekday()  # 1=周一, 7=周日
    day_names = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return f"{date_str} 是 {day_names[weekday]}。"

@tool
def calculator(expression: str) -> str:
    """安全地执行数学计算。参数 expression 为数学表达式，支持 + - * / ** // % 及 sqrt/log/sin 等数学函数。例如 '3 + 5 * 2'、'sqrt(16) + 10'。"""
    # ★ 修复：不再使用危险的裸 eval()，使用受限命名空间
    allowed = {
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "log": math.log, "log10": math.log10, "log2": math.log2,
        "exp": math.exp, "abs": abs, "round": round, "pow": pow,
        "pi": math.pi, "e": math.e, "ceil": math.ceil, "floor": math.floor,
    }
    try:
        code = compile(expression, "<calculator>", "eval")
        # 仅允许安全的数学函数和字面量
        for name in code.co_names:
            if name not in allowed and name not in dir(__builtins__):
                pass  # 内置常量放行，其他由 eval 的受限 __builtins__ 拦截
        result = eval(code, {"__builtins__": {}}, allowed)
        return f"计算结果：{expression} = {result}"
    except Exception as e:
        return f"计算出错：{str(e)}。请使用基本运算（+ - * / ** // %）或数学函数。"


@tool
def get_current_time() -> str:
    """获取当前日期和时间。不需要任何参数。"""
    return datetime.now().strftime("当前时间：%Y年%m月%d日 %H:%M:%S")


@tool
def list_files() -> str:
    """列出工作区目录下的所有文件和文件夹。不需要任何参数。"""
    try:
        # ★ 修复：os.listdir 只接受一个参数
        items = os.listdir(WORKSPACE_DIR)
        if not items:
            return "工作区目前没有文件。"
        lines = []
        for item in sorted(items):
            item_path = WORKSPACE_DIR / item
            if item_path.is_dir():
                lines.append(f" {item}/")
            else:
                size = item_path.stat().st_size
                lines.append(f" {item} ({_format_size(size)})")
        return "工作区目录内容：\n" + "\n".join(lines)
    except Exception as e:
        return f"列出文件出错：{str(e)}"


@tool
def read_file(file_name: str) -> str:
    """读取工作区中指定文件的内容。参数 file_name 为文件名称（如 'notes.txt'）。"""
    # ★ 修复：防止路径遍历攻击
    file_path = (WORKSPACE_DIR / file_name).resolve()
    if not str(file_path).startswith(str(WORKSPACE_DIR.resolve())):
        return "错误：不允许访问工作区以外的文件。"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if not content:
            return f"文件 '{file_name}' 是空的。"
        return f"文件 '{file_name}' 的内容：\n{content}"
    except FileNotFoundError:
        return f"文件 '{file_name}' 不存在。"
    except Exception as e:
        return f"读取文件出错：{str(e)}"


@tool
def write_file(file_name: str, content: str) -> str:
    """将内容写入工作区的指定文件。参数 file_name 为文件名称，content 为要写入的内容。"""
    # ★ 修复：防止路径遍历攻击
    file_path = (WORKSPACE_DIR / file_name).resolve()
    if not str(file_path).startswith(str(WORKSPACE_DIR.resolve())):
        return "错误：不允许写入工作区以外的文件。"
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"已将内容写入文件：{file_name}"
    except Exception as e:
        return f"写入文件出错：{str(e)}"


@tool
def save_memory(username: str, key: str, content: str) -> str:
    """保存一条长期记忆。参数 username 为用户名，key 为记忆名称（如 'schedule'、'preferences'），content 为要记住的内容。
    当你需要帮助用户长期记住某些信息时，请使用此工具。"""
    try:
        memory_store.set(username, key, content)
        return f"已为用户 '{username}' 保存记忆 [{key}]：{content}"
    except Exception as e:
        return f"保存记忆出错：{str(e)}"


@tool
def recall_memory(username: str, key: Optional[str] = None) -> str:
    """读取用户的长期记忆。参数 username 为用户名，key 为要读取的记忆名称（可选）。
    若不指定 key 则列出所有记忆键名，指定 key 则返回记忆内容。"""
    try:
        if key:
            value = memory_store.get(username, key)
            if value is None:
                return f"用户 '{username}' 没有名为 '{key}' 的记忆。"
            return f"用户 '{username}' 的记忆 [{key}]：{value}"
        else:
            keys = memory_store.list_keys(username)
            if not keys:
                return f"用户 '{username}' 目前没有任何长期记忆。"
            return f"用户 '{username}' 的记忆列表：{', '.join(keys)}"
    except Exception as e:
        return f"读取记忆出错：{str(e)}"

@tool
def markdown_to_html(markdown_text: str) -> str:
    """将 Markdown 文本转换为 HTML。参数 markdown_text 为 Markdown 格式的字符串。"""
    try:
        import markdown
        html = markdown.markdown(markdown_text)
        return html
    except ImportError:
        return "Markdown 转 HTML 功能需要安装 'markdown' 库，请先运行 'pip install markdown'。"
    except Exception as e:
        return f"Markdown 转 HTML 出错：{str(e)}"

@tool
def markdown_to_pdf(markdown_text: str, output_file: str = "output.pdf") -> str:
    """将 Markdown 文本转换为 PDF 文件。参数 markdown_text 为 Markdown 格式的字符串，output_file 为输出 PDF 文件名（可选，默认 'output.pdf'）。"""
    try:
        import markdown
        import pdfkit

        # 将 Markdown 转为 HTML
        body_content = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code', 'codehilite'])

        # 包装为完整 HTML 文档，指定 UTF-8 编码和中文字体
        full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: "Microsoft YaHei", "SimHei", "SimSun", "Noto Sans SC", "WenQuanYi Micro Hei", sans-serif;
            font-size: 14px;
            line-height: 1.8;
            color: #333;
            padding: 20px;
        }}
        h1, h2, h3, h4, h5, h6 {{
            font-family: "Microsoft YaHei", "SimHei", sans-serif;
            color: #1a1a1a;
        }}
        code {{
            font-family: "Consolas", "Courier New", monospace;
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
        }}
        pre {{
            background-color: #f4f4f4;
            padding: 12px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        pre code {{
            background: none;
            padding: 0;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #f0f0f0;
        }}
        blockquote {{
            border-left: 4px solid #ddd;
            padding-left: 16px;
            color: #666;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
{body_content}
</body>
</html>"""

        # 将 HTML 转为 PDF
        pdf_path = WORKSPACE_DIR / output_file
        pdfkit.from_string(full_html, str(pdf_path))

        return f"已将 Markdown 转换为 PDF: {pdf_path}"
    except ImportError:
        return "Markdown 转 PDF 功能需要安装 'markdown' 和 'pdfkit' 库，请先运行 'pip install markdown pdfkit'。此外还需安装 wkhtmltopdf (https://wkhtmltopdf.org/downloads.html)。"
    except Exception as e:
        return f"Markdown 转 PDF 出错：{str(e)}"

@tool
def use_python_pptx(command: str) -> str:
    """使用 python-pptx 库操作 PPTX 文件。参数 command 为一段 Python 代码字符串，
    该代码可以使用已导入的 python-pptx 模块（pptx）来创建或编辑 PowerPoint 文件。
    代码中可使用以下已导入的对象：
    - Presentation (from pptx import Presentation)
    - Inches, Pt, Emu (from pptx.util)
    - 以及 pptx 整个模块
    注意：代码中禁止使用 os、sys、subprocess、shutil、importlib、__import__、
    open（仅允许 Presentation.save 内部使用）、eval、exec、compile 等危险操作。
    工作目录为 WORKSPACE_DIR，生成的文件请放在当前目录下。"""
    import io
    import sys
    import traceback

    # ---- 安全检查：禁止危险关键字 ----
    FORBIDDEN_KEYWORDS = [
        "os.", "sys.", "subprocess", "shutil", "importlib",
        "__import__", "eval(", "exec(", "compile(", "globals(",
        "locals(", "__builtins__", "__globals__", "__locals__",
        "open(", "file(", "input(", "raw_input(",
        "socket", "urllib", "requests.", "http",
        "rmdir", "remove(", "unlink(", "rmtree",
        "Thread(", "Process(", "fork(",
        "setattr(", "delattr(", "__class__", "__bases__",
        "__subclasses__", "__mro__", "__code__", "__frame__",
        "ctypes", "winreg", "_winreg",
    ]
    command_lower = command.lower()
    for kw in FORBIDDEN_KEYWORDS:
        if kw.lower() in command_lower:
            return f"❌ 安全检查未通过：代码中包含禁止的关键字 '{kw}'。请移除相关调用后重试。"

    # ---- 准备受限的执行环境 ----
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt, Emu
        import pptx
    except ImportError:
        return "PPTX 操作功能需要安装 'python-pptx' 库，请先运行 'pip install python-pptx'。"

    # 安全的全局命名空间：只暴露必要的模块和对象
    safe_globals = {
        "__builtins__": {
            "print": print,
            "range": range,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sorted": sorted,
            "reversed": reversed,
            "min": min,
            "max": max,
            "sum": sum,
            "abs": abs,
            "round": round,
            "isinstance": isinstance,
            "type": type,
            "hasattr": hasattr,
            "getattr": getattr,
            "True": True,
            "False": False,
            "None": None,
            "Exception": Exception,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "KeyError": KeyError,
            "IndexError": IndexError,
            "StopIteration": StopIteration,
            "super": super,
            "object": object,
            "property": property,
            "staticmethod": staticmethod,
            "classmethod": classmethod,
        },
        "Presentation": Presentation,
        "Inches": Inches,
        "Pt": Pt,
        "Emu": Emu,
        "pptx": pptx,
        "WORKSPACE_DIR": WORKSPACE_DIR,
        "Path": Path,
    }
    safe_locals = {}

    # ---- 捕获标准输出 ----
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    sys.stdout = captured_stdout
    sys.stderr = captured_stderr

    result = None
    try:
        # 切换到工作目录执行
        original_cwd = os.getcwd()
        os.chdir(str(WORKSPACE_DIR))

        try:
            exec(command, safe_globals, safe_locals)
            result = "✅ PPTX 代码执行成功。"
        finally:
            os.chdir(original_cwd)
    except SyntaxError as e:
        result = f"❌ Python 语法错误：{str(e)}"
    except Exception as e:
        result = f"❌ 代码执行出错：{str(e)}\n\n详细堆栈：\n{traceback.format_exc()}"
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    # 拼接输出信息
    stdout_output = captured_stdout.getvalue()
    stderr_output = captured_stderr.getvalue()

    parts = [result or "✅ PPTX 代码执行完成。"]
    if stdout_output.strip():
        parts.append(f"--- 标准输出 ---\n{stdout_output.strip()}")
    if stderr_output.strip():
        parts.append(f"--- 标准错误 ---\n{stderr_output.strip()}")

    return "\n\n".join(parts)

# ============================================================
# 校园数据库查询工具（通过 Backend HTTP API）
# ============================================================

DAY_NAMES = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]


@tool
def query_student_schedule(stu_num: str, day_of_week: Optional[int] = None) -> str:
    """查询学生的个人课表。参数 stu_num 为学号（如 '2024001'），
    day_of_week 可选，为星期几（1=周一, 2=周二, ..., 7=周日），不传则返回整周课表。"""
    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/class-stu/student/{stu_num}/details",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询课表出错：{str(e)}"

    courses = data.get("courses", [])
    if not courses:
        return f"学号为 {stu_num} 的同学暂无选课记录。"

    # 按星期几筛选
    if day_of_week is not None:
        courses = [c for c in courses if c.get("day") == day_of_week]
        if not courses:
            return f"学号为 {stu_num} 的同学在{DAY_NAMES[day_of_week]}没有课程。"

    # 按星期几分组
    grouped = {}
    for c in courses:
        d = c.get("day", 0)
        grouped.setdefault(d, []).append(c)

    lines = [f"📅 学号 {stu_num} 的课表："]
    for d in sorted(grouped.keys()):
        lines.append(f"\n  {DAY_NAMES[d]}：")
        for c in grouped[d]:
            lines.append(
                f"    📖 {c.get('course_name', '未知')} | "
                f"⏰ {c.get('start_time', '?')}-{c.get('end_time', '?')} | "
                f"📍 {c.get('room_id', '未知')} | "
                f"👨‍🏫 {c.get('teacher_name', '未知')} | "
                f"📆 第{c.get('week_start', '?')}-{c.get('week_end', '?')}周"
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
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询课程出错：{str(e)}"

    # 兼容不同后端返回的 key（Courses 或 courses）
    courses = data.get("Courses", data.get("courses", []))
    if not courses:
        filters = ", ".join(f"{k}={v}" for k, v in params.items())
        return f"未找到符合条件的课程（筛选条件：{filters or '无'}）。"

    lines = [f"📚 查询结果（共 {len(courses)} 门课程）："]
    for c in courses:
        d = c.get("day", 0)
        day_str = DAY_NAMES[d] if 1 <= d <= 7 else f"星期{d}"
        lines.append(
            f"  • [{c.get('course_id', '?')}] {c.get('course_name', '未知')} | "
            f"{day_str} {c.get('start_time', '?')}-{c.get('end_time', '?')} | "
            f"👨‍🏫 {c.get('teacher_name', '未知')} | "
            f"📍 {c.get('room_id', '未知')} | "
            f"📆 第{c.get('week_start', '?')}-{c.get('week_end', '?')}周 | "
            f"📝 {c.get('semester', '未知学期')}"
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
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询班级学生出错：{str(e)}"

    students = data.get("students", [])
    if not students:
        return "学校数据库中暂无学生数据。"

    # 按班级名称筛选（支持中文名和 class-id 两种格式）
    matched = [
        s for s in students
        if class_name in (s.get("Cls", "") or "")
    ]
    if not matched:
        available = sorted(set(s.get("Cls", "未知") for s in students))
        return f"未找到班级 '{class_name}' 的学生。数据库中的班级：{', '.join(available)}"

    lines = [f"🏫 班级 '{class_name}' 学生名单（共 {len(matched)} 人）："]
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
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
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

    lines = [f"👤 学生信息查询结果（共 {len(matched)} 人）："]
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
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
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

    lines = [f"🏢 教室查询结果（共 {len(matched)} 间）："]
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
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"未找到工号为 {teacher_num} 的教师，请确认工号是否正确。"
        return f"查询教师学生信息出错：{str(e)}"
    except Exception as e:
        return f"查询教师学生信息出错：{str(e)}"

    courses = data.get("courses", [])
    if not courses:
        teacher_name = data.get("teacher_name", teacher_num)
        return f"👨‍🏫 {teacher_name}（工号：{teacher_num}）目前没有授课安排。"

    teacher_name = data.get("teacher_name", "未知")
    lines = [f"👨‍🏫 {teacher_name}（工号：{teacher_num}）的授课情况（共 {data.get('count', len(courses))} 门课程）："]
    for course in courses:
        d = course.get("day", 0)
        day_str = DAY_NAMES[d] if 1 <= d <= 7 else f"星期{d}"
        lines.append(
            f"\n  📖 {course.get('course_name', '未知')} | "
            f"{day_str} {course.get('start_time', '?')}-{course.get('end_time', '?')} | "
            f"📍 {course.get('room_id', '未知')} | "
            f"📆 第{course.get('week_start', '?')}-{course.get('week_end', '?')}周"
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
            f"✅ 教室 {room_full} 在第{week}周 {day_str} "
            f"{start_time}-{end_time} 时段空闲，可以使用。"
        )
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            # 400 表示时间冲突，提取后端返回的冲突详情
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = str(e)
            room_full = f"{area}-{building}-{room_id}"
            day_str = DAY_NAMES[day] if 1 <= day <= 7 else f"星期{day}"
            return (
                f"❌ 教室 {room_full} 在第{week}周 {day_str} "
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
    # 第一步：获取课程选课学生学号列表
    try:
        resp = requests.get(
            f"{BACKEND_API_BASE}/api/class-stu/course/{course_id}",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"未找到课程编号为 {course_id} 的课程，请确认编号是否正确。"
        return f"查询课程学生出错：{str(e)}"
    except Exception as e:
        return f"查询课程学生出错：{str(e)}"

    stu_list = data.get("students", [])
    if not stu_list:
        return f"📖 课程 {course_id} 目前没有学生选课。"

    # 第二步：获取所有学生信息，补全姓名和班级
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

    lines = [f"📖 课程 {course_id} 选课学生名单（共 {len(stu_list)} 人）："]
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
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询教师列表出错：{str(e)}"

    teachers = data.get("teacher", [])
    if not teachers:
        return "学校数据库中暂无教师数据。"

    lines = [f"👨‍🏫 教师列表（共 {len(teachers)} 人）："]
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
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询选课记录出错：{str(e)}"

    enrollments = data.get("enrollments", [])
    if not enrollments:
        return "学校数据库中暂无选课记录。"

    lines = [f"📋 全部选课记录（共 {len(enrollments)} 条）："]
    for e in enrollments:
        lines.append(f"  • 课程：{e.get('course_id', '?')} → 学生学号：{e.get('stu_num', '?')}")
    return "\n".join(lines)


# ============================================================
# 待办管理工具（通过 Backend /api/todo/* 接口）
# ============================================================

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
        return f"✅ 待办添加成功！\n  📌 {todo.get('title')}\n  📅 {todo.get('date')} | 🏷 {todo.get('priority')} | 📋 {todo.get('status')}\n  ID: {todo.get('id')}"
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
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
        return f"🗑 已删除待办：{deleted.get('title', '未知')}（日期：{deleted.get('date', '?')}）"
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
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
            return f"📅 {who}{date} 暂无待办事项。"
        lines = [f"📅 {date} 待办事项（共 {len(todos)} 个）："]
        for t in todos:
            icon = {"pending": "⬜", "in_progress": "🔄", "completed": "✅"}.get(t.get("status"), "❓")
            lines.append(
                f"  {icon} [{t.get('id')}] {t.get('title')} | "
                f"🏷 {t.get('priority', '?')} | "
                f"👤 {t.get('user_id', '?')}"
            )
        return "\n".join(lines)
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
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
            return f"👤 {user_id} 暂无待办事项。"
        lines = [f"👤 {user_id} 的待办事项（共 {len(todos)} 个）："]
        for t in todos:
            icon = {"pending": "⬜", "in_progress": "🔄", "completed": "✅"}.get(t.get("status"), "❓")
            lines.append(
                f"  {icon} [{t.get('id')}] {t.get('title')} | "
                f"📅 {t.get('date')} | 🏷 {t.get('priority', '?')}"
            )
        return "\n".join(lines)
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
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
        icon = {"pending": "⬜", "in_progress": "🔄", "completed": "✅"}.get(status, "❓")
        return f"{icon} 待办 [{todo_id}]「{todo.get('title', '?')}」状态已更新为：{status}"
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
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
            f"📊 {user_id} 的待办统计：",
            f"  📋 总计：{stats.get('total', 0)} 个",
            f"  ⬜ 待办：{stats.get('pending', 0)} 个",
            f"  🔄 进行中：{stats.get('in_progress', 0)} 个",
            f"  ✅ 已完成：{stats.get('completed', 0)} 个",
            f"  📅 今日待办：{stats.get('today', 0)} 个",
            f"  ⚠️ 逾期未完成：{stats.get('overdue', 0)} 个",
        ]
        return "\n".join(lines)
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"获取待办统计出错：{str(e)}"


# ============================================================
# 图书馆座位管理工具（通过 Backend /api/library/* 接口）
# ============================================================

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
            f"✅ 预约成功！\n"
            f"  🪑 座位：{r.get('seat_id')}\n"
            f"  📅 日期：{r.get('date')}\n"
            f"  ⏰ 时间：{r.get('start_time')}-{r.get('end_time')}\n"
            f"  🔢 预约编号：{r.get('id')}"
        )
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
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
        return f"🗑 预约已取消：座位 {r.get('seat_id')}，{r.get('date')} {r.get('start_time')}-{r.get('end_time')}"
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"取消预约出错：{str(e)}"


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
            return f"👤 {user_id} 暂无预约记录。"
        lines = [f"📋 {user_id} 的预约记录（共 {len(reservations)} 条）："]
        for r in reservations:
            icon = {"reserved": "✅", "cancelled": "❌", "completed": "✔️"}.get(r.get("status"), "❓")
            lines.append(
                f"  {icon} [{r.get('id')}] {r.get('seat_id')} | "
                f"{r.get('date')} {r.get('start_time')}-{r.get('end_time')} | "
                f"{r.get('status')}"
            )
        return "\n".join(lines)
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
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

        lines = ["🪑 图书馆座位状态："]
        for key, s in stats.items():
            lines.append(
                f"  📍 {key}：可用 {s.get('available', 0)} / 已预约 {s.get('reserved', 0)} "
                f"（共 {s.get('total', 0)} 座）"
            )

        # 列出前20个座位详情
        lines.append(f"\n📋 座位详情（显示前20个，共 {len(seats)} 个）：")
        for seat in seats[:20]:
            icon = "🟢" if seat.get("status") == "available" else "🔴"
            lines.append(f"  {icon} {seat.get('seat_id')} | {seat.get('area')}区 {seat.get('floor')}F | {seat.get('status')}")
        if len(seats) > 20:
            lines.append(f"  ... 还有 {len(seats) - 20} 个座位")
        return "\n".join(lines)
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
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

        lines = [f"🕐 {date} {start_time}-{end_time} 可用座位："]
        if not available:
            lines.append("  😞 该时段暂无可用座位，请尝试其他时间段。")
        else:
            lines.append(f"  🟢 可用 {len(available)} 个 / 🔴 已占用 {unavailable_count} 个")
            lines.append("")
            # 按区域分组
            by_area = {}
            for s in available:
                by_area.setdefault(s.get("area", "?"), []).append(s.get("seat_id"))
            for a, seats in by_area.items():
                lines.append(f"  📍 {a}区（{len(seats)} 座）：{', '.join(seats[:10])}")
                if len(seats) > 10:
                    lines.append(f"       ... 还有 {len(seats) - 10} 个")
        return "\n".join(lines)
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到学校数据库服务，请确认 Backend 已启动。"
    except Exception as e:
        return f"查询可用座位出错：{str(e)}"


# ============================================================
# 创建 Agent（带 LangGraph MemorySaver 自动记忆）
# ============================================================

# ★ 核心：MemorySaver 是 LangGraph 内置的检查点机制
# 它会自动保存每个 thread（会话）的完整对话历史
# 不同 thread_id 之间的对话完全隔离，你无需写一行记忆管理代码！
checkpointer = MemorySaver()

tools = [
    get_weather, calculator, query_day_of_week, get_current_time,
    list_files, read_file, write_file,
    save_memory, recall_memory,
    markdown_to_html, markdown_to_pdf, use_python_pptx,
    query_student_schedule, query_course_info, query_class_students,
    query_student_info, query_room_info,
    query_teacher_students, query_free_room, query_course_students,
    query_all_teachers, query_all_enrollments,
    add_todo, delete_todo, query_todos_by_date, query_user_todos,
    update_todo_status, get_todo_stats,
    reserve_seat, cancel_reservation, get_user_reservations,
    get_seats_status, get_available_seats,
]

llm = ChatDeepSeek(
    model=MODEL_NAME,
    api_key=API_KEY,
    temperature=0.3,
)

# create_agent 返回一个 CompiledStateGraph
# 传入 checkpointer 即启用自动会话记忆
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)


# ============================================================
# 公开接口（供 API 层 / Backend 调用）
# ============================================================

# ---- 角色中英文映射 ----
ROLE_LABELS: Dict[str, str] = {
    "student": "学生",
    "teacher": "教师",
    "admin": "管理员",
}


def _build_user_context_message(
    message: str,
    username: Optional[str] = None,
    role: Optional[str] = None,
    user_id: Optional[str] = None,
    class_id: Optional[str] = None,
    class_ids: Optional[List[str]] = None,
) -> str:
    """构建带用户上下文的完整消息，将 UserContext 信息以 [用户信息] 前缀注入。

    Backend 传来的 UserContext 字段（均为可选），统一拼装为一行中文标签，
    帮助 LLM 感知当前对话对象的身份、班级等，从而提供差异化服务。
    """
    parts: List[str] = []
    if username:
        parts.append(f"姓名：{username}")
    if role:
        label = ROLE_LABELS.get(role, role)
        parts.append(f"身份：{label}")
    if user_id:
        parts.append(f"ID：{user_id}")
    if class_id:
        parts.append(f"班级：{class_id}")
    if class_ids:
        parts.append(f"班级列表：{', '.join(class_ids)}")

    if not parts:
        return message

    prefix = "[用户信息] " + " | ".join(parts)
    return f"{prefix}\n{message}"


def chat(session_id: str, message: str, username: Optional[str] = None, role: Optional[str] = None, user_id: Optional[str] = None, class_id: Optional[str] = None, class_ids: Optional[List[str]] = None) -> str:
    """执行一次对话，返回 Agent 回复。
    
    Args:
        session_id: 会话 ID。同一 ID 共享对话历史，不同 ID 完全隔离。
        message: 用户消息
        username: 可选，用户名（Agent 可据此使用长期记忆工具）
        role: 可选，用户身份（student / teacher / admin）
        user_id: 可选，用户唯一标识
        class_id: 可选，单个班级 ID
        class_ids: 可选，多个班级 ID 列表
    
    Returns:
        Agent 的回复文本
    """
    message = _build_user_context_message(message, username, role, user_id, class_id, class_ids)

    result = agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config={
            "configurable": {"thread_id": session_id},
            "callbacks": [ToolCallHandler()],
        },
    )
    return result["messages"][-1].content


async def chat_stream(session_id: str, message: str, username: Optional[str] = None, role: Optional[str] = None, user_id: Optional[str] = None, class_id: Optional[str] = None, class_ids: Optional[List[str]] = None):
    """流式对话，逐事件产出 Agent 状态。

    使用 agent.astream_events() 获取 LLM token 流、工具调用/结果等事件，
    通过状态机区分 reasoning → calling_tool → responding → done 四个阶段，
    以 dict 流的形式产出，供 API 层转为 SSE 推送给前端。

    Args:
        session_id: 会话 ID
        message: 用户消息
        username: 可选，用户名
        role: 可选，用户身份（student / teacher / admin）
        user_id: 可选，用户唯一标识
        class_id: 可选，单个班级 ID
        class_ids: 可选，多个班级 ID 列表

    Yields:
        {"event": "status", "data": {"phase": "...", "message": "..."}}
        {"event": "token", "data": {"content": "...", "phase": "reasoning"|"responding"}}
        {"event": "tool_call", "data": {"name": "...", "args": {...}}}
        {"event": "tool_result", "data": {"name": "...", "result": "...", "success": true}}
        {"event": "error", "data": {"message": "...", "phase": "..."}}
        {"event": "done", "data": {"session_id": "..."}}
    """
    import traceback

    message = _build_user_context_message(message, username, role, user_id, class_id, class_ids)

    # ---- 内部状态机 ----
    phase: str = "reasoning"          # reasoning | calling_tool | responding | done
    has_pending_tools: bool = False   # 上一轮 LLM 是否产出了工具调用

    try:
        yield {"event": "status", "data": {"phase": "reasoning", "message": "正在思考..."}}

        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=message)]},
            config={"configurable": {"thread_id": session_id}},
            version="v2",
        ):
            kind = event["event"]

            # ================================================================
            # LLM 流式输出 token
            # ================================================================
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]

                # --- 提取 reasoning_content（DeepSeek 推理过程） ---
                reasoning = None
                if hasattr(chunk, "additional_kwargs") and chunk.additional_kwargs:
                    reasoning = chunk.additional_kwargs.get("reasoning_content", "")
                # 兼容某些实现把 reasoning 放在 content 之前
                if not reasoning:
                    reasoning = getattr(chunk, "reasoning_content", None)

                if reasoning and isinstance(reasoning, str):
                    yield {"event": "token", "data": {"content": reasoning, "phase": "reasoning"}}

                # --- 提取正文 content ---
                chunk_content = getattr(chunk, "content", "")
                if isinstance(chunk_content, list):
                    chunk_content = "".join(
                        b.get("text", "") if isinstance(b, dict) else str(b)
                        for b in chunk_content
                    )

                if chunk_content and isinstance(chunk_content, str):
                    if phase == "reasoning" and not has_pending_tools:
                        phase = "responding"
                        yield {"event": "status", "data": {"phase": "responding", "message": "正在生成回复..."}}
                    yield {"event": "token", "data": {"content": chunk_content, "phase": phase}}

                # --- 检测工具调用（chunk 中有 tool_call_chunks 且无正文 → 工具调用中） ---
                tcc = getattr(chunk, "tool_call_chunks", None) or []
                if tcc and not chunk_content and not reasoning:
                    if phase != "calling_tool":
                        phase = "calling_tool"

            # ================================================================
            # 工具开始执行
            # ================================================================
            elif kind == "on_tool_start":
                phase = "calling_tool"
                has_pending_tools = True
                tool_name = event.get("name", "unknown")
                raw_input = event["data"].get("input", {})
                # 清洗参数（截断过长值）
                if isinstance(raw_input, dict):
                    clean_args = {}
                    for k, v in raw_input.items():
                        s = str(v)
                        clean_args[k] = s[:200] + "..." if len(s) > 200 else s
                else:
                    clean_args = str(raw_input)[:200]

                yield {"event": "status", "data": {"phase": "calling_tool", "message": f"正在调用工具: {tool_name}"}}
                yield {"event": "tool_call", "data": {"name": tool_name, "args": clean_args}}

            # ================================================================
            # 工具执行完成
            # ================================================================
            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                raw_output = str(event["data"].get("output", ""))
                # 截断过长结果
                result_text = raw_output[:500] + "..." if len(raw_output) > 500 else raw_output
                yield {"event": "tool_result", "data": {"name": tool_name, "result": result_text, "success": True}}

                # ★ 检测文件生成工具，产出 file_ready 事件供前端渲染下载卡片
                if tool_name in ("write_file", "markdown_to_pdf"):
                    file_info = _extract_file_info(tool_name, raw_output)
                    if file_info:
                        yield {"event": "file_ready", "data": file_info}

                # 回归 reasoning，等待 LLM 分析工具结果
                phase = "reasoning"
                has_pending_tools = False
                yield {"event": "status", "data": {"phase": "reasoning", "message": "正在分析工具结果..."}}

            # ================================================================
            # LLM 单次调用结束（可忽略，仅用于调试）
            # ================================================================
            elif kind == "on_chat_model_end":
                pass

        # ---- 流正常结束 ----
        yield {"event": "status", "data": {"phase": "done", "message": "完成"}}
        yield {"event": "done", "data": {"session_id": session_id}}

    except Exception as e:
        yield {"event": "error", "data": {"message": str(e), "phase": phase}}
        yield {"event": "done", "data": {"session_id": session_id, "error": str(e)}}


def get_history(session_id: str) -> List[Dict[str, str]]:
    """获取指定会话的对话历史。
    
    Args:
        session_id: 会话 ID
    
    Returns:
        [{"role": "user"|"assistant", "content": "..."}, ...]
    """
    try:
        state = agent.get_state(config={"configurable": {"thread_id": session_id}})
        if state is None or not state.values:
            return []
        messages = state.values.get("messages", [])
        return [
            {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
            for m in messages
        ]
    except Exception:
        return []


def clear_history(session_id: str) -> bool:
    """清除指定会话的对话历史（长期记忆不受影响）。"""
    try:
        agent.invoke(
            {"messages": []},
            config={"configurable": {"thread_id": session_id}},
        )
        return True
    except Exception:
        return False


def get_user_memory(username: str, key: Optional[str] = None) -> Dict[str, Any]:
    """获取用户的长期记忆。"""
    if key:
        return {"username": username, "key": key, "value": memory_store.get(username, key)}
    return {"username": username, "memory": memory_store.get_all(username)}


def update_user_memory(username: str, key: str, value: str) -> Dict[str, Any]:
    """更新用户的长期记忆。"""
    memory_store.set(username, key, value)
    return {"username": username, "key": key, "value": value, "status": "saved"}


def delete_user_memory(username: str, key: Optional[str] = None) -> Dict[str, Any]:
    """删除用户长期记忆。不指定 key 则清空全部。"""
    memory_store.delete(username, key)
    return {"username": username, "key": key, "status": "deleted"}


def _extract_file_info(tool_name: str, output: str) -> Optional[dict]:
    """从工具输出中提取文件元数据，供 file_ready SSE 事件使用。

    支持的输出格式：
        write_file      → "已将内容写入文件：notes.txt"
        markdown_to_pdf → "已将 Markdown 转换为 PDF: C:\\...\\workspace\\output.pdf"

    Returns:
        {"name", "path", "size", "size_formatted", "modified_at"} 或 None
    """
    file_path = None

    if tool_name == "markdown_to_pdf":
        match = re.search(r'PDF:\s*(.+)$', output)
        if match:
            file_path = Path(match.group(1).strip())

    elif tool_name == "write_file":
        match = re.search(r'写入文件[：:]\s*(.+)$', output)
        if match:
            file_path = (WORKSPACE_DIR / match.group(1).strip()).resolve()

    if file_path and file_path.exists() and file_path.is_file():
        # 安全检查：确保在工作区范围内
        if not str(file_path.resolve()).startswith(str(WORKSPACE_DIR.resolve())):
            return None
        stat = file_path.stat()
        return {
            "name": file_path.name,
            "path": str(file_path.relative_to(WORKSPACE_DIR)),
            "size": stat.st_size,
            "size_formatted": _format_size(stat.st_size),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    return None


def _format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ============================================================
# 直接运行时的测试
# ============================================================

if __name__ == "__main__":

    def test(label: str, sid: str, msg: str, uname: str = "测试用户"):
        print(f"\n--- {label} ---")
        print(f"[User] {msg}")
        reply = chat(sid, msg, username=uname)
        print(f"[Agent] {reply}")

    test("天气查询", "s1", "北京今天天气怎么样？")
    test("安全计算", "s1", "帮我算一下 sqrt(256) + 10 * 3")
    test("保存课表", "s1", "请记住我的课表：周一数学，周二英语，周三计算机")
    test("回忆课表", "s1", "我之前说的课表是什么？")
    test("会话隔离", "s2", "我之前说了什么？你还记得吗？")

    history = get_history("s1")
    print(f"\n--- 会话 s1 共 {len(history)} 条消息 ---")

    print("\n✅ 测试完成！启动 API 服务请运行: python api.py")

