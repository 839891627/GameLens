#!/bin/bash
# 帧探·GameLens - 前端启动脚本

echo "================================"
echo "🎮 GameLens - 前端服务器"
echo "================================"
echo ""

# 检查 dist 目录是否存在
if [ ! -d "dist" ]; then
    echo "前端未构建，开始构建..."
    npm install --silent
    npm run build
fi

echo "前端地址: http://localhost:8000"
echo "后端 API: http://localhost:8080/api"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "================================"
echo ""

python -m http.server 8000 --directory dist