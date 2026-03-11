#!/bin/bash
# 帧探·GameLens - 统一启动脚本（前后端）

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

# 启动前端
start_frontend() {
    kill_port 8000 "前端服务"
    echo "启动前端..."
    cd frontend && $PYTHON_CMD -m http.server 8000 --directory public > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$LOG_DIR/frontend.pid"
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

    # 再检查一遍端口
    BACKEND_PID=$(lsof -ti :8080 2>/dev/null)
    FRONTEND_PID=$(lsof -ti :8000 2>/dev/null)

    if [ -n "$BACKEND_PID" ]; then
        kill -9 $BACKEND_PID
        echo -e "${GREEN}✓ 后端端口已释放${NC}"
    fi

    if [ -n "$FRONTEND_PID" ]; then
        kill -9 $FRONTEND_PID
        echo -e "${GREEN}✓ 前端端口已释放${NC}"
    fi
}

# 显示状态
show_status() {
    echo "服务状态:"
    echo ""

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

    # 前端
    if [ -f "$LOG_DIR/frontend.pid" ]; then
        PID=$(cat "$LOG_DIR/frontend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "  前端: ${GREEN}运行中 (PID: $PID)${NC}"
        else
            echo -e "  前端: ${RED}已停止${NC}"
        fi
    else
        PID=$(lsof -ti :8000 2>/dev/null)
        if [ -n "$PID" ]; then
            echo -e "  前端: ${YELLOW}运行中 (PID: $PID, 未记录)${NC}"
        else
            echo -e "  前端: ${RED}未运行${NC}"
        fi
    fi
}

# 显示帮助
show_help() {
    echo "帧探·GameLens - 启动脚本"
    echo ""
    echo "用法: ./start.sh [命令]"
    echo ""
    echo "命令:"
    echo "  start, (无参数)  - 启动前后端（默认）"
    echo "  backend          - 仅启动后端"
    echo "  frontend         - 仅启动前端"
    echo "  stop             - 停止所有服务"
    echo "  status           - 显示服务状态"
    echo "  logs             - 查看日志（后台模式）"
    echo ""
    echo "环境变量:"
    echo "  PYTHON_CMD        - 指定 Python 解释器路径"
    echo "  LOG_DIR           - 日志目录（默认: logs）"
    echo ""
    echo "示例:"
    echo "  ./start.sh                    # 启动前后端"
    echo "  nohup ./start.sh &            # 后台启动"
    echo "  ./start.sh backend            # 仅启动后端"
    echo "  ./start.sh stop               # 停止服务"
    echo "  tail -f logs/backend.log      # 查看后端日志"
}

# 主逻辑
case "${1:-start}" in
    start|"")
        echo "================================"
        echo "🎮 帧探·GameLens"
        echo "================================"
        echo ""
        start_backend
        echo ""
        start_frontend
        echo ""
        echo -e "${GREEN}✓ 启动完成${NC}"
        echo "  - 前端: http://localhost:8000"
        echo "  - 后端: http://localhost:8080/api"
        echo ""
        echo "使用 ./start.sh status 查看状态"
        echo "使用 ./start.sh logs 查看日志"
        ;;
    backend)
        echo "================================"
        echo "🎮 帧探·GameLens - 后端"
        echo "================================"
        echo ""
        start_backend
        ;;
    frontend)
        echo "================================"
        echo "🎮 帧探·GameLens - 前端"
        echo "================================"
        echo ""
        start_frontend
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