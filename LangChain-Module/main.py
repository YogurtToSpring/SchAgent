import os
import json
import contextvars
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional, List, Dict, Any

from langchain_deepseek import ChatDeepSeek
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from langchain_core.callbacks import BaseCallbackHandler

from tool_config import (
    WORKSPACE_DIR, _current_user_id, _current_username,
    memory_store,
)
from tools_general import (
    get_weather, calculator, query_day_of_week, get_current_time,
    list_files, read_file, write_file, share_files,
    query_file_line, find_file_content, edit_file_line,
    save_memory, recall_memory,
    markdown_to_html, markdown_to_pdf, use_python_pptx,
    init_pptproject, ppt_export, makedir,
)
from tools_campus import (
    query_student_schedule, query_course_info, query_class_students,
    query_student_info, query_room_info,
    query_teacher_students, query_free_room, query_course_students,
    query_all_teachers, query_all_enrollments,
)
from tools_grade import (
    query_student_grades, query_course_grades, query_teacher_grades,
    query_all_grades,
)
from tools_todo import (
    add_todo, delete_todo, query_todos_by_date, query_user_todos,
    update_todo_status, get_todo_stats,
)
from tools_library import (
    reserve_seat, cancel_reservation, get_user_reservations,
    get_seats_status, get_available_seats,
)

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY")
MODEL_NAME = os.getenv("DEEPSEEK_MODEL")

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
- query_file_line: 查询工作区文件的指定行内容
- find_file_content: 在工作区文件中查找包含关键字的行
- edit_file_line: 编辑工作区文件的指定行内容
- list_files: 列出工作区目录下的内容
- save_memory: 保存用户的长期记忆（课表、偏好、笔记等）
- recall_memory: 读取用户的长期记忆
- markdown_to_html: 将 Markdown 文本转换为 HTML
- markdown_to_pdf: 将 Markdown 文本转换为 PDF 文件
- use_python_pptx: 使用 python-pptx 库操作 PPTX 文件（创建/编辑幻灯片）
- init_pptproject: 初始化 PPT 项目目录，返回 PPT 制作工作流指引
- ppt_export: 将项目 svg_output/ 下的 SVG 后处理并导出为 PPTX 文件
- share_files: 将生成的文件共享给用户下载（在 write_file / markdown_to_pdf / use_python_pptx / ppt_export 生成文件后必须调用）

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

## 成绩查询工具（从学校数据库获取真实成绩数据）：
- query_student_grades: 查询学生个人成绩（按学号 + 可选学期），返回各科平时/期末/总评、绩点、等级
- query_course_grades: 查询某门课程的全部学生成绩及统计信息（平均分/最高/最低/及格率）
- query_teacher_grades: 查询某位教师所教全部课程的成绩及统计信息
- query_all_grades: 查询全校全部成绩记录（管理员专用，可选学期筛选）

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
4. 对于需要制作PPT的请求，提供两种方案：
   a) **PPT Master 工作流**（推荐用于制作完整的演示文稿）：先调用 init_pptproject 初始化项目并获取制作指引，然后按照指引在项目 svg_output/ 目录下逐页生成 SVG 页面文件，全部页面完成后调用 ppt_export 导出为 PPTX，最后调用 share_files 共享导出的 PPTX 文件。
   b) **低阶 PPTX 操作**（适用于编辑已有 PPTX）：使用 use_python_pptx 工具直接操作 PPTX 文件，该工具已预导入 python-pptx 模块，直接使用预导入的对象即可。
5. ⚠️ 每当你使用 write_file、markdown_to_pdf、use_python_pptx 或 ppt_export 为用户生成了文件后，必须紧接着调用 share_files 工具将文件共享给用户，否则用户无法下载。share_files 接收一个 file_names 列表参数，传入你刚刚生成的文件名。
6. 如果不需要调用工具就直接生成回答
7. 回答简洁、友好

## 角色感知原则：
- 每条消息开头会附带 [用户信息] 块，包含当前用户的姓名、身份、班级等信息
- 不允许查询其他人的课程、课表、成绩等隐私信息
- 不随意调用查询数据库的tools，仅在用户明确查询**自己**的课表、课程、班级、学生、教室等信息时才使用
- 学生（student）：可查询个人课表、课程信息、个人成绩、同班同学，不允许查询其他班级或其他学生的隐私信息
- 教师（teacher）：可查询授课安排、所授课程成绩、班级学生名单、教室信息，不允许查询其他教师或非授课学生的隐私信息
- 管理员（admin）：可查询全部数据（含成绩），帮助进行系统管理和数据统计分析
- 使用 query_ 系列工具时，应优先利用用户信息中的班级、学号等限定查询范围，提高准确性

