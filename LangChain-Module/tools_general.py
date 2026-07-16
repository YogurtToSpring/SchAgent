import os
import sys
import math
import json
import shutil
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

from langchain.tools import tool

from tool_config import (
    WORKSPACE_DIR, _current_user_id, _get_user_workspace,
    _resolve_user_path, _format_size, memory_store,
)


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
        return " 天气服务暂时无法连接，请检查网络后重试。"
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 404:
            return f"未找到城市 '{city}' 的天气数据，请检查城市名称是否正确。"
        return f"查询天气失败（HTTP {resp.status_code}），请稍后重试。"
    except Exception as e:
        return f"查询天气出错：{str(e)}"

    if "code" in data and data["code"] != 200:
        return f"查询天气失败：{data.get('message', '未知错误')}"

    province = data.get("province", "")
    district = data.get("district", "")
    location = f"{province} {city}"
    if district:
        location += f" {district}"

    lines = [f"{location} 实时天气（{data.get('report_time', '')}）"]
    lines.append(f"天气：{data.get('weather', '未知')}")
    lines.append(f"温度：{data.get('temperature', '--')}°C"
                 f"（体感 {data.get('feels_like', '--')}°C）")
    lines.append(f"湿度：{data.get('humidity', '--')}%")
    lines.append(f"风力：{data.get('wind_direction', '--')} {data.get('wind_power', '--')}")

    aqi = data.get("aqi")
    if aqi is not None:
        aqi_level = data.get("aqi_category", "")
        primary = data.get("aqi_primary", "")
        lines.append(f"空气质量：AQI {aqi}（{aqi_level}）"
                     + (f"，主要污染物 {primary}" if primary else ""))

    vis = data.get("visibility")
    if vis:
        lines.append(f"能见度：{vis} km")
    uv = data.get("uv")
    if uv:
        uv_desc = "低" if uv < 3 else ("中等" if uv < 6 else ("高" if uv < 8 else "极高"))
        lines.append(f"紫外线：{uv}（{uv_desc}）")

    indices = data.get("life_indices", {})
    if indices:
        clothing = indices.get("clothing", {})
        if clothing:
            lines.append(f"穿衣建议：{clothing.get('advice', clothing.get('brief', ''))}")
        umbrella = indices.get("umbrella", {})
        if umbrella:
            lines.append(f"雨伞：{umbrella.get('brief', umbrella.get('advice', ''))}")
        exercise = indices.get("exercise", {})
        if exercise:
            lines.append(f"运动：{exercise.get('brief', exercise.get('advice', ''))}")

    alerts = data.get("alerts", [])
    if alerts:
        lines.append(f"\n气象预警 {len(alerts)}条：")
        for alert in alerts[:3]:
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

    weekday = date_obj.isoweekday()
    day_names = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return f"{date_str} 是 {day_names[weekday]}。"


@tool
def calculator(expression: str) -> str:
    """安全地执行数学计算。参数 expression 为数学表达式，支持 + - * / ** // % 及 sqrt/log/sin 等数学函数。例如 '3 + 5 * 2'、'sqrt(16) + 10'。"""
    allowed = {
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "log": math.log, "log10": math.log10, "log2": math.log2,
        "exp": math.exp, "abs": abs, "round": round, "pow": pow,
        "pi": math.pi, "e": math.e, "ceil": math.ceil, "floor": math.floor,
    }
    try:
        code = compile(expression, "<calculator>", "eval")
        for name in code.co_names:
            if name not in allowed and name not in dir(__builtins__):
                pass
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
        ws = _get_user_workspace()
        if not ws.exists():
            return "工作区目前没有文件。"
        items = os.listdir(ws)
        if not items:
            return "工作区目前没有文件。"
        lines = []
        for item in sorted(items):
            item_path = ws / item
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
    try:
        file_path = _resolve_user_path(file_name)
    except ValueError as e:
        return f"错误：{str(e)}"
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
    try:
        file_path = _resolve_user_path(file_name)
    except ValueError as e:
        return f"错误：{str(e)}"
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"已将内容写入文件：{file_name}"
    except Exception as e:
        return f"写入文件出错：{str(e)}"


