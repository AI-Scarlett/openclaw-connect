# -*- coding: utf-8 -*-
"""
节点注册表 - 管理协作网络中的所有节点
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class Node:
    """协作节点"""
    app_id: str
    name: str
    role: str  # master | node
    ip: str
    port: int = 18789
    url: str = ""
    capabilities: List[str] = None
    status: str = "offline"  # online | offline | busy
    latency_ms: int = 0
    load: float = 0.0  # 0-1 负载
    last_heartbeat: float = 0
    created_at: float = 0
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.created_at == 0:
            self.created_at = time.time()
        if not self.url and self.ip:
            self.url = f"http://{self.ip}:{self.port}"


class NodeRegistry:
    """节点注册表"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            skill_dir = Path(__file__).parent.parent
            config_path = skill_dir / "config" / "nodes.json"
        
        self.config_path = Path(config_path)
        self.nodes: Dict[str, Node] = {}
        self._load()

    def _load(self):
        """加载节点"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 兼容旧格式
                nodes_data = data.get('nodes', data.get('ssh_nodes', []))
                for n in nodes_data:
                    node = Node(
                        app_id=n.get('app_id', n.get('id', '')),
                        name=n.get('name', ''),
                        role=n.get('role', 'node'),
                        ip=n.get('ip', n.get('host', '')),
                        port=n.get('port', 18789),
                        url=n.get('url', ''),
                        capabilities=n.get('capabilities', []),
                        status=n.get('status', 'offline'),
                        latency_ms=n.get('latency_ms', 0),
                        load=n.get('load', 0.0),
                        last_heartbeat=n.get('last_heartbeat', 0),
                        created_at=n.get('created_at', time.time())
                    )
                    self.nodes[node.app_id] = node
            except Exception as e:
                print(f"加载节点失败: {e}")

    def _save(self):
        """保存节点"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            'nodes': [
                {
                    'app_id': n.app_id,
                    'name': n.name,
                    'role': n.role,
                    'ip': n.ip,
                    'port': n.port,
                    'url': n.url,
                    'capabilities': n.capabilities,
                    'status': n.status,
                    'latency_ms': n.latency_ms,
                    'load': n.load,
                    'last_heartbeat': n.last_heartbeat,
                    'created_at': n.created_at
                }
                for n in self.nodes.values()
            ]
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ==================== 节点管理 ====================

    def register(self, node: Node) -> Node:
        """注册节点"""
        self.nodes[node.app_id] = node
        self._save()
        return node

    def unregister(self, app_id: str) -> bool:
        """注销节点"""
        if app_id in self.nodes and self.nodes[app_id].role != "master":
            del self.nodes[app_id]
            self._save()
            return True
        return False

    def get(self, app_id: str) -> Optional[Node]:
        """获取节点"""
        return self.nodes.get(app_id)

    def get_by_name(self, name: str) -> Optional[Node]:
        """通过名称获取"""
        for node in self.nodes.values():
            if node.name == name:
                return node
        return None

    def list_all(self) -> List[Node]:
        """列出所有节点"""
        return list(self.nodes.values())

    def list_online(self) -> List[Node]:
        """列出在线节点"""
        return [n for n in self.nodes.values() if n.status == "online"]

    def list_by_capability(self, capability: str) -> List[Node]:
        """按能力筛选"""
        return [
            n for n in self.nodes.values() 
            if n.status == "online" and capability in n.capabilities
        ]

    # ==================== 状态管理 ====================

    def heartbeat(self, app_id: str, latency_ms: int = 0, load: float = 0.0) -> bool:
        """更新心跳"""
        if app_id in self.nodes:
            node = self.nodes[app_id]
            node.last_heartbeat = time.time()
            node.latency_ms = latency_ms
            node.load = load
            node.status = "online"
            self._save()
            return True
        return False

    def set_offline(self, app_id: str):
        """设置离线"""
        if app_id in self.nodes:
            self.nodes[app_id].status = "offline"
            self._save()

    def set_busy(self, app_id: str):
        """设置忙碌"""
        if app_id in self.nodes:
            self.nodes[app_id].status = "busy"
            self._save()

    def set_idle(self, app_id: str):
        """设置空闲"""
        if app_id in self.nodes:
            self.nodes[app_id].status = "online"
            self._save()

    # ==================== 选择器 ====================

    def select_by_load(self) -> Optional[Node]:
        """选择负载最低的节点"""
        online = self.list_online()
        if not online:
            return None
        
        online.sort(key=lambda x: x.load)
        return online[0]

    def select_by_latency(self) -> Optional[Node]:
        """选择延迟最低的节点"""
        online = self.list_online()
        if not online:
            return None
        
        online.sort(key=lambda x: x.latency_ms)
        return online[0]

    def select_round_robin(self) -> Optional[Node]:
        """轮询选择（简单实现）"""
        online = self.list_online()
        if not online:
            return None
        
        # 简单轮询：选择第一个
        return online[0]

    def select_best(self, strategy: str = "load") -> Optional[Node]:
        """最佳选择"""
        if strategy == "load":
            return self.select_by_load()
        elif strategy == "latency":
            return self.select_by_latency()
        elif strategy == "round_robin":
            return self.select_round_robin()
        return self.select_by_load()


# ==================== 便捷函数 ====================

def create_registry(config_path: str = None) -> NodeRegistry:
    """创建注册表"""
    return NodeRegistry(config_path)