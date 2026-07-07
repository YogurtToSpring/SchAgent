"""
SchAgent Backend 异步后端服务
=============================
基于 FastAPI + httpx 的异步后端，代理 LangChain API 并向 Vue 前端提供接口。

与 example.py 的区别：
1. ★ 全面异步（httpx.AsyncClient 替代 requests）
2. ★ SSE 流式代理（POST /api/chat/stream）
3. ★ 文件下载代理
4. ★ CORS 支持（供前端跨域访问）

架构：
    Vue 前端 → Backend (本文件) → HTTP → LangChain API (api.py) → Agent → DeepSeek

启动方式：
    uvicorn main:app --host 0.0.0.0 --port 8080 --reload
"""

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn

# ============================================================
# 配置
# ============================================================

AGENT_API_BASE = "http://localhost:8000"

app = FastAPI(
    title="SchAgent Backend",
    description="校园生活智能助手后端服务 - 异步代理层",
    version="2.0.0",
)

# 全局异步 HTTP 客户端（连接池复用）
client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))


# ============================================================
# 请求 / 响应模型
# ============================================================

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    message: str = Field(..., description="用户消息")
    username: Optional[str] = Field(None, description="用户名（用于长期记忆）")


class ChatResponse(BaseModel):
    session_id: str
    response: str


class MemoryRequest(BaseModel):
    key: str = Field(..., description="记忆键名")
    value: str = Field(..., description="记忆内容")


# ============================================================
# 健康检查
# ============================================================

@app.get("/health")
async def health():
    """健康检查（同时检测 Agent API 是否可达）"""
    agent_status = "unknown"
    try:
        resp = await client.get(f"{AGENT_API_BASE}/health", timeout=5.0)
        agent_status = "ok" if resp.status_code == 200 else "error"
    except Exception:
        agent_status = "unreachable"
    return {
        "status": "ok",
        "service": "SchAgent Backend",
        "version": "2.0.0",
        "agent_api": agent_status,
    }


# ============================================================
# 对话接口
# ============================================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """同步对话 —— 发送消息并等待完整回复"""
    payload = {"session_id": request.session_id, "message": request.message}
    if request.username:
        payload["username"] = request.username

    try:
        resp = await client.post(f"{AGENT_API_BASE}/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(session_id=data["session_id"], response=data["response"])
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="⚠️ 无法连接到 Agent 服务，请确认 api.py 已启动")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Agent 返回错误：{e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"调用 Agent 出错：{str(e)}")


@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """流式对话（SSE 代理） —— 实时推送 Agent 思考过程、工具调用、回复 token

    直接透传 Agent API 的 SSE 流，前端可使用 fetch + ReadableStream 消费。
    """
    payload = {"session_id": request.session_id, "message": request.message}
    if request.username:
        payload["username"] = request.username

    async def sse_proxy():
        try:
            async with client.stream("POST", f"{AGENT_API_BASE}/chat/stream", json=payload) as resp:
                if resp.status_code != 200:
                    error_text = await resp.aread()
                    yield f"event: error\ndata: {{\"message\": \"Agent API 返回 {resp.status_code}: {error_text.decode()}\"}}\n\n"
                    yield f"event: done\ndata: {{\"session_id\": \"{request.session_id}\", \"error\": \"upstream_error\"}}\n\n"
                    return
                async for line in resp.aiter_lines():
                    if line:
                        yield line + "\n"
        except httpx.ConnectError:
            yield f"event: error\ndata: {{\"message\": \"无法连接到 Agent 服务\"}}\n\n"
            yield f"event: done\ndata: {{\"session_id\": \"{request.session_id}\", \"error\": \"connect_error\"}}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {{\"message\": \"{str(e)}\"}}\n\n"
            yield f"event: done\ndata: {{\"session_id\": \"{request.session_id}\", \"error\": \"proxy_error\"}}\n\n"

    return StreamingResponse(
        sse_proxy(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ============================================================
# 对话历史
# ============================================================

@app.get("/api/history/{session_id}")
async def get_chat_history(session_id: str):
    """获取会话对话历史"""
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
    """清除会话历史"""
    try:
        resp = await client.delete(f"{AGENT_API_BASE}/history/{session_id}")
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="无法连接到 Agent 服务")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


# ============================================================
# 长期记忆
# ============================================================

@app.get("/api/memory/{username}")
async def read_memory(username: str, key: Optional[str] = Query(None)):
    """获取用户长期记忆"""
    url = f"{AGENT_API_BASE}/memory/{username}"
    if key:
        url += f"?key={key}"
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="无法连接到 Agent 服务")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.put("/api/memory/{username}")
async def write_memory(username: str, request: MemoryRequest):
    """更新用户长期记忆"""
    try:
        resp = await client.put(
            f"{AGENT_API_BASE}/memory/{username}",
            json={"key": request.key, "value": request.value},
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="无法连接到 Agent 服务")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.delete("/api/memory/{username}")
async def delete_memory(username: str, key: Optional[str] = Query(None)):
    """删除用户长期记忆"""
    url = f"{AGENT_API_BASE}/memory/{username}"
    if key:
        url += f"?key={key}"
    try:
        resp = await client.delete(url)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="无法连接到 Agent 服务")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


# ============================================================
# 文件服务（代理 Agent 工作区文件下载）
# ============================================================

@app.get("/api/files")
async def list_files():
    """获取工作区可下载文件列表"""
    try:
        resp = await client.get(f"{AGENT_API_BASE}/files")
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="无法连接到 Agent 服务")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.get("/api/files/{file_name}")
async def download_file(file_name: str):
    """下载工作区文件 —— 流式代理，大文件不占内存"""
    async def file_stream():
        async with client.stream("GET", f"{AGENT_API_BASE}/files/{file_name}") as resp:
            if resp.status_code != 200:
                error_text = await resp.aread()
                raise HTTPException(status_code=resp.status_code, detail=error_text.decode())
            async for chunk in resp.aiter_bytes(chunk_size=65536):
                yield chunk

    return StreamingResponse(
        file_stream(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Access-Control-Allow-Origin": "*",
        },
    )


# ============================================================
# CORS 预检（OPTIONS 请求）
# ============================================================

@app.options("/{rest_of_path:path}")
async def preflight_handler():
    """处理 CORS 预检请求"""
    return {}  # 实际 CORS 建议用 fastapi.middleware.cors


# ============================================================
# 应用关闭时清理
# ============================================================

@app.on_event("shutdown")
async def shutdown():
    await client.aclose()


# ============================================================
# 启动入口
# ============================================================

if __name__ == "__main__":
    print("=" * 55)
    print("  SchAgent Backend 启动中...")
    print(f"  Agent API: {AGENT_API_BASE}")
    print("  监听端口: 8080")
    print("=" * 55)
    uvicorn.run("example-Backend-LangChain:app", host="0.0.0.0", port=8080, reload=True)
