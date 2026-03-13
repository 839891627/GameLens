#!/bin/bash
# 帧探·GameLens - 统一启动脚本（适配优化后的前端）

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

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

# Node.js 检测
NODE_CMD="${NODE_CMD:-}"
if [ -z "$NODE_CMD" ]; then
    if command -v node &> /dev/null; then
        NODE_CMD="node"
    elif command -v nodejs &> /dev/null; then
        NODE_CMD="nodejs"
    else
        echo -e "${YELLOW}警告: 未找到 Node.js，将使用 Python 启动前端${NC}"
        NODE_CMD=""
    fi
fi

# 日志目录（绝对路径）
LOG_DIR="${LOG_DIR:-$SCRIPT_DIR/logs}"
mkdir -p "$LOG_DIR"

# 检查并释放端口（非交互，自动 kill）
kill_port() {
    local port=$1
    local service_name=$2

    PID=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$PID" ]; then
        echo -e "${YELLOW}⚠️  端口 $port 已被占用 (PID: $PID)，正在释放...${NC}"
        kill -9 $PID 2>/dev/null
        sleep 1
        echo -e "${GREEN}✓ 端口 $port 已释放${NC}"
    fi
}

# 启动 MobileNet 服务
start_clip_service() {
    kill_port 9998 "MobileNet 服务"
    echo "启动 MobileNet 特征提取服务..."
    cd backend && $PYTHON_CMD mobilenet_service.py > "$LOG_DIR/clip_service.log" 2>&1 &
    echo $! > "$LOG_DIR/clip_service.pid"
    sleep 3
    if ps -p $(cat "$LOG_DIR/clip_service.pid") > /dev/null; then
        echo -e "${GREEN}✓ MobileNet 服务已启动 (PID: $(cat $LOG_DIR/clip_service.pid))${NC}"
        echo "  日志: $LOG_DIR/clip_service.log"
    else
        echo -e "${RED}✗ MobileNet 服务启动失败，查看日志: tail $LOG_DIR/clip_service.log${NC}"
    fi
}

# 启动后端
start_backend() {
    kill_port 8080 "后端 API"
    echo "启动后端..."
    cd backend && $PYTHON_CMD -m gamelens > "$LOG_DIR/backend.log" 2>&1 &
    echo $! > "$LOG_DIR/backend.pid"
    sleep 2
    if ps -p $(cat "$LOG_DIR/backend.pid") > /dev/null; then
        echo -e "${GREEN}✓ 后端已启动 (PID: $(cat $LOG_DIR/backend.pid))${NC}"
        echo "  日志: $LOG_DIR/backend.log"
    else
        echo -e "${RED}✗ 后端启动失败，查看日志: tail $LOG_DIR/backend.log${NC}"
    fi
}

# 构建前端
build_frontend() {
    echo "检查前端构建状态..."
    if [ ! -d "frontend/dist" ] || [ ! -f "frontend/dist/index.html" ]; then
        echo "前端未构建，开始构建..."
        cd frontend
        if command -v npm &> /dev/null; then
            npm install --silent
            npm run build
            cd ..
            if [ -f "frontend/dist/index.html" ]; then
                echo -e "${GREEN}✓ 前端构建完成${NC}"
            else
                echo -e "${RED}✗ 前端构建失败${NC}"
                return 1
            fi
        else
            echo -e "${RED}错误: 未找到 npm，无法构建前端${NC}"
            return 1
        fi
    else
        echo -e "${GREEN}✓ 前端已构建${NC}"
    fi
}

# 启动前端（生产模式 - 使用构建后的文件）
start_frontend_prod() {
    build_frontend || return 1

    kill_port 8000 "前端服务"
    echo "启动前端（生产模式）..."
    cd frontend && $PYTHON_CMD -m http.server 8000 --directory dist > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$LOG_DIR/frontend.pid"
    sleep 2
    if ps -p $(cat "$LOG_DIR/frontend.pid") > /dev/null; then
        echo -e "${GREEN}✓ 前端已启动 (PID: $(cat $LOG_DIR/frontend.pid))${NC}"
        echo "  日志: $LOG_DIR/frontend.log"
    else
        echo -e "${RED}✗ 前端启动失败，查看日志: tail $LOG_DIR/frontend.log${NC}"
    fi
}

