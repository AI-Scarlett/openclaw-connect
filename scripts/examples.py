# -*- coding: utf-8 -*-
"""
OpenClaw Connect 最简使用示例
用户只需要提供 SSH 信息，就能控制远程服务器的 OpenClaw
"""

import asyncio
from connect import OpenClawConnect


async def example_add_node():
    """示例：添加远程节点（只需 SSH 信息）"""
    connect = OpenClawConnect()
    
    # 添加节点 - 只需提供 SSH 信息
    result = await connect.add_node(
        name="上海服务器",
        host="192.168.1.100",  # 服务器 IP
        username="root",
        password="your_password",  # 或使用 key_path
        key_path="/root/.ssh/id_rsa",
        location="上海",
        region="华东"
    )
    
    print(result)
    # {'success': True, 'node_id': 'node-shanghai-001', 'message': '节点 上海服务器 添加成功'}


async def example_dispatch():
    """示例：分发任务到远程节点"""
    async with OpenClawConnect() as connect:
        # 分发任务 - 就像本地任务一样
        result = await connect.dispatch(
            node="上海服务器",  # 或使用 node_id: "node-shanghai-001"
            message="帮我查一下当前时间"
        )
        
        print(f"节点: {result.node_name}")
        print(f"成功: {result.success}")
        print(f"延迟: {result.latency_ms}ms")
        print(f"输出: {result.output[:500]}")


async def example_broadcast():
    """示例：广播任务到所有节点"""
    async with OpenClawConnect() as connect:
        # 广播到所有服务器
        results = await connect.broadcast(
            message="搜索最新的 AI 新闻",
            select="fastest"  # 返回最快响应
        )
        
        for r in results:
            print(f"{r.node_name}: {'✅' if r.success else '❌'} ({r.latency_ms}ms)")


async def example_status():
    """示例：查看所有节点状态"""
    async with OpenClawConnect() as connect:
        statuses = await connect.status()
        
        print("=" * 50)
        print("节点状态")
        print("=" * 50)
        for s in statuses:
            status_icon = "🟢" if s["status"] == "online" else "🔴"
            print(f"{status_icon} {s['name']}")
            print(f"   位置: {s['location']} ({s['region']})")
            print(f"   状态: {s['status']}")
            print(f"   延迟: {s['latency_ms']}ms")
            print()


# ==================== 最简用法 ====================

async def simplest_usage():
    """
    最简用法：一步添加节点 + 执行任务
    """
    connect = OpenClawConnect()
    
    # 1. 添加节点（可选，首次需要）
    # 之后节点信息会保存到配置文件
    
    # 2. 分发任务
    result = await connect.dispatch(
        node="本地服务器",  # 节点名称
        message="你好，请回复 '收到'"
    )
    
    print(f"结果: {result.output[:200] if result.success else result.error}")


if __name__ == "__main__":
    # 运行最简示例
    asyncio.run(simplest_usage())