## 错误处理规则
- 若工具返回空结果，应告知用户"未查询到相关数据，请检查查询条件"
- 若工具调用失败，应重试一次，仍失败则提示"系统繁忙，请稍后重试"
- 不得编造数据库查询结果
"""


class ToolCallHandler(BaseCallbackHandler):
    def on_tool_start(self, serialized, input_str, **kwargs):
        print(f"[Tool] {serialized['name']}({input_str})")


tools = [
    get_weather, calculator, query_day_of_week, get_current_time,
    list_files, read_file, write_file, share_files,
    query_file_line, find_file_content, edit_file_line,
    save_memory, recall_memory,
    markdown_to_html, markdown_to_pdf, use_python_pptx,
    init_pptproject, ppt_export, makedir,
    query_student_schedule, query_course_info, query_class_students,
    query_student_info, query_room_info,
    query_teacher_students, query_free_room, query_course_students,
    query_all_teachers, query_all_enrollments,
    query_student_grades, query_course_grades, query_teacher_grades,
    query_all_grades,
    add_todo, delete_todo, query_todos_by_date, query_user_todos,
    update_todo_status, get_todo_stats,
    reserve_seat, cancel_reservation, get_user_reservations,
    get_seats_status, get_available_seats,
]

checkpointer = MemorySaver()

llm = ChatDeepSeek(
    model=MODEL_NAME,
    api_key=API_KEY,
    temperature=0.3,
)

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)


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
    message = _build_user_context_message(message, username, role, user_id, class_id, class_ids)

    _current_user_id.set(user_id or '')
    _current_username.set(username or '')

    result = agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config={
            "configurable": {"thread_id": session_id},
            "callbacks": [ToolCallHandler()],
            "recursion_limit": 10000,
        },
    )
    return result["messages"][-1].content


async def chat_stream(session_id: str, message: str, username: Optional[str] = None, role: Optional[str] = None, user_id: Optional[str] = None, class_id: Optional[str] = None, class_ids: Optional[List[str]] = None):
    import traceback

    message = _build_user_context_message(message, username, role, user_id, class_id, class_ids)

    _current_user_id.set(user_id or '')
    _current_username.set(username or '')

    phase: str = "reasoning"
    has_pending_tools: bool = False
    has_responded: bool = False

    try:
        yield {"event": "status", "data": {"phase": "reasoning", "message": "正在思考..."}}

        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=message)]},
            config={
                "configurable": {"thread_id": session_id},
                "recursion_limit": 10000,
            },
            version="v2",
        ):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]

                reasoning = None
                if hasattr(chunk, "additional_kwargs") and chunk.additional_kwargs:
                    reasoning = chunk.additional_kwargs.get("reasoning_content", "")
                if not reasoning:
                    reasoning = getattr(chunk, "reasoning_content", None)

                if reasoning and isinstance(reasoning, str):
                    yield {"event": "token", "data": {"content": reasoning, "phase": "reasoning"}}

                chunk_content = getattr(chunk, "content", "")
                if isinstance(chunk_content, list):
                    chunk_content = "".join(
                        b.get("text", "") if isinstance(b, dict) else str(b)
                        for b in chunk_content
                    )

                if chunk_content and isinstance(chunk_content, str):
                    if phase == "reasoning" and not has_pending_tools:
                        phase = "responding"
                        if has_responded:
                            yield {"event": "token", "data": {"content": "\n\n", "phase": "responding"}}
                        has_responded = True
                        yield {"event": "status", "data": {"phase": "responding", "message": "正在生成回复..."}}
                    yield {"event": "token", "data": {"content": chunk_content, "phase": phase}}

                tcc = getattr(chunk, "tool_call_chunks", None) or []
                if tcc and not chunk_content and not reasoning:
                    if phase != "calling_tool":
                        phase = "calling_tool"

            elif kind == "on_tool_start":
                phase = "calling_tool"
                has_pending_tools = True
                tool_name = event.get("name", "unknown")
                raw_input = event["data"].get("input", {})
                if isinstance(raw_input, dict):
                    clean_args = {}
                    for k, v in raw_input.items():
                        s = str(v)
                        clean_args[k] = s[:200] + "..." if len(s) > 200 else s
                else:
                    clean_args = str(raw_input)[:200]

                yield {"event": "status", "data": {"phase": "calling_tool", "message": f"正在调用工具: {tool_name}"}}
                yield {"event": "tool_call", "data": {"name": tool_name, "args": clean_args}}

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                output = event["data"].get("output", "")
                if hasattr(output, 'content'):
                    raw_output = str(output.content)
                else:
                    raw_output = str(output)
                result_text = raw_output[:500] + "..." if len(raw_output) > 500 else raw_output
                yield {"event": "tool_result", "data": {"name": tool_name, "result": result_text, "success": True}}

                if tool_name == "share_files":
                    try:
                        parsed = json.loads(raw_output)
                        current_uid = _current_user_id.get()
                        uid_param = f"?user_id={current_uid}" if current_uid else ""
                        for file_info in parsed.get("shared", []):
                            file_info["download_url"] = f"/api/files/{file_info['name']}{uid_param}"
                            yield {"event": "file_ready", "data": file_info}
                    except (json.JSONDecodeError, KeyError):
                        pass

                phase = "reasoning"
                has_pending_tools = False
                yield {"event": "status", "data": {"phase": "reasoning", "message": "正在分析工具结果..."}}

            elif kind == "on_chat_model_end":
                pass

        yield {"event": "status", "data": {"phase": "done", "message": "完成"}}
        yield {"event": "done", "data": {"session_id": session_id}}

    except Exception as e:
        yield {"event": "error", "data": {"message": str(e), "phase": phase}}
        yield {"event": "done", "data": {"session_id": session_id, "error": str(e)}}


def get_history(session_id: str) -> List[Dict[str, str]]:
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
    try:
        agent.invoke(
            {"messages": []},
            config={"configurable": {"thread_id": session_id}},
        )
        return True
    except Exception:
        return False


def get_user_memory(username: str, key: Optional[str] = None) -> Dict[str, Any]:
    if key:
        return {"username": username, "key": key, "value": memory_store.get(username, key)}
    return {"username": username, "memory": memory_store.get_all(username)}


def update_user_memory(username: str, key: str, value: str) -> Dict[str, Any]:
    memory_store.set(username, key, value)
    return {"username": username, "key": key, "value": value, "status": "saved"}


def delete_user_memory(username: str, key: Optional[str] = None) -> Dict[str, Any]:
    memory_store.delete(username, key)
    return {"username": username, "key": key, "status": "deleted"}


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

    print("\n 测试完成！启动 API 服务请运行: python api.py")
