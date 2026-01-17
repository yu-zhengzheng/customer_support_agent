# 常量定义
import pickle
import csv
import datetime
import http.client
import json
import os
import requests

# with open("../api_key.pkl", "wb") as f:
#    pickle.dump(("",""),f) 危险

with open("../api_key.pkl", "rb") as f:
    API_KEY = pickle.load(f)

# print(API_KEY)
# print(APIFOX_TOKEN)

MODEL_ID = "ali/qwen3-max"
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/d97235b5-9539-4cd6-965d-c0726a81a5eb"

CONNECTION = http.client.HTTPSConnection("router.shengsuanyun.com")
HEADERS = {
    'HTTP-Referer': 'https://www.postman.com',
    'X-Title': 'Postman',
    'Authorization': API_KEY,
    'Content-Type': 'application/json'
}

KNOWLEDGE_BASE = {
    "计费": "按量付费每千次 0.1 元，包月 299 元不限量。",
    "价格": "按量付费每千次 0.1 元，包月 299 元不限量。",
    "费用": "按量付费每千次 0.1 元，包月 299 元不限量。",
    "功能": "平台支持文本生成、图像识别、语音转换等多种AI能力。",
    "API": "提供 RESTful 接口，支持多语言 SDK。",
    "文档": "官方文档中心：https://docs.example.com",
}


def log(s: str) -> None:
    """
    把一条日志追加到 log.csv。
    """
    # 构造一行
    now = datetime.datetime.now()
    row = [f"{now.year % 100}{now.month:02}{now.day:02} {now.hour:02}{now.minute:02}{now.second:02}.{now.microsecond / 1000:03.0f}", s]

    # 以追加模式打开，newline='' 防止 Windows 多空行
    with open('log.csv', 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        # 如果文件刚创建，可写表头
        if f.tell() == 0:
            writer.writerow(['timestamp', 'message'])
        writer.writerow(row)


# 模型工具
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "飞书告警",
            "description": "通过 Webhook 向指定飞书账号/群发送富文本卡片。",
            "parameters": {
                "type": "object",
                "properties": {
                    "报错时间": {
                        "type": "string",
                        "description": "报错时间",
                    },
                    "错误代码": {
                        "type": "string",
                        "description": "错误代码",
                    },
                    "当前延迟": {
                        "type": "string",
                        "description": "当前延迟",
                    },

                },
                "required": ["报错时间", "错误代码", "当前延迟"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Apifox 文档同步",
            "description": "调用 Apifox 开放 API，自动生成一篇新的接口文档或错误日志。",
            "parameters": {
                "type": "object",
                "properties": {
                    "标题": {
                        "type": "string",
                        "description": "文档标题格式：[故障记录] YYYY-MM-DD HH:mm:ss",
                    },
                    "内容": {
                        "type": "string",
                        "description": "文档内容",
                    }
                },
                "required": ["标题", "内容"],
            },
        },
    },
]


def send_card(webhook: str, 报错时间: str = "", 错误代码: str = "", 当前延迟: str = "") -> str:
    """发卡片到飞书"""
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "🚨 API报错 🚨"},
                "template": "red"  # 支持 red/green/blue/yellow…
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"报错时间：{报错时间}\n错误代码：{错误代码}\n当前延迟：{当前延迟}"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "type": "primary",
                            "value": {"key": "click"},
                            "text": {"tag": "plain_text", "content": "查看详情"}
                        }
                    ]
                }
            ]
        }
    }

    headers = {"Content-Type": "application/json; charset=utf-8"}
    resp = requests.post(webhook, data=json.dumps(payload), headers=headers)
    result = resp.json()
    # print(result)
    return result.get("msg")


# print(send_card(WEBHOOK_URL,"00:00:00","404","0ms"))
# 胜算云API调用


