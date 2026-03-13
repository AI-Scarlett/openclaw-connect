---
name: openclaw-connect
version: 1.0.0
description: OpenClaw 多实例协作连接器 - 最简方案，通过 SSH 控制远程服务器上的 OpenClaw
---

# openclaw-connect v1.0.0

> 最简单的多服务器 OpenClaw 联合协作方案

## 🎯 特点

- **零额外配置** - 不需要开启 Gateway 外网访问
- **SSH 即插即用** - 只需提供服务器 SSH 登录信息
- **一键添加节点** - 添加节点只需 3 行代码
- **统一任务分发** - 像本地任务一样分发到远程

## 📡 工作原理

```
本地 OpenClaw ──SSH──► 远程服务器 ──► OpenClaw 命令
                              │
                              └─► 执行任务，结果返回
```

通过 SSH 在远程服务器执行 `openclaw send` 命令，实现任务分发。

## 🚀 使用方式

```python
from scripts.connect import OpenClawConnect

# 初始化
connect = OpenClawConnect()

# 添加节点（首次需要）
await connect.add_node(
    name="上海服务器",
    host="192.168.1.100",
    username="root",
    password="xxx",  # 或使用 key_path
    location="上海"
)

# 分发任务（和本地一样简单）
result = await connect.dispatch(
    node="上海服务器",
    message="帮我写一首诗"
)

# 查看所有节点状态
statuses = await connect.status()
```

## ⚙️ 配置

节点信息保存在 `config/nodes.json`：

```json
{
  "ssh_nodes": [
    {
      "id": "node-001",
      "name": "服务器名称",
      "host": "192.168.1.100",
      "username": "root",
      "password": "xxx",
      "port": 22,
      "location": "城市",
      "region": "区域"
    }
  ]
}
```

## ⚡ 注意

- 需要远程服务器开启 SSH 访问
- 建议使用 SSH 密钥认证，更安全
- 确保 SSH 用户有权限执行 openclaw 命令

---

*By 斯嘉丽 Scarlett*
*一句话：把远程服务器变成你的计算节点！*