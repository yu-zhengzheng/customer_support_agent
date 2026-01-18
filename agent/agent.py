# 常量定义
import pickle
import csv
import datetime
import time
import http.client
import json
import os
import requests

API_KEY = "MWYJvUu1shEFM-xXBo2SoLQ7cHQKlUUTmQT7bQ-HYlytdOM9m5lCce8DBDRIC8SosUEzRP7xQsfI4qMZlPJu7dVb"
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
    "注册": "支持手机号验证码或微信扫码快速注册，未注册用户首次登录自动完成注册。",
    "登录": "提供手机号验证码、账号名+密码、微信扫码三种登录方式。",
    "修改密": "在控制台个人中心-个人设置中可修改密码，需验证原密码确保账户安全。",
    "实名": "个人用户使用支付宝扫码认证，企业用户需联系客服人工处理。",
    "充值": "支持微信、支付宝扫码支付，企业用户可申请对公汇款。",
    "余额": "登录后右上角实时显示账户余额，费用中心可查看详细消耗记录。",
    "密钥": "在控制台API密钥模块点击创建，系统自动生成专属密钥供调用使用。支持编辑密钥名称、查看调用权限、删除重建，需妥善保管避免泄露。",
    "用记录": "费用中心可查看每次请求的模型、token数、扣费金额等完整调用详情。",
    "计费": "按实际tokens用量计费，供应商成本基础上加收10%平台费（含税）。",
    "价格": "各模型价格不同，可在官网模型列表查看每百万输入/输出tokens的明确标价。",
    "RPM": "每分钟请求数限制，根据账户套餐等级不同，超额返回429错误。",
    "TPM": "每分钟处理的tokens总数限制，根据账户套餐等级不同，超额返回429错误。",
    "API": "调用地址https://router.shengsuanyun.com/api/v1，支持所有模型统一接入。",
    "模型名称": "在请求体model字段中指定模型名称，如'anthropic/claude-sonnet-4'。",
    "流式": "设置stream=true使用SSE格式返回，提升交互体验并减少等待时间。",
    "用量": "设置stream_options.include_usage=true，在最后一个响应块返回完整usage信息。",
    "认证头": "Authorization: Bearer <API_KEY>，必须包含Bearer前缀和有效密钥。",
    "请求体": "JSON格式，需包含model、messages等必需字段，结构需符合API文档。",
    "响应": "同步请求返回JSON对象，流式请求返回SSE格式数据块序列。",
    "超时": "客户端建议设置60-120秒超时，复杂请求可延长至300秒以上。",
    "错误": "统一返回JSON对象，包含error.type、error.message、error.code等字段。",
    "400": "请求参数错误，如JSON格式错误、缺少必需参数、参数值类型或范围无效。",
    "401": "API密钥无效、格式错误、已被禁用或账户认证失败导致权限不足。",
    "402": "配额超限，通常是账户余额不足或套餐用量额度已用尽。",
    "403": "权限不足，可能是账户余额不足或API密钥未授予访问该资源的权限。",
    "429": "速率限制，包括TPM/RPM超限，请求频率或token消耗超过套餐限额。",
    "500": "服务器内部错误，通常短暂等待数秒后重试即可解决。",
    "503": "服务不可用，服务器过载或维护中，需等待数分钟并多次重试。",
    "隐私": "平台不记录敏感内容，保障用户数据安全和商业机密。",
    "客服": "工作时间人工客服，非工作时间可加入胜算云Router微信群获取支持。",
    "文档": "docs.router.shengsuanyun.com提供完整API文档和使用指南。",
    "模型列表": "router.shengsuanyun.com/model可查看所有支持模型的参数和价格。",
    "代金券": "点击用户头像-兑换赠送额度-输入兑换码完成代金券兑换。",
    "免费": "暂不提供免费模型，因免费模型普遍限速限流无法满足编程需求。",
    "新用户": "不定期提供小额试用额度，关注社交媒体获取最新通知。",
    "接口": "支持Apifox等工具测试，需设置Authorization和Content-Type头。",
    "SSE": "按行解析，每行以'data: '开头，取其后JSON数据解析。",
    "usage": "流式响应最后一个chunk包含prompt_tokens、completion_tokens和total_tokens。",
    "套餐": "在控制台选择更高配额套餐升级，提升RPM/TPM限制。",
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
    print(f"executed in {elapsed_time.total_seconds():.4f} seconds")

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
            "你是智能客服助手。请基于【监控历史】通过 Webhook 向指定飞书账号/群发送富文本卡片,内容需包含：报错时间、错误代码、当前延迟。"
            "然后调用 Apifox 开放 API，自动生成一篇新的接口文档或错误日志。文档标题格式：[故障记录] YYYY-MM-DD HH:mm:ss。"
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
        "如果知识库中没有答案，需回答“知识库中未找到相关信息”，严禁产生幻觉。"
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

    # 条件边：monitor 之后根据系统状态分支
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

    graph = workflow.compile(checkpointer=False)

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
        print(f"\n\n{'=' * 100}\ncase:", case,"\n","-" * 100)
        final_state = self.graph.invoke(state.model_dump())  # , config=thread)
        print("agent:", final_state["final_reply"])
        time.sleep(5)
        print("（演示时每个示例间暂停5秒）")
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
print("\n--- 智能客服监控 Agent启动 ---")
agent = SmartAgent()
# results = agent.process(inputs[0])
results = [agent.process(case) for case in inputs]
# 文件输出
os.makedirs("outputs", exist_ok=True)
with open("../outputs/results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n\n{'='*100}\n✅ 处理完成！结果已保存到 outputs/results.json")
