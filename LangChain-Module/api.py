"""
SchAgent FastAPI 接口层
=======================
向外提供 REST API，供 Backend 或其他服务调用。

启动方式：
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload

接口列表：
    GET  /health              → 健康检查
    POST /chat                → 发送消息，获取 Agent 回复（同步）
    POST /chat/stream         → 发送消息，SSE 流式获取 Agent 状态
    GET  /history/{session_id} → 获取会话对话历史
    DELETE /history/{session_id} → 清除会话历史
    GET  /memory/{username}    → 获取用户长期记忆
    PUT  /memory/{username}    → 更新用户长期记忆
    DELETE /memory/{username}  → 删除用户长期记忆
    GET  /files/{file_name}    → 下载工作区文件（Agent 生成的 PDF 等）
    GET  /files                → 列出工作区可下载文件
"""

import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import uvicorn

# 从同目录的 main 模块导入核心函数
from main import (
    chat as agent_chat,
    chat_stream,
    get_history,
    clear_history,
    get_user_memory,
    update_user_memory,
    delete_user_memory,
    WORKSPACE_DIR,
)

app = FastAPI(
    title="SchAgent API",
    description="校园生活智能助手 API - 基于 LangGraph + DeepSeek",
    version="2.0.0",
)


# ============================================================
# 请求 / 响应模型
# ============================================================

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID，同一 ID 共享对话历史", examples=["user123-session1"])
    message: str = Field(..., description="用户消息", examples=["今天天气怎么样？"])
    username: Optional[str] = Field(None, description="可选，用户名（用于长期记忆）", examples=["张三"])
    role: Optional[str] = Field(None, description="可选，用户身份（student / teacher / admin）", examples=["student"])
    user_id: Optional[str] = Field(None, description="可选，用户唯一标识", examples=["2024001"])
    class_id: Optional[str] = Field(None, description="可选，单个班级 ID", examples=["class-001"])
    class_ids: Optional[List[str]] = Field(None, description="可选，多个班级 ID 列表", examples=[["class-001", "class-002"]])


class ChatResponse(BaseModel):
    session_id: str
    response: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: list
    count: int


class MemoryRequest(BaseModel):
    key: str = Field(..., description="记忆键名", examples=["schedule"])
    value: str = Field(..., description="记忆内容", examples=["周一数学 9:00-10:30"])


class MemoryResponse(BaseModel):
    username: str
    key: Optional[str] = None
    value: Optional[str] = None
    memory: Optional[dict] = None
    status: Optional[str] = None


# ============================================================
# API 端点
# ============================================================

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "SchAgent", "version": "2.0.0"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """发送消息给 Agent，获取回复（同步模式）。
    
    同一 session_id 的多次请求会共享对话历史（LangGraph 自动管理）。
    不同 session_id 之间完全隔离。
    如需流式输出（思考过程、工具调用等），请使用 /chat/stream。
    """
    try:
        reply = agent_chat(
            session_id=request.session_id,
            message=request.message,
            username=request.username,
            role=request.role,
            user_id=request.user_id,
            class_id=request.class_id,
            class_ids=request.class_ids,
        )
        return ChatResponse(session_id=request.session_id, response=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 处理出错：{str(e)}")


@app.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """流式对话端点（Server-Sent Events）。

    将 Agent 的全生命周期状态（思考 token、工具调用/结果、回复 token）
    以 SSE 格式实时推送给客户端。

    事件类型：status | token | tool_call | tool_result | error | done

    前端可使用 fetch + ReadableStream 消费（POST 不支持 EventSource）。
    """
    async def event_generator():
        async for event_data in chat_stream(
            session_id=request.session_id,
            message=request.message,
            username=request.username,
            role=request.role,
            user_id=request.user_id,
            class_id=request.class_id,
            class_ids=request.class_ids,
        ):
            event_type = event_data["event"]
            data_json = json.dumps(event_data["data"], ensure_ascii=False)
            yield f"event: {event_type}\ndata: {data_json}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/history/{session_id}", response_model=HistoryResponse)
async def conversation_history(session_id: str):
    """获取指定会话的对话历史"""
    messages = get_history(session_id)
    return HistoryResponse(session_id=session_id, messages=messages, count=len(messages))


@app.delete("/history/{session_id}")
async def clear_conversation(session_id: str):
    """清除指定会话的对话历史（长期记忆不受影响）"""
    ok = clear_history(session_id)
    if not ok:
        raise HTTPException(status_code=500, detail="清除历史失败")
    return {"session_id": session_id, "status": "cleared"}


@app.get("/memory/{username}", response_model=MemoryResponse)
async def read_memory(username: str, key: Optional[str] = Query(None)):
    """获取用户的长期记忆。不指定 key 则返回全部。"""
    data = get_user_memory(username, key)
    return MemoryResponse(**data)


@app.put("/memory/{username}", response_model=MemoryResponse)
async def write_memory(username: str, request: MemoryRequest):
    """更新用户的长期记忆"""
    result = update_user_memory(username, request.key, request.value)
    return MemoryResponse(**result)


@app.delete("/memory/{username}")
async def delete_memory(username: str, key: Optional[str] = Query(None)):
    """删除用户的长期记忆。不指定 key 则清空全部。"""
    result = delete_user_memory(username, key)
    return MemoryResponse(**result)


# ============================================================
# 文件服务端点（供 Backend 下载 Agent 生成的文件）
# ============================================================

@app.get("/files")
async def list_workspace_files():
    """列出工作区中所有可下载的文件"""
    items = []
    try:
        for f in WORKSPACE_DIR.iterdir():
            if f.is_file():
                items.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "url": f"/files/{f.name}",
                })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出文件出错：{str(e)}")
    return {"files": items}


@app.get("/files/{file_name}")
async def download_file(file_name: str):
    """下载工作区中 Agent 生成的文件（如 PDF）。

    由 markdown_to_pdf 等工具生成的文件存储在工作区目录，
    通过此端点可以下载到前端。
    """
    file_path = (WORKSPACE_DIR / file_name).resolve()
    # 安全检查：防止路径遍历攻击
    if not str(file_path).startswith(str(WORKSPACE_DIR.resolve())):
        raise HTTPException(status_code=403, detail="禁止访问工作区以外的文件")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"文件 '{file_name}' 不存在")
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"'{file_name}' 不是文件")
    return FileResponse(
        path=str(file_path),
        filename=file_name,
        media_type="application/octet-stream",
    )


# ============================================================
# 启动入口
# ============================================================

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
