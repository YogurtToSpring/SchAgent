"""
SchAgent Backend 校园生活智能助手后端
======================================
架构:
    Vue 前端 (A) -> Backend (B - 本文件) -> HTTP -> LangChain API (C - api.py) -> Agent -> DeepSeek

职责:
    1. 接收前端 POST /api/chat 请求（含 user_context, platform_context）
    2. 调用 C 的 POST /chat/stream (SSE) 获取 Agent 思考过程 + 工具调用 + 最终回复
    3. 将流式事件编译为前端期望的 { status, answer, steps, tool_calls, artifacts } 格式

启动方式:
    uvicorn main:app --host 0.0.0.0 --port 8080 --reload
"""
import uuid
import httpx
import json
from urllib.parse import quote
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn
from student import router as student_router
from course import router as course_router
from teacher import router as teacher_router
from admin import router as admin_router
from room import router as room_router
from class_stu import router as class_stu_router
from classi import router as classi_router
from classmate import router as classmate_router
from todo import router as todo_router
from grade import router as grade_router
from library import router as library_router

AGENT_API_BASE = "http://localhost:8000"

app = FastAPI(title="SchAgent Backend", description="校园生活智能助手后端服务 - 异步代理层", version="2.0.0")

app.include_router(student_router)
app.include_router(course_router)
app.include_router(teacher_router)
app.include_router(admin_router)
app.include_router(room_router)
app.include_router(class_stu_router)
app.include_router(classi_router)
app.include_router(classmate_router)
app.include_router(todo_router)
app.include_router(grade_router)
app.include_router(library_router)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))

class UserContext(BaseModel):
    user_id: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    class_id: Optional[str] = None
    class_ids: Optional[List[str]] = None

class PlatformContext(BaseModel):
    classes: Optional[List[Dict]] = None
    students: Optional[List[Dict]] = None
    courses: Optional[List[Dict]] = None
    weather: Optional[Dict] = None

class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="会话 ID，首次可为空")
    message: str = Field(..., description="用户消息")
    user_context: Optional[UserContext] = Field(None, description="用户上下文")
    platform_context: Optional[PlatformContext] = Field(None, description="平台上下文")

class ToolCallInfo(BaseModel):
    tool: str = ""
    label: str = ""
    status: str = "success"
    input: Optional[Any] = None
    output: Optional[Any] = None

class ArtifactItem(BaseModel):
    type: str = "table"
    title: Optional[str] = None
    columns: Optional[List[str]] = None
    rows: Optional[List[List]] = None

class ChatResponse(BaseModel):
    session_id: str
    status: str = "success"
    answer: str = ""
    steps: List[str] = []
    tool_calls: List[ToolCallInfo] = []
    artifacts: List[ArtifactItem] = []
    files: List[dict] = []
    missing_fields: Optional[List[str]] = None

TOOL_LABELS = {
    "get_weather": "天气查询",
    "calculator": "数学计算",
    "get_current_time": "时间查询",
    "list_files": "文件列表",
    "read_file": "读取文件",
    "write_file": "写入文件",
    "save_memory": "保存记忆",
    "recall_memory": "读取记忆",
    "markdown_to_html": "Markdown转HTML",
    "markdown_to_pdf": "Markdown转PDF",
    "share_files": "共享文件",
    "query_student_schedule": "课表查询",
    "query_course_info": "课程查询",
    "query_class_students": "班级查询",
    "query_student_info": "学生查询",
    "query_room_info": "教室查询",
    "add_todo": "添加待办",
    "delete_todo": "删除待办",
    "query_todos_by_date": "日期待办查询",
    "query_user_todos": "用户待办查询",
    "update_todo_status": "待办状态更新",
    "get_todo_stats": "待办统计",
    "reserve_seat": "预约座位",
    "cancel_reservation": "取消预约",
    "get_user_reservations": "预约记录查询",
    "get_seats_status": "座位状态查询",
    "get_available_seats": "可用座位查询",
}

