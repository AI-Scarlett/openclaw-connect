# -*- coding: utf-8 -*-
"""
OpenClaw Connect - 安全协作连接器
主入口：一行代码实现多节点任务分发
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import sys
from pathlib import Path

# 添加scripts目录到路径
_script_dir = Path(__file__).parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from auth.auth import AuthSystem, init_master, register_node
from registry import NodeRegistry
from http_client import HttpClient
from router import Router, TaskRequest
from gateway.gateway import Gateway


class OpenClawConnect:
    """OpenClaw 安全协作连接器"""

    def __init__(self, config_path: str = None):
        """
        初始化连接器
        
        Args:
            config_path: 配置文件路径
        """
        if config_path is None:
            skill_dir = Path(__file__).parent.parent
            config_path = skill_dir / "config"
        
        self.config_path = Path(config_path)
        self.auth = AuthSystem(str(self.config_path / "auth.json"))
        self.registry = NodeRegistry(str(self.config_path / "nodes.json"))
        self.http = HttpClient()
        self.router = Router(self.registry, self.http)
        self.gateway: Optional[Gateway] = None

    # ==================== 主核心操作 ====================

    def init_as_master(self, name: str = "master") -> Dict:
        """初始化为主核心"""
        return self.auth.init_master(name)

    def add_node(
        self,
        name: str,
        ip: str,
        port: int = 18789,
        capabilities: List[str] = None
    ) -> Dict:
        """添加子节点"""
        result = self.auth.register_node(name, ip, capabilities)
        
        if result.get("success"):
            # 同时添加到注册表
            from .registry import Node
            node = Node(
                app_id=result["app_id"],
                name=name,
                role="node",
                ip=ip,
                port=port,
                url=f"http://{ip}:{port}",
                capabilities=capabilities or []
            )
            self.registry.register(node)
        
        return result

    def remove_node(self, app_id: str) -> bool:
        """移除节点"""
        self.auth.unregister_node(app_id)
        return self.registry.unregister(app_id)

    # ==================== 网关操作 ====================

    async def start_gateway(self, host: str = "0.0.0.0", port: int = 18790) -> str:
        """启动协作网关"""
        self.gateway = Gateway(self.auth, self.registry)
        return await self.gateway.start(host, port)

    async def stop_gateway(self):
        """停止网关"""
        if self.gateway:
            await self.gateway.stop()

    # ==================== 任务分发 ====================

    async def dispatch(
        self,
        node: str,
        message: str,
        timeout: int = 120
    ) -> Dict:
        """
        分发任务到指定节点
        
        Args:
            node: 节点名称或 AppID
            message: 任务消息
            timeout: 超时时间（秒）
        
        Returns:
            任务结果
        """
        # 查找节点
        node_obj = self.auth.get_node_by_name(node)
        if not node_obj:
            node_obj = self.auth.get_node(node)
        
        if not node_obj:
            return {"success": False, "error": f"节点 {node} 不存在"}
        
        # 通过 HTTP 调用
        response = await self.http.dispatch(
            url=f"http://{node_obj.ip}:18789",
            app_id=node_obj.app_id,
            key=node_obj.key,
            message=message,
            timeout=timeout
        )
        
        return {
            "success": response.success,
            "node": node_obj.name,
            "app_id": node_obj.app_id,
            "data": response.data,
            "error": response.error,
            "latency_ms": response.latency_ms
        }

    async def broadcast(
        self,
        message: str,
        timeout: int = 30,
        select: str = "fastest"
    ) -> List[Dict]:
        """
        广播任务到所有节点
        
        Args:
            message: 任务消息
            timeout: 超时时间
            select: "fastest" 或 "all"
        
        Returns:
            结果列表
        """
        # 通过路由广播
        request = TaskRequest(message=message, timeout=timeout)
        
        # 获取主核心凭证
        if not self.auth.config.app_id:
            return [{"success": False, "error": "未初始化为主核心"}]
        
        results = await self.router.broadcast(
            request,
            self.auth.config.app_id,
            self.auth.config.key,
            select
        )
        
        return [
            {
                "success": r.success,
                "node": r.node_name,
                "app_id": r.node_app_id,
                "data": r.data,
                "error": r.error,
                "latency_ms": r.latency_ms
            }
            for r in results
        ]

    # ==================== 节点管理 ====================

    def list_nodes(self) -> List[Dict]:
        """列出所有节点"""
        nodes = self.auth.list_nodes()
        return [
            {
                "app_id": n.app_id,
                "name": n.name,
                "role": n.role,
                "ip": n.ip,
                "status": n.status,
                "capabilities": n.capabilities,
                "key_expires": n.key_expires
            }
            for n in nodes
        ]

    async def status(self) -> List[Dict]:
        """获取节点状态"""
        nodes = self.auth.list_nodes()
        statuses = []
        
        for node in nodes:
            # Ping 节点
            url = f"http://{node.ip}:18789"
            response = await self.http.ping(url)
            
            statuses.append({
                "app_id": node.app_id,
                "name": node.name,
                "role": node.role,
                "ip": node.ip,
                "status": "online" if response.success else "offline",
                "latency_ms": response.latency_ms,
                "capabilities": node.capabilities
            })
        
        return statuses

    # ==================== 数据同步 ====================

    async def sync_push(self, data: Dict) -> bool:
        """推送数据到主核心"""
        if not self.auth.config.master_url:
            return False
        
        response = await self.http.sync_data(
            self.auth.config.master_url,
            self.auth.config.app_id,
            self.auth.config.key,
            data
        )
        return response.success

    async def sync_pull(self, key: str) -> Dict:
        """从主核心拉取数据"""
        if not self.auth.config.master_url:
            return {}
        
        response = await self.http.pull_data(
            self.auth.config.master_url,
            self.auth.config.app_id,
            self.auth.config.key,
            key
        )
        
        return response.data if response.success else {}

    # ==================== 上下文管理 ====================

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """关闭连接"""
        await self.http.close()
        await self.stop_gateway()


# ==================== 便捷函数 ====================

def create_connect(config_path: str = None) -> OpenClawConnect:
    """创建连接器"""
    return OpenClawConnect(config_path)


async def quick_dispatch(node: str, message: str, config_path: str = None) -> Dict:
    """快速分发任务"""
    async with OpenClawConnect(config_path) as connect:
        return await connect.dispatch(node, message)


async def quick_status(config_path: str = None) -> List[Dict]:
    """快速查看状态"""
    async with OpenClawConnect(config_path) as connect:
        return await connect.status()


# ==================== CLI 入口 ====================

def main():
    """CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenClaw Connect")
    parser.add_argument("command", choices=["init-master", "add-node", "list", "status", "dispatch"])
    parser.add_argument("--name", help="节点名称")
    parser.add_argument("--ip", help="节点 IP")
    parser.add_argument("--message", help="任务消息")
    parser.add_argument("--config", help="配置文件路径")
    
    args = parser.parse_args()
    connect = OpenClawConnect(args.config)
    
    if args.command == "init-master":
        result = connect.init_as_master(args.name or "master")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == "add-node":
        result = connect.add_node(args.name, args.ip)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == "list":
        nodes = connect.list_nodes()
        print(json.dumps(nodes, ensure_ascii=False, indent=2))
    
    elif args.command == "status":
        import asyncio
        statuses = asyncio.run(connect.status())
        print(json.dumps(statuses, ensure_ascii=False, indent=2))
    
    elif args.command == "dispatch":
        import asyncio
        result = asyncio.run(connect.dispatch(args.name, args.message))
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()