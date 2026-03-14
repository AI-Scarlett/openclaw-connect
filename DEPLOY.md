# OpenClaw Connect - 部署指南

## 目录

- [快速开始](#快速开始)
- [Docker 部署](#docker-部署)
- [systemd 服务](#systemd-服务)
- [故障排除](#故障排除)

---

## 快速开始

### 1. 安装依赖

```bash
cd ~/.openclaw/skills/openclaw-connect
pip install aiohttp aiofiles
```

### 2. 启动网关

```bash
# 前台运行
python3 scripts/cli.py start

# 后台运行
./start.sh -d

# 指定端口
./start.sh -p 18790 -d
```

### 3. 验证

```bash
# 健康检查
curl http://localhost:18790/health

# 状态检查
curl http://localhost:18790/api/openclaw/status
```

---

## Docker 部署

### 构建镜像

```bash
cd ~/.openclaw/skills/openclaw-connect
docker build -t openclaw-connect .
```

### 运行容器

```bash
docker run -d -p 18790:18790 openclaw-connect
```

### Docker Compose（可选）

创建 `docker-compose.yml`:

```yaml
version: '3'
services:
  openclaw-connect:
    build: .
    ports:
      - "18790:18790"
    volumes:
      - ./config:/app/config
    restart: unless-stopped
```

启动：
```bash
docker-compose up -d
```

---

## systemd 服务

### 1. 创建服务文件

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
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. 启动服务

```bash
systemctl daemon-reload
systemctl enable openclaw-connect
systemctl start openclaw-connect
```

### 3. 查看状态

```bash
systemctl status openclaw-connect
journalctl -u openclaw-connect -f
```

---

## 故障排除

### 端口被占用

```bash
# 查找占用进程
lsof -i :18790

# 杀掉进程
kill -9 <PID>
```

### 依赖未安装

```bash
pip install aiohttp aiofiles
```

### 查看日志

```bash
# 前台运行时查看输出
python3 scripts/cli.py start

# systemd 服务日志
journalctl -u openclaw-connect -n 50
```

### 测试 API

```bash
# 健康检查
curl http://localhost:18790/health

# 节点列表（需要 Bearer Token）
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:18790/api/node/list
```

---

## 常见问题

**Q: 如何添加新节点？**

```bash
python3 scripts/cli.py add-node \
  --name "新节点" \
  --ip "192.168.1.50" \
  --capabilities code search
```

**Q: 如何查看当前节点？**

```bash
python3 scripts/cli.py list-nodes
```

**Q: 如何停止服务？**

```bash
# 如果是前台运行，按 Ctrl+C

# 如果是后台运行
pkill -f "python3 scripts/cli.py start"
```

---

## 配置说明

### config/auth.json

```json
{
  "config": {
    "role": "master",
    "app_id": "master_xxx",
    "token": "your_token_here",
    "key_valid_days": 7
  },
  "nodes": []
}
```

### config/nodes.json

```json
{
  "nodes": [
    {
      "app_id": "node_xxx",
      "name": "节点名称",
      "role": "node",
      "ip": "192.168.1.100",
      "port": 18789,
      "capabilities": ["code", "search"]
    }
  ]
}
```

---

## 下一步

- 配置更多节点
- 与 OpenClaw Gateway 集成
- 启用 HTTPS（可选）