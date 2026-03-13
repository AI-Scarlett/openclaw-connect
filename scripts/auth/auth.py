# -*- coding: utf-8 -*-
"""
认证系统 - AppID + Token + Key 三层认证
"""

import hashlib
import hmac
import secrets
import time
import json
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from pathlib import Path


@dataclass
class NodeCredential:
    """节点凭证"""
    app_id: str
    name: str
    role: str = "node"  # master | node
    token: str = ""  # 长期凭证（30天）
    key: str = ""  # 短期密钥（7天）
    token_expires: float = 0
    key_expires: float = 0
    ip: str = ""
    capabilities: List[str] = field(default_factory=list)
    status: str = "offline"
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)


@dataclass
class AuthConfig:
    """认证配置"""
    role: str = "node"  # master | node
    app_id: str = ""
    token: str = ""
    key: str = ""
    token_expires: float = 0
    key_expires: float = 0
    master_url: str = ""
    token_valid_days: int = 30
    key_valid_days: int = 7


class AuthSystem:
    """认证系统"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            skill_dir = Path(__file__).parent.parent
            config_path = skill_dir / "config" / "auth.json"
        
        self.config_path = Path(config_path)
        self.nodes: Dict[str, NodeCredential] = {}
        self.config = AuthConfig()
        self._load()

    def _load(self):
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 加载配置
                    if 'config' in data:
                        c = data['config']
                        self.config = AuthConfig(
                            role=c.get('role', 'node'),
                            app_id=c.get('app_id', ''),
                            token=c.get('token', ''),
                            key=c.get('key', ''),
                            master_url=c.get('master_url', ''),
                            token_valid_days=c.get('token_valid_days', 30),
                            key_valid_days=c.get('key_valid_days', 7)
                        )
                    
                    # 加载节点
                    if 'nodes' in data:
                        for n in data['nodes']:
                            node = NodeCredential(
                                app_id=n['app_id'],
                                name=n.get('name', ''),
                                role=n.get('role', 'node'),
                                token=n.get('token', ''),
                                key=n.get('key', ''),
                                token_expires=n.get('token_expires', 0),
                                key_expires=n.get('key_expires', 0),
                                ip=n.get('ip', ''),
                                capabilities=n.get('capabilities', []),
                                status=n.get('status', 'offline'),
                                created_at=n.get('created_at', time.time()),
                                last_active=n.get('last_active', time.time())
                            )
                            self.nodes[n['app_id']] = node
            except Exception as e:
                print(f"加载配置失败: {e}")

    def _save(self):
        """保存配置"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'config': {
                'role': self.config.role,
                'app_id': self.config.app_id,
                'token': self.config.token,
                'key': self.config.key,
                'master_url': self.config.master_url,
                'token_valid_days': self.config.token_valid_days,
                'key_valid_days': self.config.key_valid_days
            },
            'nodes': [
                {
                    'app_id': n.app_id,
                    'name': n.name,
                    'role': n.role,
                    'token': n.token,
                    'key': n.key,
                    'token_expires': n.token_expires,
                    'key_expires': n.key_expires,
                    'ip': n.ip,
                    'capabilities': n.capabilities,
                    'status': n.status,
                    'created_at': n.created_at,
                    'last_active': n.last_active
                }
                for n in self.nodes.values()
            ]
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ==================== 凭证生成 ====================

    def generate_token(self, length: int = 32) -> str:
        """生成 Token（长期）"""
        return secrets.token_urlsafe(length)

    def generate_key(self, length: int = 24) -> str:
        """生成 Key（短期）"""
        return secrets.token_urlsafe(length)

    def generate_app_id(self, name: str, role: str = "node") -> str:
        """生成 AppID"""
        prefix = "master" if role == "master" else "node"
        suffix = hashlib.md5(name.encode()).hexdigest()[:6]
        return f"{prefix}_{suffix}"

    # ==================== 主核心初始化 ====================

    def init_master(self, name: str = "master") -> Dict:
        """初始化为主核心"""
        app_id = self.generate_app_id(name, "master")
        token = self.generate_token()
        
        self.config = AuthConfig(
            role="master",
            app_id=app_id,
            token=token,
            token_expires=time.time() + 30 * 86400,
            token_valid_days=30
        )
        
        # 添加主节点到列表
        master_node = NodeCredential(
            app_id=app_id,
            name=name,
            role="master",
            token=token,
            token_expires=self.config.token_expires,
            ip="localhost",
            capabilities=["*"],
            status="online"
        )
        self.nodes[app_id] = master_node
        self._save()
        
        return {
            "success": True,
            "app_id": app_id,
            "token": token,
            "token_expires": self.config.token_expires,
            "message": f"主核心初始化成功，Token 有效期 30 天"
        }

    # ==================== 子节点注册 ====================

    def register_node(
        self,
        name: str,
        ip: str = "",
        capabilities: List[str] = None
    ) -> Dict:
        """注册子节点"""
        app_id = self.generate_app_id(name)
        key = self.generate_key()
        key_expires = time.time() + 7 * 86400  # 7天
        
        node = NodeCredential(
            app_id=app_id,
            name=name,
            role="node",
            key=key,
            key_expires=key_expires,
            ip=ip,
            capabilities=capabilities or [],
            status="online",
            last_active=time.time()
        )
        
        self.nodes[app_id] = node
        self._save()
        
        return {
            "success": True,
            "app_id": app_id,
            "key": key,
            "key_expires": key_expires,
            "message": f"节点 {name} 注册成功，Key 有效期 7 天"
        }

    def unregister_node(self, app_id: str) -> bool:
        """注销节点"""
        if app_id in self.nodes and self.nodes[app_id].role != "master":
            del self.nodes[app_id]
            self._save()
            return True
        return False

    # ==================== 认证验证 ====================

    def verify_app_id(self, app_id: str) -> bool:
        """验证 AppID 是否存在"""
        return app_id in self.nodes

    def verify_token(self, app_id: str, token: str) -> bool:
        """验证 Token（主核心用）"""
        node = self.nodes.get(app_id)
        if not node:
            return False
        
        if node.role != "master":
            return False
        
        if node.token != token:
            return False
        
        if time.time() > node.token_expires:
            return False
        
        return True

    def verify_key(self, app_id: str, key: str) -> bool:
        """验证 Key（子节点用）"""
        node = self.nodes.get(app_id)
        if not node:
            return False
        
        if node.key != key:
            return False
        
        if time.time() > node.key_expires:
            return False
        
        # 更新活跃时间
        node.last_active = time.time()
        node.status = "online"
        self._save()
        
        return True

    def authenticate(self, app_id: str, token: str = None, key: str = None) -> Dict:
        """完整认证流程"""
        # 检查 AppID
        if not self.verify_app_id(app_id):
            return {"success": False, "error": "AppID 不存在"}
        
        node = self.nodes[app_id]
        
        # 验证 Token 或 Key
        if node.role == "master":
            # 主核心用 Token
            if not token or not self.verify_token(app_id, token):
                return {"success": False, "error": "Token 无效或已过期"}
        else:
            # 子节点用 Key
            if not key or not self.verify_key(app_id, key):
                return {
                    "success": False, 
                    "error": "Key 无效或已过期",
                    "key_expires": node.key_expires
                }
        
        return {
            "success": True,
            "app_id": app_id,
            "name": node.name,
            "role": node.role,
            "capabilities": node.capabilities
        }

    # ==================== 节点管理 ====================

    def get_node(self, app_id: str) -> Optional[NodeCredential]:
        """获取节点"""
        return self.nodes.get(app_id)

    def get_node_by_name(self, name: str) -> Optional[NodeCredential]:
        """通过名称获取节点"""
        for node in self.nodes.values():
            if node.name == name:
                return node
        return None

    def list_nodes(self) -> List[NodeCredential]:
        """列出所有节点"""
        return list(self.nodes.values())

    def get_online_nodes(self) -> List[NodeCredential]:
        """获取在线节点"""
        return [n for n in self.nodes.values() if n.status == "online"]

    def refresh_key(self, app_id: str) -> Dict:
        """刷新 Key"""
        node = self.nodes.get(app_id)
        if not node:
            return {"success": False, "error": "节点不存在"}
        
        node.key = self.generate_key()
        node.key_expires = time.time() + self.config.key_valid_days * 86400
        self._save()
        
        return {
            "success": True,
            "key": node.key,
            "key_expires": node.key_expires
        }

    def refresh_token(self) -> Dict:
        """刷新 Token（仅主核心）"""
        if self.config.role != "master":
            return {"success": False, "error": "只有主核心可以刷新 Token"}
        
        app_id = self.config.app_id
        node = self.nodes.get(app_id)
        if not node:
            return {"success": False, "error": "主核心未初始化"}
        
        node.token = self.generate_token()
        node.token_expires = time.time() + self.config.token_valid_days * 86400
        self.config.token = node.token
        self.config.token_expires = node.token_expires
        self._save()
        
        return {
            "success": True,
            "token": node.token,
            "token_expires": node.token_expires
        }

    # ==================== 子节点初始化 ====================

    def init_node(self, master_url: str, app_id: str, key: str) -> Dict:
        """初始化为子节点"""
        # 验证 Key
        if not self.verify_key(app_id, key):
            return {"success": False, "error": "Key 验证失败"}
        
        self.config = AuthConfig(
            role="node",
            app_id=app_id,
            key=key,
            master_url=master_url
        )
        self._save()
        
        return {"success": True, "message": "子节点初始化成功"}


# ==================== 便捷函数 ====================

def create_auth(config_path: str = None) -> AuthSystem:
    """创建认证系统"""
    return AuthSystem(config_path)


def init_master(name: str = "master", config_path: str = None) -> Dict:
    """快速初始化主核心"""
    auth = AuthSystem(config_path)
    return auth.init_master(name)


def register_node(name: str, ip: str = "", capabilities: List[str] = None, config_path: str = None) -> Dict:
    """快速注册节点"""
    auth = AuthSystem(config_path)
    return auth.register_node(name, ip, capabilities)