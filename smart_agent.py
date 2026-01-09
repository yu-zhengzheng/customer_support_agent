"""
智能客服监控 Agent - 完整实现
作者：AI助手
日期：2025-01-06
"""

import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
import os


class KnowledgeBase:
    """知识库模块 - 负责回答业务问题"""
    
    def __init__(self):
        # 模拟知识库内容（实际项目中可能是数据库或API）
        self.knowledge = {
            "计费": "根据平台文档，我们提供按量付费和包月订阅两种模式。按量付费的价格为每千次调用 0.1 元，包月订阅为 299 元/月不限量调用。",
            "价格": "根据平台文档，我们提供按量付费和包月订阅两种模式。按量付费的价格为每千次调用 0.1 元，包月订阅为 299 元/月不限量调用。",
            "费用": "根据平台文档，我们提供按量付费和包月订阅两种模式。按量付费的价格为每千次调用 0.1 元，包月订阅为 299 元/月不限量调用。",
            "功能": "平台支持文本生成、图像识别、语音转换等多种AI能力，具体功能请查看产品文档。",
            "API": "平台提供RESTful API接口，支持多种编程语言调用，详细文档请查看开发者中心。",
            "文档": "您可以访问我们的官方文档中心：https://docs.example.com 获取详细的使用说明。"
        }
    
    def query(self, question: str) -> str:
        """查询知识库，返回最匹配的回答"""
        question_lower = question.lower()
        
        for keyword, answer in self.knowledge.items():
            if keyword.lower() in question_lower:
                print("虞铮铮：",answer)
                return answer
        return "知识库中未找到相关信息"


class Monitor:
    """监控模块 - 负责感知系统状态"""
    
    @staticmethod
    def is_system_healthy(api_status: str) -> bool:
        """判断API是否正常"""
        return api_status == "200 OK"
    
    @staticmethod
    def get_stability_info(monitor_log: List[Dict]) -> str:
        """基于监控日志生成稳定性描述"""
        if not monitor_log:
            return "系统目前运行稳定"
        
        latest_error = monitor_log[-1]
        return f"系统在 {latest_error['timestamp']} 曾出现 {latest_error['msg']} 的问题，目前已恢复正常"


class Actions:
    """动作执行模块 - 负责触发外部操作"""
    
    @staticmethod
    def send_feishu_alert(api_status: str, response_time: str, monitor_log: List[Dict]) -> str:
        """发送飞书告警（模拟）"""
        print(f"📤 正在发送飞书告警...")
        print(f"   状态: {api_status}")
        print(f"   响应时间: {response_time}")
        
        # 这里应该是真实的飞书Webhook调用
        # requests.post(webhook_url, json=alert_data)
        
        return "Sent success"
    
    @staticmethod
    def create_apifox_doc(api_status: str, response_time: str, monitor_log: List[Dict]) -> str:
        """创建Apifox故障文档（模拟）"""
        print(f"📄 正在创建Apifox文档...")
        
        # 生成文档ID
        doc_id = f"DOC_{datetime.now().strftime('%Y%m%d_%H%M%S')}_ERROR"
        
        # 这里应该是真实的Apifox API调用
        # requests.post(apifox_api, json=doc_data)
        
        return doc_id


