# OpenClaw Connect

多实例 OpenClaw 安全协作系统

[📖 使用手册](./SKILL.md) | [🚀 部署指南](./DEPLOY.md)

## 简介

OpenClaw Connect 是用于多 OpenClaw 实例安全协作的系统，通过 REST API 实现节点发现、任务分发和状态同步。

## 特性

- 三层认证（AppID + Token + Key）
- REST API 网关
- 节点管理
- 任务分发

## 快速开始

```bash
# 启动服务
cd ~/.openclaw/skills/openclaw-connect
pip install aiohttp aiofiles
./start.sh
```

## 文档

- [SKILL.md](./SKILL.md) - 完整使用手册
- [DEPLOY.md](./DEPLOY.md) - 部署指南