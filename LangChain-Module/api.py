"""
SchAgent FastAPI 接口层
=======================
向外提供 REST API，供 Backend 或其他服务调用。

启动方式：
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload

接口列表：
    GET  /health              → 健康检查
    POST /chat                → 发送消息，获取 Agent 回复
    GET  /history/{session_id} → 获取会话对话历史
    DELETE /history/{session_id} → 清除会话历史
    GET  /memory/{username}    → 获取用户长期记忆
    PUT  /memory/{username}    → 更新用户长期记忆
    DELETE /memory/{username}  → 删除用户长期记忆
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

# 从同目录的 main 模块导入核心函数
from main import (
    chat as agent_chat,
    get_history,
    clear_history,
    get_user_memory,
    update_user_memory,
    delete_user_memory,
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
    """发送消息给 Agent，获取回复。
    
    同一 session_id 的多次请求会共享对话历史（LangGraph 自动管理）。
    不同 session_id 之间完全隔离。
    """
    try:
        reply = agent_chat(
            session_id=request.session_id,
            message=request.message,
            username=request.username,
        )
        return ChatResponse(session_id=request.session_id, response=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 处理出错：{str(e)}")


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
# 启动入口
# ============================================================

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
