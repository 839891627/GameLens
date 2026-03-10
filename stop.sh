#!/bin/bash
# 帧探·GameLens - 停止服务脚本

echo "================================"
echo "🛑 停止 GameLens 服务"
echo "================================"
echo ""

# 停止后端服务（端口 8080）
BACKEND_PID=$(lsof -ti :8080 2>/dev/null)
if [ -n "$BACKEND_PID" ]; then
    echo "停止后端服务（PID: $BACKEND_PID）..."
    kill -9 $BACKEND_PID
    echo "✓ 后端服务已停止"
else
    echo "⚠️  后端服务未运行"
fi

# 停止前端服务（端口 8000）
FRONTEND_PID=$(lsof -ti :8000 2>/dev/null)
if [ -n "$FRONTEND_PID" ]; then
    echo "停止前端服务（PID: $FRONTEND_PID）..."
    kill -9 $FRONTEND_PID
    echo "✓ 前端服务已停止"
else
    echo "⚠️  前端服务未运行"
fi

echo ""
echo "================================"
echo "✓ 所有服务已停止"
echo "================================"