def LLM_invoke(message, tools=None):
    payload = json.dumps({
        "model": MODEL_ID,
        "stream": False,
        "messages": message,
        "tools": tools,
        "stream_options": {
            "include_usage": True
        }
    }) if tools else json.dumps({
        "model": MODEL_ID,
        "stream": False,
        "messages": message,
        "stream_options": {
            "include_usage": True
        }
    })
    start_time = datetime.datetime.now()

    CONNECTION.request("POST", "/api/v1/chat/completions", payload, HEADERS)
    res = CONNECTION.getresponse()
    obj = json.loads(res.read().decode('utf-8'))
    elapsed_time = datetime.datetime.now() - start_time
    log(obj)
    # print("-"*100,f"\nexecuted in {elapsed_time.total_seconds():.4f} seconds")
    # print("usage:",obj["usage"])
    try:
        content = obj["choices"][0]
    except:
        print("msg=", message)
        print("obj=", obj)
        content = "（比赛无关）胜算云API错误"
    return content


# 知识库


# TODO vector database
def query(question: str) -> str:
    q = question.lower()
    for k, v in KNOWLEDGE_BASE.items():
        if k.lower() in q:
            return v
    return "知识库中未找到相关信息"


# Agent构建
from typing import Dict, List, Optional, Any
from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel


class AgentState(BaseModel):
    case_id: str
    user_query: str
    api_status: str
    api_response_time: str
    monitor_log: List[Dict]

    # 运行过程中产生的中间数据
    user_intent: Optional[str] = None
    final_reply: Optional[str] = None
    action_apifox_id: Optional[str] = None
    action_log: Dict = {}


def monitor_node_state(func):
    """打印AgentState的装饰器"""

    def inner(*args):
        # print(func.__name__,"entered:",args)
        log(*args)
        return func(*args)

    return inner


@monitor_node_state
def node_monitor(state: AgentState) -> AgentState:
    """判断是否需要触发报警流程+判断用户意图"""
    if state.api_status != "200 OK":
        sys_msg = (
            "你是智能客服助手。请基于【监控历史】给出真实、自然、简洁、专业化的回答，而不是瞎编。"
            "触发报警流程。通过 Webhook 向指定飞书账号/群发送富文本卡片。"
            "内容需包含：报错时间、错误代码、当前延迟。"
            "调用 Apifox 开放 API，自动生成一篇新的接口文档或错误日志。"
            "文档标题格式：[故障记录] YYYY-MM-DD HH:mm:ss。"
        )
        user_msg = f"【监控日志】\n{state.api_status} 当前延迟:{state.api_response_time}{state.monitor_log}"
        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg},
        ]
        response = LLM_invoke(messages, tools=TOOLS)
        # 调用工具
        for tc in response["message"]["tool_calls"]:
            func_name = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"])

            if func_name == "飞书告警":
                state.action_log["feishu_webhook"] = send_card(WEBHOOK_URL, **args)  # 发送富文本卡片

                print("飞书告警 args:", args, "\n", state.action_log["feishu_webhook"])
            elif func_name == "Apifox 文档同步":
                print("（模拟）Apifox 文档同步 args:", args)
                state.action_log["apifox_doc_id"] = args["标题"]

    # 如果user_query有内容则让大模型确定用户意图
    if state.user_query:
        """让大模型决定回复内容（系统正常分支）"""
        sys_msg = (
            "你是智能客服助手。请根据用户问题判断用户的意图，如果用户问的是业务问题，输出\"业务\"，如果用户问的是系统状态问题，输出\"状态\"。"
        )
        user_msg = f"{state.user_query}"
        print("user:  ", user_msg)
        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg},
        ]
        judgement = LLM_invoke(messages)["message"]["content"]
        # print("judgement:", judgement)

        if judgement == "业务":
            state.user_intent = "业务"
        elif judgement == "状态":
            state.user_intent = "状态"
        else:
            state.user_intent = judgement
    # 否则就是例行监控
    else:
        state.user_intent = "监控"
    return state


