# -*- coding: utf-8 -*-
"""
路由分发器 - 智能选择最佳节点执行任务
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from registry import NodeRegistry, Node
from http_client import HttpClient, NodeResponse


@dataclass
class TaskRequest:
    """任务请求"""
    message: str
    capability: str = ""  # 需要的技能
    timeout: int = 120
    priority: str = "normal"  # normal | high | low


@dataclass
class TaskResponse:
    """任务响应"""
    node_app_id: str
    node_name: str
    success: bool
    data: Any = None
    error: str = ""
    latency_ms: int = 0


class Router:
    """智能路由"""

    def __init__(self, registry: NodeRegistry, http_client: HttpClient):
        self.registry = registry
        self.http = http_client
        self.strategy = "load"  # load | latency | round_robin | capability

    def select_node(self, capability: str = "") -> Optional[Node]:
        """选择最佳节点"""
        if capability:
            # 按能力筛选
            nodes = self.registry.list_by_capability(capability)
        else:
            nodes = self.registry.list_online()
        
        if not nodes:
            return None
        
        # 根据策略选择
        if self.strategy == "load":
            nodes.sort(key=lambda x: x.load)
        elif self.strategy == "latency":
            nodes.sort(key=lambda x: x.latency_ms)
        elif self.strategy == "round_robin":
            pass  # 保持原顺序
        
        return nodes[0] if nodes else None

    async def dispatch(
        self,
        node: Node,
        app_id: str,
        key: str,
        message: str,
        timeout: int = 120
    ) -> TaskResponse:
        """分发任务到节点"""
        response = await self.http.dispatch(
            url=node.url,
            app_id=app_id,
            key=key,
            message=message,
            timeout=timeout
        )
        
        return TaskResponse(
            node_app_id=node.app_id,
            node_name=node.name,
            success=response.success,
            data=response.data,
            error=response.error,
            latency_ms=response.latency_ms
        )

    async def route(
        self,
        request: TaskRequest,
        master_app_id: str,
        master_key: str
    ) -> TaskResponse:
        """路由任务"""
        # 选择节点
        node = self.select_node(request.capability)
        
        if not node:
            return TaskResponse(
                node_app_id="",
                node_name="",
                success=False,
                error="没有可用的节点"
            )
        
        # 标记节点忙碌
        self.registry.set_busy(node.app_id)
        
        try:
            return await self.dispatch(
                node, master_app_id, master_key,
                request.message, request.timeout
            )
        finally:
            # 恢复空闲
            self.registry.set_idle(node.app_id)

    async def broadcast(
        self,
        request: TaskRequest,
        master_app_id: str,
        master_key: str,
        select: str = "fastest"  # fastest | all
    ) -> List[TaskResponse]:
        """广播任务"""
        nodes = self.registry.list_online()
        
        if not nodes:
            return []
        
        # 并行执行
        tasks = [
            self.dispatch(node, master_app_id, master_key, request.message, request.timeout)
            for node in nodes
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                valid_results.append(TaskResponse(
                    node_app_id=nodes[i].app_id,
                    node_name=nodes[i].name,
                    success=False,
                    error=str(result)
                ))
            else:
                valid_results.append(result)
        
        if select == "fastest":
            valid_results.sort(key=lambda x: x.latency_ms if x.success else 999999)
            if valid_results and valid_results[0].success:
                return [valid_results[0]]
            return valid_results[:1] if valid_results else []
        
        return valid_results

    async def fallback(
        self,
        request: TaskRequest,
        master_app_id: str,
        master_key: str,
        max_retries: int = 2
    ) -> TaskResponse:
        """失败重试（备用节点）"""
        nodes = self.registry.list_online()
        
        if not nodes:
            return TaskResponse(
                node_app_id="",
                node_name="",
                success=False,
                error="没有可用的节点"
            )
        
        last_error = ""
        for node in nodes[:max_retries + 1]:
            self.registry.set_busy(node.app_id)
            try:
                result = await self.dispatch(
                    node, master_app_id, master_key,
                    request.message, request.timeout
                )
                if result.success:
                    return result
                last_error = result.error
            except Exception as e:
                last_error = str(e)
            finally:
                self.registry.set_idle(node.app_id)
        
        return TaskResponse(
            node_app_id="",
            node_name="",
            success=False,
            error=f"所有节点都失败: {last_error}"
        )


class TaskQueue:
    """任务队列（简单实现）"""

    def __init__(self, router: Router):
        self.router = router
        self.queue: asyncio.Queue = asyncio.Queue()
        self.running = False

    async def enqueue(self, request: TaskRequest):
        """入队"""
        await self.queue.put(request)

    async def worker(self, master_app_id: str, master_key: str):
        """工作协程"""
        while self.running:
            try:
                request = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await self.router.route(request, master_app_id, master_key)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"队列执行错误: {e}")

    async def start(self, master_app_id: str, master_key: str, workers: int = 3):
        """启动队列"""
        self.running = True
        self.workers = [
            asyncio.create_task(self.worker(master_app_id, master_key))
            for _ in range(workers)
        ]

    async def stop(self):
        """停止队列"""
        self.running = False
        for w in self.workers:
            w.cancel()


# ==================== 便捷函数 ====================

def create_router(registry: NodeRegistry = None, http_client: HttpClient = None) -> Router:
    """创建路由器"""
    if registry is None:
        from registry import create_registry
        registry = create_registry()
    if http_client is None:
        http_client = HttpClient()
    return Router(registry, http_client)