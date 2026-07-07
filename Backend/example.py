"""
SchAgent Backend 后端服务
==========================
调用 LangChain 模块的 API，实现完整的后端逻辑。

运行方式：
    1. 先启动 LangChain API：cd LangChain-Module && python api.py
    2. 再启动 Backend：cd Backend && python main.py

架构：
    Frontend → Backend (本文件) → HTTP → LangChain API (api.py) → Agent (main.py) → DeepSeek
"""

import requests
import json

# LangChain API 地址
AGENT_API_BASE = "http://localhost:8000"


def call_agent(session_id: str, message: str, username: str = None) -> str:
    """调用 LangChain Agent 进行对话"""
    payload = {
        "session_id": session_id,
        "message": message,
    }
    if username:
        payload["username"] = username

    try:
        resp = requests.post(f"{AGENT_API_BASE}/chat", json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["response"]
    except requests.exceptions.ConnectionError:
        return "⚠️ 无法连接到 Agent 服务，请确认 api.py 已启动（python api.py）"
    except Exception as e:
        return f"⚠️ 调用 Agent 出错：{str(e)}"


def get_chat_history(session_id: str) -> list:
    """获取会话历史"""
    try:
        resp = requests.get(f"{AGENT_API_BASE}/history/{session_id}", timeout=10)
        resp.raise_for_status()
        return resp.json()["messages"]
    except Exception:
        return []


def clear_chat_history(session_id: str) -> bool:
    """清除会话历史"""
    try:
        resp = requests.delete(f"{AGENT_API_BASE}/history/{session_id}", timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def get_memory(username: str, key: str = None) -> dict:
    """获取用户长期记忆"""
    url = f"{AGENT_API_BASE}/memory/{username}"
    if key:
        url += f"?key={key}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def save_memory(username: str, key: str, value: str) -> dict:
    """保存用户长期记忆"""
    try:
        resp = requests.put(
            f"{AGENT_API_BASE}/memory/{username}",
            json={"key": key, "value": value},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# 业务逻辑示例
# ============================================================

def handle_user_message(user_id: str, message: str) -> dict:
    """处理用户消息的完整业务流程示例"""
    session_id = f"user-{user_id}"

    # 1. 调用 Agent 获取回复
    reply = call_agent(session_id, message, username=user_id)

    # 2. 获取对话历史（可用于前端展示）
    history = get_chat_history(session_id)

    return {
        "user_id": user_id,
        "session_id": session_id,
        "reply": reply,
        "message_count": len(history),
    }


if __name__ == "__main__":
    print("=" * 55)
    print("  SchAgent Backend 测试")
    print("=" * 55)

    # 测试：调用 Agent
    result = handle_user_message("user001", "你好！北京今天天气怎么样？")
    print(f"\n回复: {result['reply']}")
    print(f"历史消息数: {result['message_count']}")

    # 继续同一会话
    result2 = handle_user_message("user001", "我刚才问了什么？")
    print(f"\n回复: {result2['reply']}")
    print(f"历史消息数: {result2['message_count']}")

    # 查看长期记忆
    print("\n--- 长期记忆 ---")
    mem = get_memory("user001")
    print(json.dumps(mem, ensure_ascii=False, indent=2))

    print("\n提示：请先启动 LangChain API（python api.py）再运行本文件")