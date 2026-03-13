# -*- coding: utf-8 -*-
"""
SSH 客户端 - 通过 SSH 在远程服务器执行 OpenClaw 命令
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Optional, Any, List
import asyncssh


@dataclass
class SSHResponse:
    """SSH 执行结果"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    error: str = ""
    latency_ms: int = 0


class SSHClient:
    """SSH 客户端"""

    def __init__(self, timeout: int = 120):
        self.timeout = timeout

    async def connect(
        self,
        host: str,
        username: str,
        password: str = None,
        key_filename: str = None,
        port: int = 22
    ) -> bool:
        """测试 SSH 连接"""
        try:
            async with asyncssh.connect(
                host=host,
                username=username,
                password=password,
                known_hosts=None,
                client_keys=[key_filename] if key_filename else None,
                server_host_key_algs=['ssh-rsa', 'rsa-sha2-256', 'rsa-sha2-512'],
                port=port
            ) as conn:
                return True
        except Exception as e:
            print(f"SSH 连接失败: {e}")
            return False

    async def execute(
        self,
        host: str,
        username: str,
        command: str,
        password: str = None,
        key_filename: str = None,
        port: int = 22,
        timeout: int = 120
    ) -> SSHResponse:
        """在远程服务器执行命令"""
        start = time.time()
        
        try:
            async with asyncssh.connect(
                host=host,
                username=username,
                password=password,
                known_hosts=None,
                client_keys=[key_filename] if key_filename else None,
                server_host_key_algs=['ssh-rsa', 'rsa-sha2-256', 'rsa-sha2-512'],
                port=port
            ) as conn:
                result = await conn.run(command, timeout=timeout)
                latency = int((time.time() - start) * 1000)
                
                return SSHResponse(
                    success=result.exit_status == 0,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    latency_ms=latency
                )
                
        except asyncssh.ProcessError as e:
            return SSHResponse(
                success=False,
                error=f"进程错误: {e}",
                latency_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            return SSHResponse(
                success=False,
                error=str(e),
                latency_ms=int((time.time() - start) * 1000)
            )

    async def execute_openclaw(
        self,
        host: str,
        username: str,
        message: str,
        password: str = None,
        key_filename: str = None,
        port: int = 22,
        openclaw_path: str = "/usr/local/bin/openclaw"
    ) -> SSHResponse:
        """在远程服务器执行 OpenClaw 命令"""
        # 构建消息文件，避免 shell 转义问题
        cmd = f'''
cd ~/.openclaw/workspace && {openclaw_path} send --message "{message}" --channel self 2>&1
'''
        return await self.execute(host, username, cmd, password, key_filename, port, timeout=120)

    async def get_remote_status(
        self,
        host: str,
        username: str,
        password: str = None,
        key_filename: str = None,
        port: int = 22
    ) -> SSHResponse:
        """获取远程 OpenClaw 状态"""
        cmd = "openclaw status 2>&1 || echo 'openclaw not found'"
        return await self.execute(host, username, cmd, password, key_filename, port, timeout=30)