class SmartAgent:
    """智能客服Agent - 核心决策逻辑"""
    
    def __init__(self):
        self.kb = KnowledgeBase()
        self.monitor = Monitor()
        self.actions = Actions()
    
    def process(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个测试用例"""
        case_id = case["case_id"]
        user_query = case["user_query"]
        api_status = case["api_status"]
        response_time = case["api_response_time"]
        monitor_log = case["monitor_log"]
        
        print(f"\n{'='*60}")
        print(f"【处理案例】: {case_id}")
        print(f"用户提问: {user_query}")
        print(f"API状态: {api_status}")
        print(f"响应时间: {response_time}")
        
        # 判断系统状态
        is_healthy = self.monitor.is_system_healthy(api_status)
        
        action_triggered = None
        
        if is_healthy:
            print(f"\n🟢 系统运行正常")
            reply = self._handle_healthy_query(user_query, monitor_log)
        else:
            print(f"\n🔴 检测到系统异常！")
            # 触发告警和文档记录
            feishu_result = self.actions.send_feishu_alert(api_status, response_time, monitor_log)
            apifox_result = self.actions.create_apifox_doc(api_status, response_time, monitor_log)
            
            action_triggered = {
                "feishu_webhook": feishu_result,
                "apifox_doc_id": apifox_result
            }
            
            # 生成故障回复
            reply = self._handle_error_query(monitor_log)
        
        print(f"\n🤖 智能回复: {reply}")
        if action_triggered:
            print(f"⚡ 触发动作: {action_triggered}")
        
        return {
            "case_id": case_id,
            "reply": reply,
            "action_triggered": action_triggered
        }
    
    def _handle_healthy_query(self, query: str, monitor_log: List[Dict]) -> str:
        """处理系统正常时的用户查询"""
        # 检查是否在询问系统稳定性
        stability_keywords = ["系统", "稳定", "挂", "崩", "坏", "问题", "异常"]
        if any(keyword in query for keyword in stability_keywords):
            stability_info = self.monitor.get_stability_info(monitor_log)
            return f"根据监控数据，{stability_info}。"
        
        # 从知识库查找答案
        return self.kb.query(query)
    
    def _handle_error_query(self, monitor_log: List[Dict]) -> str:
        """处理系统异常时的用户查询"""
        if monitor_log:
            latest_error = monitor_log[-1]
            return f"非常抱歉，检测到模型 API 在 {latest_error['timestamp']} 出现了短暂的 {latest_error['msg']}。目前系统正在自动修复中，请您稍后再试。"
        else:
            return "非常抱歉，检测到模型 API 出现了异常。目前系统正在自动修复中，请您稍后再试。"


def main():
    """主程序入口"""
    print("="*60)
    print("智能客服监控 Agent - 启动")
    print("="*60)
    
    # 创建Agent
    agent = SmartAgent()
    
    # 读取输入数据
    try:
        with open("inputs.json", "r", encoding="utf-8") as f:
            inputs = json.load(f)
        print(f"✅ 成功读取 {len(inputs)} 个测试用例")
    except FileNotFoundError:
        print("❌ 未找到 inputs.json 文件，使用内置测试数据")
        inputs = [
            {
                "case_id": "C001",
                "user_query": "你们平台的计费模式是怎样的？",
                "api_status": "200 OK",
                "api_response_time": "120ms",
                "monitor_log": []
            },
            {
                "case_id": "C002",
                "user_query": "刚才模型是不是挂了？怎么一直没反应？",
                "api_status": "500 Internal Server Error",
                "api_response_time": "Timeout",
                "monitor_log": [
                    {"timestamp": "10:00:01", "status": "Error", "msg": "Connection Refused"}
                ]
            },
            {
                "case_id": "C003",
                "user_query": "今天系统稳定吗？",
                "api_status": "200 OK",
                "api_response_time": "150ms",
                "monitor_log": [
                    {"timestamp": "09:30:15", "status": "Error", "msg": "Timeout"},
                    {"timestamp": "09:35:20", "status": "OK", "msg": "Recovered"}
                ]
            }
        ]
    
    # 处理所有测试用例
    results = []
    for case in inputs:
        result = agent.process(case)
        results.append(result)
    
    # 创建输出目录
    os.makedirs("outputs", exist_ok=True)
    
    # 保存结果
    with open("outputs/results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✅ 处理完成！结果已保存到 outputs/results.json")
    print(f"{'='*60}\n")
    
    # 打印最终结果摘要
    print("【处理摘要】")
    for result in results:
        case_id = result["case_id"]
        has_action = "✓" if result["action_triggered"] else "✗"
        print(f"  {case_id}: 已回复 {has_action} 触发动作")


if __name__ == "__main__":
    main()
