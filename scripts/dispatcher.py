# -*- coding: utf-8 -*-
"""
任务分发器 - 将任务分发到远程节点
"""

import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from registry import NodeRegistry, Node
from http_client import HttpClient, NodeResponse


@dataclass
class TaskResult:
    """任务结果"""
    node_id: str
    node_name: str
    success: bool
    data: Any = None
    error: str = ""
    latency_ms: int = 0


class TaskDispatcher:
    """任务分发器"""

    def __init__(self, registry: NodeRegistry, http_client: HttpClient):
        self.registry = registry
        self.http_client = http_client

    async def dispatch(
        self,
        node_id: str,
        message: str,
        user_id: str = "remote",
        timeout: int = 120
    ) -> TaskResult:
        """分发任务到指定节点"""
        node = self.registry.get_node(node_id)
        if not node:
            return TaskResult(
                node_id=node_id,
                node_name=node_id,
                success=False,
                error=f"节点 {node_id} 不存在"
            )

        # 设置超时
        original_timeout = self.http_client.timeout
        self.http_client.timeout = timeout

        try:
            response = await self.http_client.dispatch_task(
                url=node.url,
                token=node.token,
                message=message,
                user_id=user_id
            )

            # 更新心跳
            self.registry.update_heartbeat(node_id, response.latency_ms)

            return TaskResult(
                node_id=node_id,
                node_name=node.name,
                success=response.success,
                data=response.data,
                error=response.error,
                latency_ms=response.latency_ms
            )
        except Exception as e:
            self.registry.set_offline(node_id)
            return TaskResult(
                node_id=node_id,
                node_name=node.name,
                success=False,
                error=str(e)
            )
        finally:
            self.http_client.timeout = original_timeout

    async def dispatch_to_node_by_name(
        self,
        node_name: str,
        message: str,
        user_id: str = "remote",
        timeout: int = 120
    ) -> TaskResult:
        """通过节点名称分发任务"""
        node = self.registry.get_node_by_name(node_name)
        if not node:
            return TaskResult(
                node_id="",
                node_name=node_name,
                success=False,
                error=f"节点 {node_name} 不存在"
            )
        return await self.dispatch(node.id, message, user_id, timeout)

    async def broadcast(
        self,
        message: str,
        user_id: str = "remote",
        timeout: int = 30,
        select: str = "fastest"  # "fastest" | "all"
    ) -> List[TaskResult]:
        """广播任务到所有在线节点"""
        nodes = self.registry.get_online_nodes()
        
        if not nodes:
            return []

        # 并行执行
        tasks = [
            self.dispatch(node.id, message, user_id, timeout)
            for node in nodes
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                valid_results.append(TaskResult(
                    node_id=nodes[i].id,
                    node_name=nodes[i].name,
                    success=False,
                    error=str(result)
                ))
            else:
                valid_results.append(result)

        if select == "fastest":
            # 返回最快的成功结果
            valid_results.sort(key=lambda x: x.latency_ms if x.success else 999999)
            if valid_results and valid_results[0].success:
                return [valid_results[0]]
            return valid_results[:1] if valid_results else []

        return valid_results

    async def round_robin(
        self,
        messages: List[str],
        user_id: str = "remote",
        timeout: int = 120
    ) -> List[TaskResult]:
        """轮询分发任务到不同节点"""
        nodes = self.registry.get_online_nodes()
        
        if not nodes:
            return []

        results = []
        for i, message in enumerate(messages):
            node = nodes[i % len(nodes)]
            result = await self.dispatch(node.id, message, user_id, timeout)
            results.append(result)

        return results

    async def call_skill(
        self,
        node_id: str,
        skill_name: str,
        action: str,
        params: Dict[str, Any],
        timeout: int = 120
    ) -> TaskResult:
        """调用远程节点的技能"""
        node = self.registry.get_node(node_id)
        if not node:
            return TaskResult(
                node_id=node_id,
                node_name=node_id,
                success=False,
                error=f"节点 {node_id} 不存在"
            )

        original_timeout = self.http_client.timeout
        self.http_client.timeout = timeout

        try:
            response = await self.http_client.call_skill(
                url=node.url,
                token=node.token,
                skill_name=skill_name,
                action=action,
                params=params
            )

            self.registry.update_heartbeat(node_id, response.latency_ms)

            return TaskResult(
                node_id=node_id,
                node_name=node.name,
                success=response.success,
                data=response.data,
                error=response.error,
                latency_ms=response.latency_ms
            )
        except Exception as e:
            self.registry.set_offline(node_id)
            return TaskResult(
                node_id=node_id,
                node_name=node.name,
                success=False,
                error=str(e)
            )
        finally:
            self.http_client.timeout = original_timeout