# 启动前端（开发模式 - 需要 Node.js）
start_frontend_dev() {
    if [ -z "$NODE_CMD" ]; then
        echo -e "${RED}错误: 开发模式需要 Node.js${NC}"
        return 1
    fi

    kill_port 3000 "前端开发服务器"
    echo "启动前端（开发模式）..."
    cd frontend

    # 检查 node_modules
    if [ ! -d "node_modules" ]; then
        echo "安装依赖..."
        npm install --silent
    fi

    $NODE_CMD ./node_modules/.bin/vite --host 0.0.0.0 > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$LOG_DIR/frontend.pid"
    cd ..
    sleep 2
    if ps -p $(cat "$LOG_DIR/frontend.pid") > /dev/null; then
        echo -e "${GREEN}✓ 前端已启动 (PID: $(cat $LOG_DIR/frontend.pid))${NC}"
        echo "  日志: $LOG_DIR/frontend.log"
    else
        echo -e "${RED}✗ 前端启动失败，查看日志: tail $LOG_DIR/frontend.log${NC}"
    fi
}

# 停止服务
stop_services() {
    echo "停止所有服务..."

    # 停止 MobileNet 服务
    if [ -f "$LOG_DIR/clip_service.pid" ]; then
        PID=$(cat "$LOG_DIR/clip_service.pid")
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID
            echo -e "${GREEN}✓ MobileNet 服务已停止 (PID: $PID)${NC}"
        fi
        rm -f "$LOG_DIR/clip_service.pid"
    fi

    if [ -f "$LOG_DIR/backend.pid" ]; then
        PID=$(cat "$LOG_DIR/backend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID
            echo -e "${GREEN}✓ 后端已停止 (PID: $PID)${NC}"
        fi
        rm -f "$LOG_DIR/backend.pid"
    fi

    if [ -f "$LOG_DIR/frontend.pid" ]; then
        PID=$(cat "$LOG_DIR/frontend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID
            echo -e "${GREEN}✓ 前端已停止 (PID: $PID)${NC}"
        fi
        rm -f "$LOG_DIR/frontend.pid"
    fi

    # 再检查一遍端口（开发模式前端在 3000 端口）
    MOBILENET_PID=$(lsof -ti :9998 2>/dev/null)
    BACKEND_PID=$(lsof -ti :8080 2>/dev/null)
    FRONTEND_PID=$(lsof -ti :8000 2>/dev/null)
    FRONTEND_DEV_PID=$(lsof -ti :3000 2>/dev/null)

    if [ -n "$MOBILENET_PID" ]; then
        kill -9 $MOBILENET_PID
        echo -e "${GREEN}✓ MobileNet 端口已释放${NC}"
    fi

    if [ -n "$BACKEND_PID" ]; then
        kill -9 $BACKEND_PID
        echo -e "${GREEN}✓ 后端端口已释放${NC}"
    fi

    if [ -n "$FRONTEND_PID" ]; then
        kill -9 $FRONTEND_PID
        echo -e "${GREEN}✓ 前端端口已释放${NC}"
    fi

    if [ -n "$FRONTEND_DEV_PID" ]; then
        kill -9 $FRONTEND_DEV_PID
        echo -e "${GREEN}✓ 前端开发端口已释放${NC}"
    fi
}

# 显示状态
show_status() {
    echo "服务状态:"
    echo ""

    # MobileNet 服务
    if [ -f "$LOG_DIR/clip_service.pid" ]; then
        PID=$(cat "$LOG_DIR/clip_service.pid")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "  MobileNet: ${GREEN}运行中 (PID: $PID)${NC}"
        else
            echo -e "  MobileNet: ${RED}已停止${NC}"
        fi
    else
        PID=$(lsof -ti :9998 2>/dev/null)
        if [ -n "$PID" ]; then
            echo -e "  MobileNet: ${YELLOW}运行中 (PID: $PID, 未记录)${NC}"
        else
            echo -e "  MobileNet: ${RED}未运行${NC}"
        fi
    fi

    # 后端
    if [ -f "$LOG_DIR/backend.pid" ]; then
        PID=$(cat "$LOG_DIR/backend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "  后端: ${GREEN}运行中 (PID: $PID)${NC}"
        else
            echo -e "  后端: ${RED}已停止${NC}"
        fi
    else
        PID=$(lsof -ti :8080 2>/dev/null)
        if [ -n "$PID" ]; then
            echo -e "  后端: ${YELLOW}运行中 (PID: $PID, 未记录)${NC}"
        else
            echo -e "  后端: ${RED}未运行${NC}"
        fi
    fi

    # 前端（检查 8000 和 3000 端口）
    FRONTEND_PID=$(lsof -ti :8000 2>/dev/null)
    FRONTEND_DEV_PID=$(lsof -ti :3000 2>/dev/null)

    if [ -n "$FRONTEND_PID" ]; then
        echo -e "  前端: ${GREEN}运行中 (生产模式, PID: $FRONTEND_PID)${NC}"
    elif [ -n "$FRONTEND_DEV_PID" ]; then
        echo -e "  前端: ${GREEN}运行中 (开发模式, PID: $FRONTEND_DEV_PID)${NC}"
    else
        echo -e "  前端: ${RED}未运行${NC}"
    fi
}

# 显示帮助
show_help() {
    echo "帧探·GameLens - 启动脚本"
    echo ""
    echo "用法: ./start.sh [命令]"
    echo ""
    echo "命令:"
    echo "  start, (无参数)  - 启动所有服务（生产模式，默认）"
    echo "  dev              - 启动所有服务（开发模式，支持热更新）"
    echo "  backend          - 仅启动后端 + CLIP 服务"
    echo "  frontend         - 仅启动前端（生产模式）"
    echo "  stop             - 停止所有服务"
    echo "  status           - 显示服务状态"
    echo "  logs             - 查看后端日志"
    echo "  rebuild          - 重新构建前端"
    echo ""
    echo "服务端口:"
    echo "  - 前端: 8000 (生产) / 3000 (开发)"
    echo "  - 后端: 8080"
    echo "  - MobileNet: 9998"
    echo ""
    echo "环境变量:"
    echo "  PYTHON_CMD        - 指定 Python 解释器路径"
    echo "  NODE_CMD          - 指定 Node.js 路径"
    echo "  LOG_DIR           - 日志目录（默认: logs）"
    echo ""
    echo "示例:"
    echo "  ./start.sh                # 启动生产模式"
    echo "  ./start.sh dev            # 启动开发模式"
    echo "  nohup ./start.sh &        # 后台启动"
    echo "  ./start.sh stop           # 停止服务"
    echo "  tail -f logs/backend.log  # 查看后端日志"
}

# 重新构建前端
rebuild_frontend() {
    echo "重新构建前端..."
    cd frontend
    npm run build
    cd ..
    echo -e "${GREEN}✓ 前端构建完成${NC}"
}

# 主逻辑
case "${1:-start}" in
    start|"")
        echo "================================"
        echo "🎮 帧探·GameLens - 生产模式"
        echo "================================"
        echo ""
        start_clip_service
        echo ""
        start_backend
        echo ""
        start_frontend_prod
        echo ""
        echo -e "${GREEN}✓ 启动完成${NC}"
        echo "  - 前端: http://localhost:8000"
        echo "  - 后端: http://localhost:8080/api"
        echo "  - MobileNet: http://localhost:9998"
        echo ""
        echo "使用 ./start.sh status 查看状态"
        echo "使用 ./start.sh logs 查看日志"
        ;;
    dev)
        echo "================================"
        echo "🎮 帧探·GameLens - 开发模式"
        echo "================================"
        echo ""
        start_clip_service
        echo ""
        start_backend
        echo ""
        start_frontend_dev
        echo ""
        echo -e "${GREEN}✓ 启动完成${NC}"
        echo "  - 前端: http://localhost:3000"
        echo "  - 后端: http://localhost:8080/api"
        echo "  - MobileNet: http://localhost:9998"
        echo ""
        echo "使用 ./start.sh status 查看状态"
        echo "使用 ./start.sh logs 查看日志"
        ;;
    backend)
        echo "================================"
        echo "🎮 帧探·GameLens - 后端 + MobileNet"
        echo "================================"
        echo ""
        start_clip_service
        echo ""
        start_backend
        ;;
    frontend)
        echo "================================"
        echo "🎮 帧探·GameLens - 前端（生产模式）"
        echo "================================"
        echo ""
        start_frontend_prod
        ;;
    stop)
        stop_services
        ;;
    status)
        show_status
        ;;
    logs)
        echo "查看日志 (Ctrl+C 退出):"
        echo ""
        echo "后端日志:"
        tail -f "$LOG_DIR/backend.log" 2>/dev/null || echo "无日志"
        ;;
    rebuild)
        rebuild_frontend
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}未知命令: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac