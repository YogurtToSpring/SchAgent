import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import uvicorn

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
    description="校园生活智能助手 API",
    version="2.0.0",
)

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


# API 端点
@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "SchAgent", "version": "2.0.0"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """同步模式"""
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
    """流式对话"""
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


# 文件服务端点（供 Backend 下载 Agent 生成的文件）

@app.get("/files")
async def list_workspace_files(user_id: Optional[str] = Query(None, description="用户ID，用于隔离工作区文件")):
    """列出工作区中所有可下载的文件。若提供 user_id 则仅列出该用户的文件。"""
    items = []
    try:
        if user_id:
            user_dir = WORKSPACE_DIR / user_id
            if user_dir.exists() and user_dir.is_dir():
                for f in user_dir.iterdir():
                    if f.is_file():
                        items.append({
                            "name": f.name,
                            "size": f.stat().st_size,
                            "url": f"/files/{f.name}?user_id={user_id}",
                        })
        else:
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
async def download_file(file_name: str, user_id: Optional[str] = Query(None, description="用户ID，用于隔离工作区文件")):
    """下载工作区中 Agent 生成的文件"""
    if user_id:
        file_path = (WORKSPACE_DIR / user_id / file_name).resolve()
    else:
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


# 启动入口

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
