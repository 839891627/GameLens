"""
帧探·GameLens - 手游攻略智能匹配工具

基于图像相似度的手游攻略智能匹配工具，使用 FAISS + SQLite 架构。
"""

__version__ = "2.0.0"
__author__ = "GameLens Team"
__description__ = "基于图像相似度的手游攻略智能匹配工具"

# 导出核心功能
from gamelens.core import (
    # Database
    get_db,
    init_db,
    get_video_by_bvid,
    get_videos_with_frame_count,
    get_total_videos_count,
    get_total_frames_count,
    get_stats,
    db_exists,
    # Vector Store
    VectorStore,
    load_or_create_store,
    index_exists,
)

__all__ = [
    'get_db',
    'init_db',
    'get_video_by_bvid',
    'get_videos_with_frame_count',
    'get_total_videos_count',
    'get_total_frames_count',
    'get_stats',
    'db_exists',
    'VectorStore',
    'load_or_create_store',
    'index_exists',
]
