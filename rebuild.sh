#!/bin/bash
# 帧探·GameLens - 完全重新索引脚本

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 进入 backend 目录
cd backend

echo "================================"
echo "🔄 完全重新索引"
echo "================================"
echo ""

# 1. 停止服务
echo -e "${YELLOW}[1/3] 停止服务...${NC}"
MOBILENET_PID=$(lsof -ti :9998 2>/dev/null)
BACKEND_PID=$(lsof -ti :8080 2>/dev/null)

if [ -n "$MOBILENET_PID" ]; then
    kill -9 $MOBILENET_PID 2>/dev/null
    echo -e "${GREEN}✓ 已停止 MobileNet 服务${NC}"
fi

if [ -n "$BACKEND_PID" ]; then
    kill -9 $BACKEND_PID 2>/dev/null
    echo -e "${GREEN}✓ 已停止后端服务${NC}"
fi
echo ""

# 2. 删除旧索引和数据库
echo -e "${YELLOW}[2/3] 删除旧索引和数据库...${NC}"

deleted_files=()

if [ -f "data/faiss_index.index" ]; then
    rm -f data/faiss_index.index
    deleted_files+=("faiss_index.index")
fi

if [ -f "data/frame_ids.npy" ]; then
    rm -f data/frame_ids.npy
    deleted_files+=("frame_ids.npy")
fi

if [ -f "data/video_frames.db" ]; then
    rm -f data/video_frames.db
    deleted_files+=("video_frames.db")
fi

# 可选：删除所有视频帧（取消注释以启用）
# if [ -d "data/video_frames" ]; then
#     rm -rf data/video_frames
#     deleted_files+=("video_frames/")
# fi

if [ ${#deleted_files[@]} -eq 0 ]; then
    echo -e "${YELLOW}⚠️  没有找到需要删除的文件${NC}"
else
    for file in "${deleted_files[@]}"; do
        echo -e "${GREEN}✓ 已删除: $file${NC}"
    done
fi
echo ""

# 3. 重新构建索引
echo -e "${YELLOW}[3/3] 重新构建索引...${NC}"
echo ""
python3 scripts/build_index.py
BUILD_RESULT=$?

echo ""
if [ $BUILD_RESULT -eq 0 ]; then
    echo "================================"
    echo -e "${GREEN}✓ 重新索引完成！${NC}"
    echo "================================"
    echo ""
    echo "接下来可以启动服务："
    echo "  ./start.sh"
else
    echo "================================"
    echo -e "${RED}✗ 重新索引失败${NC}"
    echo "================================"
    exit 1
fi