# -*- coding: utf-8 -*-
"""
OpenClaw Connect CLI - 集成到 OpenClaw Gateway
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

# 添加 scripts 目录到路径
_script_dir = Path(__file__).parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from connect import OpenClawConnect


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Connect - 安全协作连接器")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 启动网关
    start_parser = subparsers.add_parser("start", help="启动协作网关")
    start_parser.add_argument("--host", default="0.0.0.0", help="绑定地址")
    start_parser.add_argument("--port", type=int, default=18790, help="端口")
    
    # 添加节点
    add_parser = subparsers.add_parser("add-node", help="添加子节点")
    add_parser.add_argument("--name", required=True, help="节点名称")
    add_parser.add_argument("--ip", required=True, help="节点 IP")
    add_parser.add_argument("--port", type=int, default=18789, help="节点端口")
    add_parser.add_argument("--capabilities", nargs="+", default=[], help="节点能力")
    
    # 列出节点
    subparsers.add_parser("list-nodes", help="列出所有节点")
    
    # 移除节点
    remove_parser = subparsers.add_parser("remove-node", help="移除节点")
    remove_parser.add_argument("--app-id", required=True, help="节点 AppID")
    
    # 测试连接
    test_parser = subparsers.add_parser("test", help="测试连接")
    test_parser.add_argument("--node", help="指定节点名称")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    connect = OpenClawConnect()
    
    if args.command == "start":
        print(f"启动 OpenClaw Connect Gateway: {args.host}:{args.port}")
        asyncio.run(_start_gateway(connect, args.host, args.port))
        
    elif args.command == "add-node":
        result = connect.add_node(args.name, args.ip, args.port, args.capabilities)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    elif args.command == "list-nodes":
        import json
        with open(connect.config_path / "auth.json") as f:
            config = json.load(f)
        nodes = config.get("nodes", [])
        print(f"节点列表 ({len(nodes)} 个):")
        for node in nodes:
            print(f"  - {node['name']} ({node['app_id']})")
            print(f"    角色: {node['role']}, IP: {node['ip']}, 状态: {node['status']}")
            
    elif args.command == "remove-node":
        result = connect.remove_node(args.app_id)
        print(f"移除节点: {'成功' if result else '失败'}")
        
    elif args.command == "test":
        asyncio.run(_test_connection(connect, args.node))


async def _start_gateway(connect, host, port):
    """启动网关"""
    url = await connect.start_gateway(host, port)
    print(f"✅ Gateway 已启动: {url}")
    print("按 Ctrl+C 停止...")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await connect.stop_gateway()
        print("\n✅ Gateway 已停止")


async def _test_connection(connect, node_name=None):
    """测试连接"""
    import aiohttp
    
    await connect.start_gateway()
    await asyncio.sleep(0.5)
    
    async with aiohttp.ClientSession() as session:
        # 获取节点列表
        with open(connect.config_path / "auth.json") as f:
            config = json.load(f)
            master_token = config["config"]["token"]
        
        headers = {"Authorization": f"Bearer {master_token}"}
        
        async with session.get(
            "http://localhost:18790/api/node/list",
            headers=headers
        ) as resp:
            data = await resp.json()
            print(f"节点列表: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    await connect.stop_gateway()
    print("✅ 测试完成")


if __name__ == "__main__":
    main()