#!/bin/bash
# 帧探·GameLens - 后端启动脚本

echo "================================"
echo "🎮 GameLens - 后端 API 服务器"
echo "================================"
echo ""
echo "API 地址: http://localhost:8080/api"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "================================"
echo ""

cd backend || exit 1
python -m gamelens "$@"
