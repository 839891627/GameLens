#!/bin/bash
# 帧探·GameLens - 统一启动脚本（前后端）

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Python 检测（支持环境变量覆盖）
PYTHON_CMD="${PYTHON_CMD:-}"
if [ -z "$PYTHON_CMD" ]; then
    # 自动检测：优先使用 python3.12，然后是 python3，最后是 python
    if command -v python3.12 &> /dev/null; then
        PYTHON_CMD="python3.12"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}错误: 未找到 Python 解释器${NC}"
        echo "请设置环境变量 PYTHON_CMD，例如: PYTHON_CMD=/usr/local/bin/python3.12 ./start.sh"
        exit 1
    fi
fi

# 检查端口占用
check_port() {
    local port=$1
    local service_name=$2

    PID=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$PID" ]; then
        echo -e "${YELLOW}⚠️  端口 $port 已被占用 (PID: $PID)${NC}"
        echo -e "  服务: $service_name"
        read -p "  是否释放端口并继续？(y/n): " choice
        if [ "$choice" = "y" ]; then
            kill -9 $PID 2>/dev/null
            sleep 1
            echo -e "${GREEN}✓ 端口 $port 已释放${NC}"
        else
            return 1
        fi
    fi
    return 0
}

echo "================================"
echo "🎮 帧探·GameLens"
echo "================================"
echo ""
echo "启动方式:"
echo "  1) 前后端一起启动"
echo "  2) 仅启动后端"
echo "  3) 仅启动前端"
echo "  4) 停止所有服务"
echo ""
read -p "请选择 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "检查端口占用..."

        # 检查并释放端口
        check_port 8080 "后端 API" || exit 1
        check_port 8000 "前端服务" || exit 1

        echo ""
        echo "启动后端..."
        cd backend && $PYTHON_CMD -m gamelens &
        BACKEND_PID=$!

        sleep 2

        echo ""
        echo "启动前端..."
        cd frontend && $PYTHON_CMD -m http.server 8000 --directory public &
        FRONTEND_PID=$!

        echo ""
        echo -e "${GREEN}✓ 前后端已启动${NC}"
        echo "  - 前端: http://localhost:8000"
        echo "  - 后端: http://localhost:8080/api"
        echo ""
        echo "按 Ctrl+C 停止所有服务"

        # 等待两个进程
        wait $BACKEND_PID $FRONTEND_PID
        ;;
    2)
        echo ""
        echo "检查端口占用..."
        check_port 8080 "后端 API" || exit 1

        echo ""
        echo "启动后端..."
        cd backend
        $PYTHON_CMD -m gamelens
        ;;
    3)
        echo ""
        echo "检查端口占用..."
        check_port 8000 "前端服务" || exit 1

        echo ""
        echo "启动前端..."
        cd frontend
        $PYTHON_CMD -m http.server 8000 --directory public
        ;;
    4)
        echo ""
        echo "停止所有服务..."

        BACKEND_PID=$(lsof -ti :8080 2>/dev/null)
        FRONTEND_PID=$(lsof -ti :8000 2>/dev/null)

        if [ -n "$BACKEND_PID" ]; then
            echo "停止后端服务..."
            kill -9 $BACKEND_PID
            echo "✓ 后端已停止"
        fi

        if [ -n "$FRONTEND_PID" ]; then
            echo "停止前端服务..."
            kill -9 $FRONTEND_PID
            echo "✓ 前端已停止"
        fi

        if [ -z "$BACKEND_PID" ] && [ -z "$FRONTEND_PID" ]; then
            echo "⚠️  没有运行中的服务"
        fi
        ;;
    *)
        echo -e "${RED}无效选择${NC}"
        exit 1
        ;;
esac
