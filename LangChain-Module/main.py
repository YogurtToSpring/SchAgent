"""
LangChain 工具调用（Tool Calling）示例
=======================================
使用 langchain 1.3+ 最新的 create_agent API + langchain-deepseek 库。

本示例演示了 Agent 自动选择和调用工具的完整流程：
1. 定义工具（使用 @tool 装饰器）
2. 配置 DeepSeek 模型（langchain_deepseek.ChatDeepSeek）
3. 创建 Agent → 自动决策 → 调用工具 → 返回结果

运行方式：python main.py
"""

import os
from langchain.tools import tool
from langchain_deepseek import ChatDeepSeek
from langchain.agents import create_agent
from langchain_core.callbacks import BaseCallbackHandler


# 工具调用时的回调：当 Agent 调用任意工具时，自动打印一行提示
class ToolCallHandler(BaseCallbackHandler):
    def on_tool_start(self, serialized, input_str, **kwargs):
        print(f"[Tool] {serialized['name']}({input_str})")

# ============================================================
# 第1步：定义工具
# ============================================================
# 使用 @tool 装饰器定义工具，LangChain 会自动提取函数名、
# 文档字符串和参数类型作为工具的元数据（name, description, args_schema）


@tool
def get_weather(city: str) -> str:
    """查询指定城市的实时天气情况。参数 city 为城市名称，如 '北京'、'上海'。"""
    weather_data = {
        "北京": "晴天，温度 28°C，湿度 40%，风力 2 级",
        "上海": "多云转小雨，温度 25°C，湿度 75%，风力 3 级",
        "深圳": "雷阵雨，温度 30°C，湿度 85%，风力 4 级",
        "成都": "阴天，温度 22°C，湿度 60%，风力 1 级",
    }
    return weather_data.get(city, f"{city}：晴天，温度 26°C，湿度 50%，风力 2 级")


@tool
def calculator(expression: str) -> str:    
    """执行数学计算。参数 expression 为数学表达式字符串，如 '3 + 5 * 2'。支持加减乘除和括号。"""
    try:
        result = eval(expression, {"__builtins__": {}})
        return f"计算结果：{expression} = {result}"
    except Exception as e:
        return f"计算出错：{str(e)}"


@tool
def get_current_time() -> str:
    """获取当前日期和时间。不需要任何参数。"""
    from datetime import datetime
    return datetime.now().strftime("当前时间：%Y年%m月%d日 %H:%M:%S")


# ============================================================
# 第2步：配置 LLM 和创建 Agent
# ============================================================

# 工具列表
tools = [get_weather, calculator, get_current_time]

# 使用 langchain-deepseek 库的 ChatDeepSeek
api_key = os.getenv("DEEPSEEK_API_KEY", "sk-0a79b44b052a4e7189c35c09b04040fb")
llm = ChatDeepSeek(
    model="deepseek-v4-flash",
    api_key=api_key,
    temperature=0.3,
)

# ★ 核心：create_agent 一行创建能自动调用工具的 Agent
# 这是 langchain 1.3+ 的新 API，返回一个 CompiledStateGraph，直接 .invoke() 即可
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt="你是一个有用的智能助手。你可以使用以下工具来帮助用户：\n"
                  "- get_weather: 查询城市天气\n"
                  "- calculator: 执行数学计算\n"
                  "- get_current_time: 获取当前时间\n\n"
                  "请根据用户的问题，自主决定使用哪个工具。如果不需要工具就直接回答。",
)


# ============================================================
# 第3步：运行示例
# ============================================================

def run_query(query: str):
    """执行一次查询并打印结果"""
    print(f"\n[Message] User: {query}")
    # create_agent 返回的是 langgraph CompiledStateGraph，直接传 messages 调用
    # 传入 callbacks 以在工具调用时输出提示
    result = agent.invoke(
        {"messages": [{"role": "user", "content": query}]},
        config={"callbacks": [ToolCallHandler()]},
    )
    # 提取最后一条消息作为回复
    final_message = result["messages"][-1]
    print(f"\n[Message] Agent: {final_message.content}")


if __name__ == "__main__":
    # 示例1：天气查询 → Agent 会自动调用 get_weather 工具
    run_query("北京今天天气怎么样？")

    # 示例2：数学计算 → Agent 会自动调用 calculator 工具
    run_query("帮我算一下 (15 + 27) * 3 - 50 等于多少？")

    # 示例3：时间查询 → Agent 会自动调用 get_current_time 工具
    run_query("现在几点了？")

    # 示例4：不需要工具的问题 → Agent 直接回答
    run_query("你好，请介绍一下你自己。")

    # 示例5：多工具组合 → Agent 可能需要多次调用
    run_query("深圳天气如何？顺便帮我算一下 256 除以 8 等于多少。")
