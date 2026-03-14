#!/bin/bash
# OpenClaw Connect 快速启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 默认端口
PORT=18790
DAEMON=0

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  -p, --port <端口>  指定端口 (默认: 18790)"
            echo "  -d, --daemon       后台运行"
            echo "  -h, --help         显示帮助"
            exit 0
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -d|--daemon)
            DAEMON=1
            shift
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# 检查依赖
echo "检查依赖..."
if ! python3 -c "import aiohttp" 2>/dev/null; then
    echo "安装依赖..."
    pip install aiohttp aiofiles -q
fi

# 启动
echo "启动 OpenClaw Connect on port $PORT..."

if [ "$DAEMON" = "1" ]; then
    nohup python3 scripts/cli.py start --port $PORT > /tmp/openclaw-connect.log 2>&1 &
    echo "✓ 已后台启动 (PID: $!)"
    echo "日志: /tmp/openclaw-connect.log"
else
    python3 scripts/cli.py start --port $PORT
fi