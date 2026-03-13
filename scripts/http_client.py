# -*- coding: utf-8 -*-
"""
HTTP 客户端 - 与远程节点通信
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
import aiohttp


@dataclass
class NodeResponse:
    """节点响应"""
    success: bool
    data: Any = None
    error: str = ""
    latency_ms: int = 0


class HttpClient:
    """HTTP 客户端"""

    def __init__(self, timeout: int = 120):
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取 session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """关闭 session"""
        if self._session and not self._session.closed:
            await self._session.close()

    # ==================== 健康检查 ====================

    async def ping(self, url: str) -> NodeResponse:
        """Ping 节点"""
        start = time.time()
        try:
            session = await self._get_session()
            async with session.get(
                f"{url.rstrip('/')}/health",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                latency = int((time.time() - start) * 1000)
                if resp.status == 200:
                    data = await resp.json()
                    return NodeResponse(success=True, data=data, latency_ms=latency)
                return NodeResponse(success=False, error=f"HTTP {resp.status}", latency_ms=latency)
        except Exception as e:
            return NodeResponse(success=False, error=str(e), latency_ms=int((time.time() - start) * 1000))

    # ==================== 认证 ====================

    async def login(self, url: str, app_id: str, key: str) -> NodeResponse:
        """登录节点"""
        start = time.time()
        try:
            session = await self._get_session()
            payload = {"app_id": app_id, "key": key}
            
            async with session.post(
                f"{url.rstrip('/')}/api/auth/login",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                latency = int((time.time() - start) * 1000)
                if resp.status == 200:
                    data = await resp.json()
                    return NodeResponse(success=True, data=data, latency_ms=latency)
                text = await resp.text()
                return NodeResponse(success=False, error=f"HTTP {resp.status}: {text[:100]}", latency_ms=latency)
        except Exception as e:
            return NodeResponse(success=False, error=str(e), latency_ms=int((time.time() - start) * 1000))

    # ==================== 任务分发 ====================

    async def dispatch(
        self,
        url: str,
        app_id: str,
        key: str,
        message: str,
        timeout: int = 120
    ) -> NodeResponse:
        """分发任务"""
        start = time.time()
        try:
            session = await self._get_session()
            payload = {
                "app_id": app_id,
                "key": key,
                "message": message
            }
            headers = {"Content-Type": "application/json"}
            
            async with session.post(
                f"{url.rstrip('/')}/api/agent/turn",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                latency = int((time.time() - start) * 1000)
                if resp.status == 200:
                    data = await resp.json()
                    return NodeResponse(success=True, data=data, latency_ms=latency)
                text = await resp.text()
                return NodeResponse(success=False, error=f"HTTP {resp.status}: {text[:200]}", latency_ms=latency)
        except asyncio.TimeoutError:
            return NodeResponse(success=False, error="Timeout", latency_ms=int((time.time() - start) * 1000))
        except Exception as e:
            return NodeResponse(success=False, error=str(e), latency_ms=int((time.time() - start) * 1000))

    # ==================== 节点信息 ====================

    async def get_info(self, url: str, app_id: str, key: str) -> NodeResponse:
        """获取节点信息"""
        start = time.time()
        try:
            session = await self._get_session()
            headers = {
                "Authorization": f"Bearer {app_id}:{key}",
                "Content-Type": "application/json"
            }
            
            async with session.get(
                f"{url.rstrip('/')}/api/node/info",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                latency = int((time.time() - start) * 1000)
                if resp.status == 200:
                    data = await resp.json()
                    return NodeResponse(success=True, data=data, latency_ms=latency)
                return NodeResponse(success=False, error=f"HTTP {resp.status}", latency_ms=latency)
        except Exception as e:
            return NodeResponse(success=False, error=str(e), latency_ms=int((time.time() - start) * 1000))

    # ==================== 心跳 ====================

    async def heartbeat(self, url: str, app_id: str, key: str, load: float = 0.0) -> NodeResponse:
        """发送心跳"""
        start = time.time()
        try:
            session = await self._get_session()
            payload = {"app_id": app_id, "key": key, "load": load}
            
            async with session.post(
                f"{url.rstrip('/')}/api/node/heartbeat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                latency = int((time.time() - start) * 1000)
                if resp.status == 200:
                    return NodeResponse(success=True, latency_ms=latency)
                return NodeResponse(success=False, error=f"HTTP {resp.status}", latency_ms=latency)
        except Exception as e:
            return NodeResponse(success=False, error=str(e), latency_ms=int((time.time() - start) * 1000))

    # ==================== 数据同步 ====================

    async def sync_data(self, url: str, app_id: str, key: str, data: Dict) -> NodeResponse:
        """同步数据"""
        start = time.time()
        try:
            session = await self._get_session()
            payload = {"app_id": app_id, "key": key, "data": data}
            
            async with session.post(
                f"{url.rstrip('/')}/api/sync/push",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                latency = int((time.time() - start) * 1000)
                if resp.status == 200:
                    return NodeResponse(success=True, latency_ms=latency)
                text = await resp.text()
                return NodeResponse(success=False, error=f"HTTP {resp.status}: {text[:100]}", latency_ms=latency)
        except Exception as e:
            return NodeResponse(success=False, error=str(e), latency_ms=int((time.time() - start) * 1000))

    async def pull_data(self, url: str, app_id: str, key: str, key_name: str) -> NodeResponse:
        """拉取数据"""
        start = time.time()
        try:
            session = await self._get_session()
            headers = {"Authorization": f"Bearer {app_id}:{key}"}
            
            async with session.get(
                f"{url.rstrip('/')}/api/sync/pull/{key_name}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                latency = int((time.time() - start) * 1000)
                if resp.status == 200:
                    data = await resp.json()
                    return NodeResponse(success=True, data=data, latency_ms=latency)
                return NodeResponse(success=False, error=f"HTTP {resp.status}", latency_ms=latency)
        except Exception as e:
            return NodeResponse(success=False, error=str(e), latency_ms=int((time.time() - start) * 1000))