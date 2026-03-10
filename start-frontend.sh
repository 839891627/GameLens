#!/bin/bash
# 帧探·GameLens - 前端启动脚本

echo "================================"
echo "🎮 GameLens - 前端服务器"
echo "================================"
echo ""
echo "前端地址: http://localhost:8000"
echo "后端 API: http://localhost:5000/api"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "================================"
echo ""

cd frontend || exit 1
python -m http.server 8000 --directory public
