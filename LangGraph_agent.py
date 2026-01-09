"""
智能客服监控 Agent – LangGraph 版
作者：AI助手
日期：2025-01-06（重构）
"""
import json, os, time, requests
from datetime import datetime
from typing import Dict, List, Optional, Any

from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

# --------------------------------------------------
# 0. 外部大模型调用封装（用户自己实现）
# --------------------------------------------------
def get_response(messages: list) -> str:
    """
    统一调用外部大模型接口，messages 为 openai 风格列表：
    [{"role":"system","content":...}, {"role":"user","content":...}]
    返回生成的字符串。
    这里用一个假的本地函数模拟，真实场景请替换成 http 调用或 SDK。
    """
    # 模拟延迟
    time.sleep(0.5)
    # 这里简单 echo，实际请调用真实模型
    last = messages[-1]["content"]
    if "计费" in last or "价格" in last:
        return "根据平台文档，我们提供按量付费和包月订阅两种模式。按量付费的价格为每千次调用 0.1 元，包月订阅为 299 元/月不限量调用。"
    if "系统稳定" in last or "挂了" in last:
        return "系统刚才出现了一点小波动，目前已恢复，请放心使用。"
    return "您好，这里是智能客服，请问有什么可以帮您？"


# --------------------------------------------------
# 1. 知识库 / 监控 / 动作 工具函数（保持原逻辑）
# --------------------------------------------------
class KnowledgeBase:
    def __init__(self):
        self.knowledge = {
            "计费": "按量付费每千次 0.1 元，包月 299 元不限量。",
            "价格": "按量付费每千次 0.1 元，包月 299 元不限量。",
            "费用": "按量付费每千次 0.1 元，包月 299 元不限量。",
            "功能": "平台支持文本生成、图像识别、语音转换等多种AI能力。",
            "API": "提供 RESTful 接口，支持多语言 SDK。",
            "文档": "官方文档中心：https://docs.example.com",
        }

    def query(self, question: str) -> str:
        q = question.lower()
        for k, v in self.knowledge.items():
            if k.lower() in q:
                return v
        return "知识库中未找到相关信息"


class Monitor:
    @staticmethod
    def is_healthy(api_status: str) -> bool:
        return api_status == "200 OK"

    @staticmethod
    def get_stability_info(monitor_log: List[Dict]) -> str:
        if not monitor_log:
            return "系统目前运行稳定"
        latest = monitor_log[-1]
        return f"系统在 {latest['timestamp']} 曾出现 {latest['msg']}，目前已恢复。"


class Actions:
    @staticmethod
    def send_feishu_alert(api_status: str, response_time: str, monitor_log: List[Dict]) -> str:
        print("📤 发送飞书告警（模拟）")
        return "Sent success"

    @staticmethod
    def create_apifox_doc(api_status: str, response_time: str, monitor_log: List[Dict]) -> str:
        print("📄 创建 Apifox 故障文档（模拟）")
        return f"DOC_{datetime.now():%Y%m%d_%H%M%S}_ERROR"


# --------------------------------------------------
# 2. LangGraph 状态定义
# --------------------------------------------------
class AgentState(BaseModel):
    case_id: str
    user_query: str
    api_status: str
    api_response_time: str
    monitor_log: List[Dict]

    # 运行过程中产生的中间数据
    system_healthy: Optional[bool] = None
    knowledge_snippet: Optional[str] = None
    final_reply: Optional[str] = None
    action_apifox_id: Optional[str] = None


# --------------------------------------------------
# 3. 节点函数
# --------------------------------------------------
kb = KnowledgeBase()
monitor = Monitor()
actions = Actions()


def node_retrieve(state: AgentState) -> AgentState:
    """检索知识库 + 判断系统健康"""
    state.system_healthy = monitor.is_healthy(state.api_status)
    state.knowledge_snippet = kb.query(state.user_query)
    return state


def node_llm_decide(state: AgentState) -> AgentState:
    """让大模型决定回复内容（系统正常分支）"""
    sys_msg = (
        "你是智能客服助手。请根据【用户问题】和【知识库片段】生成一段自然、简洁、口语化的回复。"
        "如果知识库片段为空，可委婉表示暂未找到信息。"
    )
    user_msg = f"【用户问题】{state.user_query}\n【知识库片段】{state.knowledge_snippet}"
    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": user_msg},
    ]
    state.final_reply = get_response(messages)
    return state


