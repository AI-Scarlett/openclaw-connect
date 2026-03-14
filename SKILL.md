# OpenClaw Connect - 安全协作连接器

**多实例 OpenClaw 安全协作系统，支持 AppID + Token + Key 三层认证**

---

## 📋 概述

OpenClaw Connect 是用于多 OpenClaw 实例安全协作的系统，通过 REST API 实现节点发现、任务分发和状态同步。

### 核心特性

- 🔐 **三层认证** - AppID + Token + Key 双重验证
- 🌐 **REST API** - 完整的网关接口
- 📡 **节点管理** - 自动发现和管理远程节点
- 🔄 **任务分发** - 支持跨节点任务调度
- 🛡️ **安全传输** - Token/Key 过期机制

---

## 🚀 快速开始

### 1. 查看节点列表

```bash
cd ~/.openclaw/skills/openclaw-connect
python3 scripts/cli.py list-nodes
```

### 2. 启动网关服务

```bash
# 前台运行
python3 scripts/cli.py start

# 后台运行
./start.sh -d

# 指定端口
./start.sh -p 18790 -d
```

### 3. 添加新节点

```bash
python3 scripts/cli.py add-node \
  --name "北京服务器" \
  --ip "192.168.1.101" \
  --port 18789 \
  --capabilities code search
```

---

## 📖 使用手册

### 角色说明

| 角色 | 说明 | 认证方式 |
|------|------|----------|
| **master** | 主核心，控制端 | Token |
| **node** | 子节点，被控制端 | Key |

### 配置文件

配置文件位于 `config/` 目录：

- `config/auth.json` - 认证配置（AppID、Token、Key）
- `config/nodes.json` - 节点列表

### API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/auth/login` | 登录认证 |
| GET | `/api/node/list` | 节点列表 |
| POST | `/api/node/heartbeat` | 节点心跳 |
| POST | `/api/openclaw/proxy` | 代理接口 |
| GET | `/api/openclaw/status` | 服务状态 |

### 认证示例

```bash
# Token 登录（master）
curl -X POST http://localhost:18790/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"app_id": "master_xxx", "token": "your_token"}'

# Key 登录（node）
curl -X POST http://localhost:18790/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"app_id": "node_xxx", "key": "your_key"}'
```

### 代理接口

```bash
# 获取节点列表
curl -X POST http://localhost:18790/api/openclaw/proxy \
  -H "Content-Type: application/json" \
  -d '{"action": "list_nodes"}'

# 获取单个节点
curl -X POST http://localhost:18790/api/openclaw/proxy \
  -H "Content-Type: application/json" \
  -d '{"action": "get_node", "app_id": "node_xxx"}'

# 分发任务
curl -X POST http://localhost:18790/api/openclaw/proxy \
  -H "Content-Type: application/json" \
  -d '{"action": "dispatch", "app_id": "node_xxx", "message": "hello"}'
```

---

## 🛠️ CLI 命令

| 命令 | 说明 |
|------|------|
| `python3 scripts/cli.py list-nodes` | 列出所有节点 |
| `python3 scripts/cli.py add-node --name X --ip Y` | 添加节点 |
| `python3 scripts/cli.py remove-node --app-id X` | 移除节点 |
| `python3 scripts/cli.py start` | 启动网关 |
| `python3 scripts/cli.py test` | 测试连接 |

---

## 🔧 部署方式

### Python 直接运行

```bash
cd ~/.openclaw/skills/openclaw-connect
pip install aiohttp aiofiles
python3 scripts/cli.py start --port 18790
```

### Docker 部署

```bash
# 构建镜像
docker build -t openclaw-connect .

# 运行容器
docker run -d -p 18790:18790 openclaw-connect
```

### systemd 服务

```bash
# 复制服务文件
sudo cp openclaw-connect.service /etc/systemd/system/

# 启动服务
sudo systemctl enable openclaw-connect
sudo systemctl start openclaw-connect
```

详细部署说明见 [DEPLOY.md](./DEPLOY.md)

---

## 📁 项目结构

```
openclaw-connect/
├── SKILL.md              # 本文件
├── DEPLOY.md             # 部署指南
├── start.sh              # 快速启动脚本
├── config/
│   ├── auth.json          # 认证配置
│   └── nodes.json         # 节点配置
└── scripts/
    ├── connect.py         # 主连接器
    ├── cli.py             # CLI 工具
    ├── auth/
    │   └── auth.py        # 认证系统
    ├── gateway/
    │   └── gateway.py     # REST 网关
    ├── router.py          # 任务路由
    ├── http_client.py     # HTTP 客户端
    └── registry.py        # 节点注册
```

---

## 🔐 安全说明

1. **Token** - 长期凭证，用于 master 身份验证
2. **Key** - 短期凭证（默认7天），用于 node 身份验证
3. 定期更换 Key 可以提高安全性
4. 不要把 Token/Key 分享给不信任的人

---

## 📞 支持

- 查看状态：`python3 scripts/cli.py list-nodes`
- 测试服务：`curl http://localhost:18790/health`
- 查看日志：运行 `python3 scripts/cli.py start` 查看输出