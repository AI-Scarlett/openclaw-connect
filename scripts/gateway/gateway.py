# -*- coding: utf-8 -*-
"""
网关服务 - 提供 REST API 供其他节点调用
"""

import json
import asyncio
import aiohttp
from aiohttp import web
from typing import Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class Gateway:
    """协作网关服务"""

    def __init__(self, auth_system, node_registry):
        self.auth = auth_system
        self.registry = node_registry
        self.app = web.Application()
        self._setup_routes()
        self.runner: Optional[web.AppRunner] = None

    def _setup_routes(self):
        """设置路由"""
        # 健康检查
        self.app.router.add_get('/health', self.handle_health)
        
        # 认证
        self.app.router.add_post('/api/auth/login', self.handle_login)
        self.app.router.add_post('/api/auth/logout', self.handle_logout)
        
        # 节点管理
        self.app.router.add_get('/api/node/info', self.handle_node_info)
        self.app.router.add_post('/api/node/heartbeat', self.handle_heartbeat)
        self.app.router.add_get('/api/node/list', self.handle_node_list)
        
        # 任务分发
        self.app.router.add_post('/api/agent/turn', self.handle_agent_turn)
        
        # 数据同步
        self.app.router.add_post('/api/sync/push', self.handle_sync_push)
        self.app.router.add_get('/api/sync/pull/{key}', self.handle_sync_pull)

    # ==================== 处理器 ====================

    async def handle_health(self, request):
        """健康检查"""
        return web.json_response({
            "status": "ok",
            "service": "openclaw-connect",
            "role": self.auth.config.role
        })

    async def handle_login(self, request):
        """登录"""
        try:
            data = await request.json()
            app_id = data.get('app_id', '')
            key = data.get('key', '')
            
            result = self.auth.verify_key(app_id, key)
            if result:
                node = self.auth.get_node(app_id)
                return web.json_response({
                    "success": True,
                    "app_id": app_id,
                    "name": node.name if node else "",
                    "role": node.role if node else ""
                })
            return web.json_response({"success": False, "error": "认证失败"}, status=401)
        except Exception as e:
            logger.error(f"登录错误: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def handle_logout(self, request):
        """登出"""
        return web.json_response({"success": True})

    async def handle_node_info(self, request):
        """获取节点信息"""
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return web.json_response({"error": "未授权"}, status=401)
        
        try:
            app_id, key = auth[7:].split(':')
            if not self.auth.verify_key(app_id, key):
                return web.json_response({"error": "认证失败"}, status=401)
            
            node = self.auth.get_node(app_id)
            if not node:
                return web.json_response({"error": "节点不存在"}, status=404)
            
            return web.json_response({
                "app_id": node.app_id,
                "name": node.name,
                "role": node.role,
                "capabilities": node.capabilities,
                "status": node.status
            })
        except:
            return web.json_response({"error": "认证格式错误"}, status=400)

    async def handle_heartbeat(self, request):
        """心跳"""
        try:
            data = await request.json()
            app_id = data.get('app_id', '')
            key = data.get('key', '')
            load = data.get('load', 0.0)
            
            if not self.auth.verify_key(app_id, key):
                return web.json_response({"error": "认证失败"}, status=401)
            
            # 更新节点状态
            self.registry.heartbeat(app_id, load=load)
            self.auth.nodes[app_id].last_active = time.time()
            
            return web.json_response({"success": True})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_node_list(self, request):
        """获取节点列表"""
        auth = request.headers.get('Authorization', '')
        if not auth:
            return web.json_response({"error": "未授权"}, status=401)
        
        try:
            # 简单验证
            if not auth.startswith('Bearer '):
                return web.json_response({"error": "认证格式错误"}, status=400)
            
            nodes = self.registry.list_all()
            return web.json_response({
                "nodes": [
                    {
                        "app_id": n.app_id,
                        "name": n.name,
                        "role": n.role,
                        "ip": n.ip,
                        "status": n.status,
                        "capabilities": n.capabilities
                    }
                    for n in nodes
                ]
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_agent_turn(self, request):
        """任务处理"""
        try:
            data = await request.json()
            app_id = data.get('app_id', '')
            key = data.get('key', '')
            message = data.get('message', '')
            
            # 验证
            if not self.auth.verify_key(app_id, key):
                return web.json_response({"error": "认证失败"}, status=401)
            
            # 获取节点
            node = self.auth.get_node(app_id)
            if not node:
                return web.json_response({"error": "节点不存在"}, status=404)
            
            # 检查主核心权限
            if self.auth.config.role != "master":
                return web.json_response({"error": "只有主核心可以处理任务"}, status=403)
            
            # 这里可以调用实际的 OpenClaw 执行任务
            # 目前返回模拟响应
            response = {
                "success": True,
                "message": f"任务已接收: {message[:50]}...",
                "node": node.name,
                "app_id": app_id
            }
            
            return web.json_response(response)
            
        except Exception as e:
            logger.error(f"任务处理错误: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_sync_push(self, request):
        """同步数据"""
        try:
            data = await request.json()
            app_id = data.get('app_id', '')
            key = data.get('key', '')
            sync_data = data.get('data', {})
            
            if not self.auth.verify_key(app_id, key):
                return web.json_response({"error": "认证失败"}, status=401)
            
            # 存储数据（这里简化为内存存储）
            # 实际应该用数据库
            if not hasattr(self, '_sync_store'):
                self._sync_store = {}
            
            self._sync_store.update(sync_data)
            
            return web.json_response({"success": True})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_sync_pull(self, request):
        """拉取数据"""
        auth = request.headers.get('Authorization', '')
        key_name = request.match_info['key']
        
        if not auth.startswith('Bearer '):
            return web.json_response({"error": "未授权"}, status=401)
        
        try:
            if not hasattr(self, '_sync_store'):
                self._sync_store = {}
            
            data = self._sync_store.get(key_name, {})
            return web.json_response({"data": data})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ==================== 服务控制 ====================

    async def start(self, host: str = "0.0.0.0", port: int = 18790):
        """启动网关"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        site = web.TCPSite(self.runner, host, port)
        await site.start()
        
        logger.info(f"网关启动: http://{host}:{port}")
        return f"http://{host}:{port}"

    async def stop(self):
        """停止网关"""
        if self.runner:
            await self.runner.cleanup()
            logger.info("网关已停止")


import time

# ==================== 便捷函数 ====================

async def start_gateway(auth_system, node_registry, host: str = "0.0.0.0", port: int = 18790):
    """快速启动网关"""
    gateway = Gateway(auth_system, node_registry)
    url = await gateway.start(host, port)
    return gateway, url


def create_gateway(config_path: str = None) -> Gateway:
    """创建网关"""
    from .auth.auth import create_auth
    from .registry import create_registry
    
    auth = create_auth(config_path)
    registry = create_registry(config_path)
    return Gateway(auth, registry)