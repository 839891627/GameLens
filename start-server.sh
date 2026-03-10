#!/bin/bash
# 帧探·GameLens - 启动服务器脚本

echo "========================================"
echo "帧探·GameLens - 服务器启动"
echo "========================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    echo "请先安装 Python 3.7+"
    exit 1
fi

echo "✓ Python 版本: $(python3 --version)"
echo ""

# 安装依赖
echo "正在安装依赖..."
pip3 install -r server/requirements.txt -q
echo "✓ 依赖安装完成"
echo ""

# 启动服务器
echo "========================================"
echo "服务已启动！"
echo "========================================"
echo ""
echo "访问地址:"
echo "  📱 主页:       http://localhost:5000"
echo "  ⚙️  管理后台:  http://localhost:5000/admin.html"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "========================================"
echo ""

cd "$(dirname "$0")"
python3 server/server.py
