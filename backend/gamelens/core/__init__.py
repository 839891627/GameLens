#!/usr/bin/env python3.12
"""
帧探·GameLens - 核心模块

包含数据库和向量存储等核心功能。
"""

from gamelens.core.database import (
    get_db,
    init_db,
    get_video_by_bvid,
    get_videos_with_frame_count,
    get_total_videos_count,
    get_total_frames_count,
    get_stats,
    db_exists,
)

from gamelens.core.vector_store import (
    VectorStore,
    load_or_create_store,
    index_exists,
)

__all__ = [
    # Database
    'get_db',
    'init_db',
    'get_video_by_bvid',
    'get_videos_with_frame_count',
    'get_total_videos_count',
    'get_total_frames_count',
    'get_stats',
    'db_exists',
    # Vector Store
    'VectorStore',
    'load_or_create_store',
    'index_exists',
]