async def call_agent_stream_collect(session_id: str, message: str, username: Optional[str] = None, role: Optional[str] = None, user_id: Optional[str] = None, class_id: Optional[str] = None, class_ids: Optional[List[str]] = None) -> ChatResponse:
    """
    调用 C 的 /chat/stream SSE 端点，收集所有事件，编译成前端期望的格式。
    这是 B 的核心翻译逻辑：
        C 的流式事件 -> B 收集整理 -> A 期望的结构化 JSON
    """
    payload = {"session_id": session_id, "message": message}
    if username:
        payload["username"] = username
    if role:
        payload["role"] = role
    if user_id:
        payload["user_id"] = user_id
    if class_id:
        payload["class_id"] = class_id
    if class_ids:
        payload["class_ids"] = class_ids

    collected_tokens = []
    collected_steps = []
    collected_tool_calls = []
    collected_files = []
    final_session_id = session_id
    error_message = None

    try:
        async with client.stream("POST", f"{AGENT_API_BASE}/chat/stream", json=payload) as resp:
            if resp.status_code != 200:
                error_text = await resp.aread()
                return ChatResponse(session_id=session_id, status="failed", answer=f"Agent API 返回 {resp.status_code}: {error_text.decode()}")
            event_type = ""
            async for line in resp.aiter_lines():
                if not line:
                    continue
                if line.startswith("event: "):
                    event_type = line[7:].strip()
                elif line.startswith("data: "):
                    data_str = line[6:].strip()
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    handle_sse_event(event_type, data, collected_steps, collected_tokens, collected_tool_calls, collected_files, user_id)
                    if event_type == "error":
                        error_message = data.get("message", "未知错误")
                    elif event_type == "done":
                        final_session_id = data.get("session_id", session_id)
    except httpx.ConnectError:
        return ChatResponse(session_id=session_id, status="failed", answer="无法连接到 Agent 服务。请先启动 LangChain API: cd LangChain-Module && python api.py")
    except Exception as e:
        return ChatResponse(session_id=session_id, status="failed", answer=f"调用 Agent 出错: {str(e)}")

    full_answer = "".join(collected_tokens)
    if not full_answer and error_message:
        full_answer = f"处理出错: {error_message}"
        status = "failed"
    elif not full_answer:
        full_answer = "Agent 未返回有效回答，请重试。"
        status = "failed"
    elif "?" in full_answer[:60] and any(kw in full_answer[:60] for kw in ["哪", "什么", "几", "如何", "吗", "呢"]):
        status = "need_clarification"
    else:
        status = "success"
    if not collected_steps:
        collected_steps = ["正在理解任务...", "正在生成回答..."]
    return ChatResponse(session_id=final_session_id, status=status, answer=full_answer, steps=collected_steps, tool_calls=collected_tool_calls, files=collected_files)

def handle_sse_event(event_type, data, collected_steps, collected_tokens, collected_tool_calls, collected_files, user_id=None):
    """处理单个 SSE 事件"""
    if event_type == "status":
        phase = data.get("phase", "")
        msg = data.get("message", "")
        if msg and phase in ("reasoning", "calling_tool", "responding"):
            collected_steps.append(msg)
    elif event_type == "token":
        content = data.get("content", "")
        if content:
            collected_tokens.append(content)
    elif event_type == "tool_call":
        name = data.get("name", "unknown")
        args = data.get("args", {})
        label = TOOL_LABELS.get(name, name)
        if isinstance(args, dict):
            clean_args = {}
            for k, v in args.items():
                s = str(v)
                clean_args[k] = s[:200] + "..." if len(s) > 200 else s
        else:
            clean_args = str(args)[:200]
        collected_tool_calls.append({"tool": name, "label": label, "status": "success", "input": clean_args, "output": None})
    elif event_type == "file_ready":
        user_param = f"?user_id={user_id}" if user_id else ""
        collected_files.append({
            "name": data.get("name", ""),
            "path": data.get("path", ""),
            "size": data.get("size", 0),
            "size_formatted": data.get("size_formatted", ""),
            "modified_at": data.get("modified_at", ""),
            "download_url": f"/api/files/{data.get("name", "")}{user_param}",
        })
    elif event_type == "tool_result":
        name = data.get("name", "")
        result = data.get("result", "")
        success = data.get("success", True)
        for tc in reversed(collected_tool_calls):
            if tc["tool"] == name and tc["output"] is None:
                tc["status"] = "success" if success else "failed"
                r = str(result)
                tc["output"] = r[:300] + "..." if len(r) > 300 else r
                break

@app.get("/health")
async def health():
    agent_status = "unknown"
    try:
        resp = await client.get(f"{AGENT_API_BASE}/health", timeout=5.0)
        agent_status = "ok" if resp.status_code == 200 else "error"
    except Exception:
        agent_status = "unreachable"
    return {"status": "ok", "service": "SchAgent Backend", "version": "2.0.0", "agent_api": agent_status}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """对话接口 - 接收前端请求，调用 LangChain Agent，返回结构化响应"""
    ctx = request.user_context
    username = ctx.name if ctx else None
    role = ctx.role if ctx else None
    user_id = ctx.user_id if ctx else None
    class_id = ctx.class_id if ctx else None
    class_ids = ctx.class_ids if ctx else None
    sid = request.session_id or str(uuid.uuid4())
    return await call_agent_stream_collect(
        session_id=sid, message=request.message,
        username=username, role=role,
        user_id=user_id, class_id=class_id, class_ids=class_ids,
    )