@tool
def query_file_line(file_name: str, line_number: int) -> str:
    """查询工作区中指定文件的某一行内容。参数 file_name 为文件名称，line_number 为行号（从 1 开始）。"""
    try:
        file_path = _resolve_user_path(file_name)
    except ValueError as e:
        return f"错误：{str(e)}"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if line_number < 1 or line_number > len(lines):
            return f"行号 {line_number} 超出文件总行数 {len(lines)}。"
        return f"文件 '{file_name}' 的第 {line_number} 行内容：{lines[line_number - 1].rstrip()}"
    except FileNotFoundError:
        return f"文件 '{file_name}' 不存在。"
    except Exception as e:
        return f"查询文件行出错：{str(e)}"


@tool
def find_file_content(file_name: str, keyword: str) -> str:
    """在工作区中指定文件中查找包含关键字的行。参数 file_name 为文件名称，keyword 为要查找的关键字。"""
    try:
        file_path = _resolve_user_path(file_name)
    except ValueError as e:
        return f"错误：{str(e)}"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        matching_lines = [f"{i + 1}: {line.rstrip()}" for i, line in enumerate(lines) if keyword in line]
        if not matching_lines:
            return f"在文件 '{file_name}' 中未找到包含关键字 '{keyword}' 的行。"
        return f"在文件 '{file_name}' 中找到以下包含关键字 '{keyword}' 的行：\n" + "\n".join(matching_lines)
    except FileNotFoundError:
        return f"文件 '{file_name}' 不存在。"
    except Exception as e:
        return f"查找文件内容出错：{str(e)}"


@tool
def edit_file_line(file_name: str, line_number: int, new_content: str) -> str:
    """编辑工作区中指定文件的某一行内容。参数 file_name 为文件名称，line_number 为行号（从 1 开始），new_content 为新的行内容。"""
    try:
        file_path = _resolve_user_path(file_name)
    except ValueError as e:
        return f"错误：{str(e)}"
    try:
        if not file_path.exists():
            return f"文件 '{file_name}' 不存在。"
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if line_number < 1 or line_number > len(lines):
            return f"行号 {line_number} 超出文件总行数 {len(lines)}。"
        lines[line_number - 1] = new_content + '\n'
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return f"已将文件 '{file_name}' 的第 {line_number} 行修改为：{new_content}"
    except Exception as e:
        return f"编辑文件出错：{str(e)}"