@monitor_node_state
def node_knowledge(state: AgentState) -> AgentState:
    """大模型回复业务问题"""
    sys_msg = (
        "你是智能客服助手。请根据【用户问题】和【知识库片段】生成一段自然、简洁、口语化的回复。"
        "如果知识库片段为空，可委婉表示暂未找到信息。"
    )
    user_msg = f"【用户问题】{state.user_query}\n【知识库片段】{query(state.user_query)}"
    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": user_msg},
    ]
    state.final_reply = LLM_invoke(messages)["message"]["content"]
    return state


@monitor_node_state
def node_server(state: AgentState) -> AgentState:
    """大模型回复系统系统状态问题"""
    sys_msg = (
        "你是智能客服助手。请基于【用户问题】和【监控历史】给出真实、自然、简洁、专业化的回答，而不是瞎编。"
        "如果知识库片段为空，可委婉表示暂未找到信息。"
        "你不需要调用工具。"
    )
    user_msg = f"【用户问题】{state.user_query}\n【监控日志】{state.api_status}{state.api_response_time}{state.monitor_log}"
    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": user_msg},
    ]
    response = LLM_invoke(messages)
    state.final_reply = response["message"]["content"]
    return state


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("monitor", node_monitor)
    workflow.set_entry_point("monitor")

    workflow.add_node("knowledge", node_knowledge)
    workflow.add_node("server", node_server)

    # 条件边：retrieve 之后根据系统状态分支
    # @print_state_info
    def _router(state: AgentState):
        if state.user_intent == "监控":
            return "监控"
        elif state.user_intent == "状态":
            return "状态"
        elif state.user_intent == "业务":
            return "业务"
        else:
            return "状态"  # 模型未按要求输出时默认状态查询

    workflow.add_conditional_edges(
        "monitor",
        _router,
        {"状态": "server", "业务": "knowledge", "监控": END},
    )

    workflow.add_edge("server", END)
    workflow.add_edge("knowledge", END)

    # memory = MemorySaver()
    graph = workflow.compile(checkpointer=False)  # memory) 暂不使用检查点

    # 生成模型结构流程图
    mmd_graph = graph.get_graph().draw_mermaid().replace("classDef", "%% classDef")
    with open("graph.mmd", "w", encoding='utf-8') as f:
        #可能出现汉字编码问题
        try:
            f.write(mmd_graph)
        except UnicodeDecodeError as e:
            print(e)
        except Exception as e:
            print(e)
        # assert False, "breakpoint"
    return graph


class SmartAgent:
    def __init__(self):
        self.graph = build_graph()

    def process(self, case: Dict[str, Any]) -> Dict[str, Any]:
        state = AgentState(**case)
        print("=" * 100, "\ncase:", case,"\n","-" * 100)
        # thread = {"configurable": {"thread_id": case["case_id"]}}
        # print("-"*100,"\nstate.model_dump():",state.model_dump())
        final_state = self.graph.invoke(state.model_dump())  # , config=thread)
        print("agent:", final_state["final_reply"])
        # 组装成旧格式
        return {
            "case_id": final_state["case_id"],
            "reply": final_state["final_reply"],
            "action_triggered": final_state["action_log"]
        }


# 读取输入数据
try:
    with open("../inputs.json", "r", encoding="utf-8") as f:
        inputs = json.load(f)
    print(f"✅ 成功读取 {len(inputs)} 个测试用例")
except FileNotFoundError:
    print("❌ 未找到 inputs.json!")

# 运行Agent
print("=" * 100)
print("智能客服监控 Agent启动")
print("=" * 100)

agent = SmartAgent()
# results = agent.process(inputs[0])
results = [agent.process(case) for case in inputs]
# 文件输出
os.makedirs("outputs", exist_ok=True)
with open("../outputs/results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("✅ 处理完成！结果已保存到 outputs/results.json")