@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """SSE 流式对话 - 直接透传 LangChain Agent 的 SSE 事件"""
    ctx = request.user_context
    username = ctx.name if ctx else None
    role = ctx.role if ctx else None
    user_id = ctx.user_id if ctx else None
    class_id = ctx.class_id if ctx else None
    class_ids = ctx.class_ids if ctx else None
    sid = request.session_id or str(uuid.uuid4())
    payload = {"session_id": sid, "message": request.message}
    if username:
        payload["username"] = username
    if role:
        payload["role"] = role
    if user_id:
        payload["user_id"] = user_id
    if class_id:
        payload["class_id"] = class_id
    if class_ids:
        payload["class_ids"] = class_ids

    async def sse_proxy():
        try:
            async with client.stream("POST", f"{AGENT_API_BASE}/chat/stream", json=payload) as resp:
                if resp.status_code != 200:
                    error_text = await resp.aread()
                    yield f"event: error\ndata: {{\"message\": \"Agent API 返回 {resp.status_code}: {error_text.decode()}\"}}\n\n"
                    yield f"event: done\ndata: {{\"session_id\": \"{sid}\", \"error\": \"upstream_error\"}}\n\n"
                    return
                async for line in resp.aiter_lines():
                    if line:
                        yield line + "\n"
        except httpx.ConnectError:
            yield f"event: error\ndata: {{\"message\": \"无法连接到 Agent 服务\"}}\n\n"
            yield f"event: done\ndata: {{\"session_id\": \"{sid}\", \"error\": \"connect_error\"}}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {{\"message\": \"{str(e)}\"}}\n\n"
            yield f"event: done\ndata: {{\"session_id\": \"{sid}\", \"error\": \"proxy_error\"}}\n\n"

    return StreamingResponse(sse_proxy(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})

@app.get("/api/history/{session_id}")
async def get_chat_history(session_id: str):
    try:
        resp = await client.get(f"{AGENT_API_BASE}/history/{session_id}")
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="无法连接到 Agent 服务")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

@app.delete("/api/history/{session_id}")
async def clear_chat_history(session_id: str):
    try:
        resp = await client.delete(f"{AGENT_API_BASE}/history/{session_id}")
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="无法连接到 Agent 服务")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

@app.get("/api/memory/{username}")
async def read_memory(username: str, key: Optional[str] = None):
    url = f"{AGENT_API_BASE}/memory/{username}"
    if key:
        url += f"?key={key}"
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="无法连接到 Agent 服务")

@app.put("/api/memory/{username}")
async def write_memory(username: str, key: str, value: str):
    try:
        resp = await client.put(f"{AGENT_API_BASE}/memory/{username}", json={"key": key, "value": value})
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="无法连接到 Agent 服务")

@app.get("/api/files")
async def list_files(user_id: Optional[str] = Query(None, description="用户ID，透传给 Agent API")):
    try:
        params = {}
        if user_id:
            params["user_id"] = user_id
        resp = await client.get(f"{AGENT_API_BASE}/files", params=params)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="无法连接到 Agent 服务")


@app.get("/api/files/{file_name:path}")
async def download_file(file_name: str, user_id: Optional[str] = Query(None, description="用户ID，透传给 Agent API")):
    """下载 Agent 生成的文件（如 PDF），从 C 代理"""
    normalized_name = file_name.replace("\\", "/").strip("/")
    if not normalized_name or ".." in normalized_name.split("/"):
        raise HTTPException(status_code=400, detail="非法文件名")

    encoded_name = quote(normalized_name, safe="")
    display_name = normalized_name.split("/")[-1]
    encoded_display_name = quote(display_name)
    params = {}
    if user_id:
        params["user_id"] = user_id
    url = f"{AGENT_API_BASE}/files/{encoded_name}"
    try:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "application/octet-stream"),
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_display_name}",
            }
        )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="无法连接到 Agent 服务")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

@app.on_event("shutdown")
async def shutdown():
    await client.aclose()

if __name__ == "__main__":
    print("=" * 55)
    print("  SchAgent Backend 启动中...")
    print(f"  Agent API: {AGENT_API_BASE}")
    print("  监听端口: 8080")
    print("  前端地址: http://127.0.0.1:8080")
    print("=" * 55)
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