@tool
def share_files(file_names: list) -> str:
    """将已生成的工作区文件共享给用户下载。

    重要：每当你使用 write_file、markdown_to_pdf 或 use_python_pptx 为用户生成了文件后，
    必须调用此工具来通知系统这些文件可供用户下载。

    参数 file_names: 要共享的文件名列表，如 ['report.pdf', 'slides.pptx']。
    文件名是相对于用户工作区的路径，只传文件名即可，不要传绝对路径。"""
    user_ws = _get_user_workspace()
    shared = []
    errors = []

    for name in file_names:
        try:
            resolved = (user_ws / name).resolve()
            if not str(resolved).startswith(str(WORKSPACE_DIR.resolve())):
                errors.append(f"{name}: 非法文件路径")
                continue
            if not resolved.exists():
                errors.append(f"{name}: 文件不存在")
                continue
            if not resolved.is_file():
                errors.append(f"{name}: 不是文件")
                continue
            stat = resolved.stat()
            shared.append({
                "name": resolved.name,
                "path": str(resolved.relative_to(WORKSPACE_DIR)),
                "size": stat.st_size,
                "size_formatted": _format_size(stat.st_size),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        except Exception as e:
            errors.append(f"{name}: {str(e)}")

    return json.dumps({"shared": shared, "errors": errors}, ensure_ascii=False)


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

        body_content = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code', 'codehilite'])

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

        pdf_path = _get_user_workspace() / output_file
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
    代码中已经预先import io/sys/traceback 模块和对象，
    注意：代码中禁止使用 os、sys、subprocess、shutil、importlib、__import__、
    open（仅允许 Presentation.save 内部使用）、eval、exec、compile 等危险操作。
    工作目录为 WORKSPACE_DIR，生成的文件请放在当前目录下。"""
    import io
    import sys
    import traceback

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
            return f" 安全检查未通过：代码中包含禁止的关键字 '{kw}'。请移除相关调用后重试。"

    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt, Emu
        import pptx
    except ImportError:
        return "PPTX 操作功能需要安装 'python-pptx' 库，请先运行 'pip install python-pptx'。"

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
        "WORKSPACE_DIR": _get_user_workspace(),
        "Path": Path,
    }
    safe_locals = {}

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    sys.stdout = captured_stdout
    sys.stderr = captured_stderr

    result = None
    try:
        original_cwd = os.getcwd()
        user_ws = _get_user_workspace()
        os.chdir(str(user_ws))

        try:
            exec(command, safe_globals, safe_locals)
            result = " PPTX 代码执行成功。"
        finally:
            os.chdir(original_cwd)
    except SyntaxError as e:
        result = f" Python 语法错误：{str(e)}"
    except Exception as e:
        result = f" 代码执行出错：{str(e)}\n\n详细堆栈：\n{traceback.format_exc()}"
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    stdout_output = captured_stdout.getvalue()
    stderr_output = captured_stderr.getvalue()

    parts = [result or " PPTX 代码执行完成。"]
    if stdout_output.strip():
        parts.append(f"--- 标准输出 ---\n{stdout_output.strip()}")
    if stderr_output.strip():
        parts.append(f"--- 标准错误 ---\n{stderr_output.strip()}")

    return "\n\n".join(parts)


@tool
def makedir(dir_name: str) -> str:
    """在工作区中创建一个新目录。参数 dir_name 为目录名称（如 'my_folder'）。"""
    try:
        dir_path = _resolve_user_path(dir_name)
        dir_path.mkdir(parents=True, exist_ok=True)
        return f"已创建目录：{dir_path}"
    except ValueError as e:
        return f"错误：{str(e)}"
    except Exception as e:
        return f"创建目录出错：{str(e)}"


@tool
def init_pptproject(project_name: str) -> str:
    """
    初始化 PPT 项目目录，在用户工作区下新建名为project_name的目录。
    目录内包括：
    sources          # 源文件（包含你根据主题生成的markdown文件）
    svg_output       # SVG 页面（待生成）
    exports          # PPTX 输出（由导出工具生成）
    该工具返回值为制作ppt的Skill字符串
    """
    try:
        dir_path = _resolve_user_path(project_name)
        dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return f"初始化项目目录出错：{str(e)}"
    return """
# PPT Master Agent — System Prompt

你是 **PPT Master Agent**，一个专业的 PPT 生成助手。你拥有文件读写能力和一个导出工具，其余全部凭你的设计能力完成。

---

## 核心规则（必须遵守）

1. **串行执行**：严格按下述 5 步顺序执行，不跳过、不预跑。
2. **spec_lock 是圣经**：生成每页 SVG 前重读 `spec_lock.md`，所有颜色/字体/字号以此为准。
3. **一次一页 SVG**：写完一页再写下一页，不批量生成。
4. **不用 emoji 之外的图标**：纯文字 PPT 用 emoji 点缀即可。
5. **不编造事实**：内容严格来自 sources/ 下的源材料。

---

## 工作流

### Step 1: 接收需求 & 准备内容

用户提供主题或源文件：

- 如果只是主题，用你的知识编写 Markdown 源文件

将源内容写入 `<project>/sources/<name>.md`。

### Step 2: 策略师设计

输出 **两个关键文件**——这是整个项目的设计蓝图：

#### 2a. `design_spec.md`（设计说明书）

```markdown
# {主题} - Design Spec

## I. Project Information
| 项目 | 值 |
|------|-----|
| 画布 | PPT 16:9 (1280×720) |
| 页数 | {N} |
| 受众 | {受众描述} |
| 用途 | {使用场景} |

## III. Visual Theme
- Mode: narrative（叙事流，适合故事/介绍类）
- Visual style: editorial（经典排版，大面积留白）
- 色调: {主色描述}

### Color Scheme（HEX 必填）
| 角色 | HEX | 用途 |
|------|-----|------|
| bg | #XXXXXX | 页面背景 |
| primary | #XXXXXX | 标题、强调 |
| accent | #XXXXXX | 重点装饰 |
| text | #2D2D2D | 正文 |
| text_secondary | #6B6B6B | 次要文字 |
| text_tertiary | #9B9B9B | 页码 |
| border | #XXXXXX | 分隔线 |

## IV. Typography
标题: Georgia, "Microsoft YaHei", serif
正文: "Microsoft YaHei", Arial, sans-serif
body: 24, title: 42, subtitle: 28, annotation: 18, footnote: 16, page_number: 16

## IX. Content Outline
| 页码 | 标题 | 内容要点 |
|------|------|---------|
| P01 | 封面 | ... |
| P02 | ... | ... |
```

#### 2b. `spec_lock.md`（执行锁——SVG 生成时的唯一数据源）

```markdown
## canvas
- viewBox: 0 0 1280 720
- format: PPT 16:9

## mode
- mode: narrative

## visual_style
- visual_style: editorial

## colors
- bg: #XXXXXX
- primary: #XXXXXX
- accent: #XXXXXX
- text: #2D2D2D
- text_secondary: #6B6B6B
- text_tertiary: #9B9B9B
- border: #XXXXXX

## typography
- font_family: "Microsoft YaHei", Arial, sans-serif
- title_family: Georgia, "Microsoft YaHei", serif
- body: 24
- title: 42
- subtitle: 28
- annotation: 18
- footnote: 16
- page_number: 16

## icons
- library: emoji

## images
```

### Step 3: 逐页生成 SVG

**每页之前**：重读 `spec_lock.md`。

**SVG 模板骨架**（直接套用）：

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <!-- 顶部 6px 色条 -->
  <rect x="0" y="0" width="1280" height="6" fill="[primary]"/>

  <!-- 标题 -->
  <text x="80" y="100" font-family="[title_family]" font-size="42" fill="[primary]" font-weight="bold">页面标题</text>
  <line x1="80" y1="120" x2="320" y2="120" stroke="[accent]" stroke-width="3"/>

  <!-- 正文 -->
  <text x="80" y="200" font-family="[font_family]" font-size="24" fill="[text]">
    <tspan x="80" dy="0">第一行</tspan>
    <tspan x="80" dy="38">第二行</tspan>
  </text>

  <!-- 页码 -->
  <text x="1200" y="700" text-anchor="end" font-family="[font_family]" font-size="16" fill="[text_tertiary]">01</text>
</svg>
```

**强制执行规范**（缺一不可）：

| 规则 | 说明                                                        |
| ---- | ----------------------------------------------------------- |
| 颜色 | 所有 fill/stroke 只用 spec_lock.colors 中的 HEX             |
| 字号 | 直接用 px 数字：`font-size="24"`（不带 px 后缀）          |
| 分行 | 正文用`<tspan x="..." dy="36~40">` 分行                   |
| 卡片 | 用`<rect rx="4" fill="[secondary_bg 或 primary]">` 做背景 |
| 装饰 | 用`<line>` `<circle>` `<rect>`，不用 filter/shadow    |
| 页码 | 每页右下角`x="1200" y="700"`                              |

**页面类型模板**：

- **封面**：左侧大面积深色区域 + 右侧名言，`font-size="64~72"` 大标题
- **内容页**：顶部色条 + 左标题 + 右/下正文，卡片辅助
- **名言页**：全幅深色背景 + 大号居中文字
- **结束页**：同封面风格，感谢语

### Step 4: 导出 PPTX

所有 SVG 生成完毕后，调用工具：

```
ppt_export(project_path="<project>")
```

---

## 配色速查

| 主题类型            | primary        | bg           | accent       |
| ------------------- | -------------- | ------------ | ------------ |
| 文学/历史/海洋   | #1B3A5C 深海蓝 | #F5F0E8 暖沙 | #C97B5D 珊瑚 |
| 科技/AI/代码     | #1565C0 科技蓝 | #FFFFFF 白   | #42A5F5 亮蓝 |
| 商业/金融/咨询   | #003366 海军蓝 | #FFFFFF 白   | #C8A951 金   |
| 自然/环保/健康   | #2E7D32 森林绿 | #FAFAF5 奶白 | #66BB6A 叶绿 |
| 创意/艺术/设计   | #1A1A1A 黑     | #FFFFFF 白   | #FFD600 明黄 |
| 历史/文化/传统   | #6D2727 赭红   | #FDF8F0 宣纸 | #B8860B 暗金 |
| 学术/教育/论文   | #1A3A5C 学术蓝 | #FFFFFF 白   | #C0392B 红   |

## 字号阶梯

| 角色                   | 16:9 (1280×720) |
| ---------------------- | ---------------- |
| cover_title            | 72               |
| title                  | 42               |
| subtitle               | 28               |
| lead                   | 26               |
| body                   | 24               |
| annotation             | 18               |
| footnote / page_number | 16               |

## 页面规划建议

- 总页数 8-12 页为佳
- 封面 + 结束各 1 页
- 书籍/电影介绍：背景 1-2 + 情节 3-4 + 主题 1-2
- 技术主题：概念 1 + 核心 3-4 + 案例 1-2 + 总结 1
- 每页 1-3 个信息点，不堆砌
"""


@tool
def ppt_export(project_path: str) -> str:
    """
    将项目 svg_output/ 目录下的 SVG 后处理并导出为 PPTX。

    前置条件：project_path 下已有 svg_output/ 含 SVG 页面文件。
    必须先完成: design_spec.md、spec_lock.md、所有 SVG 页面文件。
    参数 project_path 为项目目录名（相对于用户工作区的路径）。
    """
    from pathlib import Path as _Path

    user_ws = _get_user_workspace()
    project = (user_ws / project_path).resolve()
    if not str(project).startswith(str(WORKSPACE_DIR.resolve())):
        return f"[错误] 非法项目路径：{project_path}"

    scripts = _Path(__file__).resolve().parent / "pptmaster" / "scripts"

    svg_dir = project / "svg_output"
    if not svg_dir.is_dir():
        return f"[错误] 缺少 svg_output/ 目录: {svg_dir}"

    svg_files = sorted(svg_dir.glob("*.svg"))
    if not svg_files:
        return f"[错误] svg_output/ 下没有 .svg 文件"

    r1 = subprocess.run(
        [sys.executable, str(scripts / "finalize_svg.py"), str(project)],
        capture_output=True, text=True, timeout=120,
    )
    if r1.returncode != 0:
        return f"[错误] 后处理失败:\n{r1.stderr}"

    r2 = subprocess.run(
        [sys.executable, str(scripts / "svg_to_pptx.py"), str(project), "-q"],
        capture_output=True, text=True, timeout=180,
    )
    if r2.returncode != 0:
        return f"[错误] 导出失败:\n{r2.stderr}"

    exports = sorted((project / "exports").glob("*.pptx"))
    pptx = exports[-1] if exports else None

    if pptx is None:
        return f"[错误] 导出完成但在 exports/ 下未找到 .pptx 文件"

    dest = user_ws / pptx.name
    try:
        if dest.exists():
            dest.unlink()
        shutil.move(str(pptx), str(dest))
    except Exception as e:
        return f"[错误] 移动 PPTX 到工作区根目录失败: {e}"

    return f"[完成] {len(svg_files)} 页 → {pptx.name}"
