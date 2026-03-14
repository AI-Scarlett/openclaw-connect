# OpenClaw Connect - 部署指南

## 快速开始

### 1. 安装依赖

```bash
cd ~/.openclaw/skills/openclaw-connect
pip install aiohttp aiofiles
```

### 2. 初始化主核心

```bash
python3 scripts/cli.py list-nodes
```

### 3. 启动网关

```bash
# 前台运行
python3 scripts/cli.py start

# 或后台运行
python3 scripts/cli.py start --port 18790 &
```

## Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app
RUN pip install aiohttp aiofiles

EXPOSE 18790
CMD ["python3", "scripts/cli.py", "start", "--port", "18790"]
```

## systemd 服务（可选）

创建 `/etc/systemd/system/openclaw-connect.service`:

```ini
[Unit]
Description=OpenClaw Connect
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/.openclaw/skills/openclaw-connect
ExecStart=/usr/bin/python3 scripts/cli.py start --port 18790
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
systemctl enable openclaw-connect
systemctl start openclaw-connect
```

## API 文档

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| POST | /api/auth/login | 登录认证 |
| GET | /api/node/list | 节点列表 |
| POST | /api/node/heartbeat | 节点心跳 |
| POST | /api/openclaw/proxy | 代理接口 |
| GET | /api/openclaw/status | 服务状态 |

## 与 OpenClaw Gateway 集成

OpenClaw Gateway 可以通过代理 API 调用 Connect：

```bash
# 获取 Connect 状态
curl http://localhost:18790/api/openclaw/status

# 获取节点列表
curl -X POST http://localhost:18790/api/openclaw/proxy \
  -H "Content-Type: application/json" \
  -d '{"action": "list_nodes"}'
```

## 故障排除

### 端口被占用

```bash
# 查找占用进程
lsof -i :18790

# 杀掉进程
kill -9 <PID>
```

### 查看日志

```bash
# 直接运行查看输出
python3 scripts/cli.py start
```