def node_error_reply(state: AgentState) -> AgentState:
    """系统异常时的统一回复"""
    latest = state.monitor_log[-1] if state.monitor_log else None
    if latest:
        hint = f"在 {latest['timestamp']} 出现 {latest['msg']}，目前已恢复。"
    else:
        hint = "检测到模型 API 异常，正在修复，请稍后再试。"
    state.final_reply = f"非常抱歉，{hint} 给您带来不便敬请谅解。"
    return state


def node_alert(state: AgentState) -> AgentState:
    """触发飞书告警"""
    actions.send_feishu_alert(state.api_status, state.api_response_time, state.monitor_log)
    return state


def node_doc(state: AgentState) -> AgentState:
    """创建 Apifox 文档"""
    state.action_apifox_id = actions.create_apifox_doc(
        state.api_status, state.api_response_time, state.monitor_log
    )
    return state


# --------------------------------------------------
# 4. 构建图
# --------------------------------------------------
def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("retrieve", node_retrieve)
    workflow.add_node("llm_decide", node_llm_decide)
    workflow.add_node("error_reply", node_error_reply)
    workflow.add_node("alert", node_alert)
    workflow.add_node("doc", node_doc)

    workflow.set_entry_point("retrieve")

    # 条件边：retrieve 之后根据系统状态分支
    def _router(state: AgentState):
        return "normal" if state.system_healthy else "error"

    workflow.add_conditional_edges(
        "retrieve",
        _router,
        {"normal": "llm_decide", "error": "alert"},
    )

    # 异常分支：alert -> doc -> error_reply -> END
    workflow.add_edge("alert", "doc")
    workflow.add_edge("doc", "error_reply")
    workflow.add_edge("error_reply", END)

    # 正常分支：llm_decide -> END
    workflow.add_edge("llm_decide", END)

    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)
    return graph


# --------------------------------------------------
# 5. 对外暴露的 Agent 类（保持原接口）
# --------------------------------------------------
class SmartAgent:
    def __init__(self):
        self.graph = build_graph()

    def process(self, case: Dict[str, Any]) -> Dict[str, Any]:
        state = AgentState(**case)
        thread = {"configurable": {"thread_id": case["case_id"]}}
        final_state = self.graph.invoke(state.model_dump(), thread)

        # 组装成旧格式
        return {
            "case_id": final_state["case_id"],
            "reply": final_state["final_reply"],
            "action_triggered": (
                {"apifox_doc_id": final_state["action_apifox_id"]}
                if final_state["action_apifox_id"]
                else None
            ),
        }


# --------------------------------------------------
# 6. main 入口（与原版完全一致）
# --------------------------------------------------
def main():
    print("=" * 60)
    print("智能客服监控 Agent – LangGraph 版 启动")
    print("=" * 60)

    agent = SmartAgent()

    # 读取输入
    try:
        with open("inputs.json", "r", encoding="utf-8") as f:
            inputs = json.load(f)
        print(f"✅ 成功读取 {len(inputs)} 个测试用例")
    except FileNotFoundError:
        print("❌ 未找到 inputs.json，使用内置测试数据")
        inputs = [
            {
                "case_id": "C001",
                "user_query": "你们平台的计费模式是怎样的？",
                "api_status": "200 OK",
                "api_response_time": "120ms",
                "monitor_log": [],
            },
            {
                "case_id": "C002",
                "user_query": "刚才模型是不是挂了？怎么一直没反应？",
                "api_status": "500 Internal Server Error",
                "api_response_time": "Timeout",
                "monitor_log": [
                    {"timestamp": "10:00:01", "status": "Error", "msg": "Connection Refused"}
                ],
            },
            {
                "case_id": "C003",
                "user_query": "今天系统稳定吗？",
                "api_status": "200 OK",
                "api_response_time": "150ms",
                "monitor_log": [
                    {"timestamp": "09:30:15", "status": "Error", "msg": "Timeout"},
                    {"timestamp": "09:35:20", "status": "OK", "msg": "Recovered"},
                ],
            },
        ]

    results = [agent.process(case) for case in inputs]

    os.makedirs("outputs", exist_ok=True)
    with open("outputs/results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("✅ 处理完成！结果已保存到 outputs/results.json")
    print("=" * 60 + "\n")

    print("【处理摘要】")
    for r in results:
        print(f"  {r['case_id']}: 已回复 {'✓' if r['action_triggered'] else '✗'} 触发动作")


if __name__ == "__main__":
    main()