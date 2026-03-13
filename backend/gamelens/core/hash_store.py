#!/usr/bin/env python3
"""
帧探·GameLens - 轻量级向量存储（基于感知哈希）

使用哈希匹配替代 FAISS，适合低内存环境：
- 不需要 FAISS 库
- 内存占用极小
- 匹配速度快
- 适合精确截图识别
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# ==================== 配置 ====================
HASH_DB_PATH = Path(__file__).parent.parent.parent / "data" / "hash_frames.db"

# ==================== 初始化 ====================
def init_hash_db():
    """初始化哈希数据库"""
    conn = sqlite3.connect(HASH_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hash_frames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            frame_id INTEGER NOT NULL UNIQUE,
            bvid TEXT NOT NULL,
            phash INTEGER NOT NULL,
            dhash INTEGER NOT NULL,
            histogram TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建索引
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hash_frames_bvid ON hash_frames(bvid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hash_frames_frame_id ON hash_frames(frame_id)")

    conn.commit()
    conn.close()

    logger.info(f"哈希数据库初始化完成: {HASH_DB_PATH}")


def add_hash_record(
    frame_id: int,
    bvid: str,
    phash: int,
    dhash: int,
    histogram: list
) -> bool:
    """添加哈希记录

    Args:
        frame_id: 帧ID
        bvid: 视频BV号
        phash: 感知哈希
        dhash: 差值哈希
        histogram: 颜色直方图

    Returns:
        是否成功
    """
    import json

    try:
        conn = sqlite3.connect(HASH_DB_PATH)
        conn.execute(
            """INSERT OR REPLACE INTO hash_frames (frame_id, bvid, phash, dhash, histogram)
               VALUES (?, ?, ?, ?, ?)""",
            (frame_id, bvid, phash, dhash, json.dumps(histogram))
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"添加哈希记录失败: {e}")
        return False


def get_hash_record(frame_id: int) -> Optional[Dict[str, Any]]:
    """获取哈希记录

    Args:
        frame_id: 帧ID

    Returns:
        哈希记录字典
    """
    import json

    try:
        conn = sqlite3.connect(HASH_DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM hash_frames WHERE frame_id = ?",
            (frame_id,)
        ).fetchone()
        conn.close()

        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"获取哈希记录失败: {e}")
        return None


def match_by_hash(
    query_phash: int,
    query_dhash: int,
    max_distance: int = 5,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """基于哈希匹配

    Args:
        query_phash: 查询的 pHash
        query_dhash: 查询的 dHash
        max_distance: 最大汉明距离
        limit: 返回结果数量

    Returns:
        匹配结果列表
    """
    import json

    try:
        conn = sqlite3.connect(HASH_DB_PATH)
        conn.row_factory = sqlite3.Row

        # 获取所有记录
        rows = conn.execute("SELECT * FROM hash_frames").fetchall()
        conn.close()

        results = []

        for row in rows:
            record = dict(row)

            # 计算汉明距离
            phash_distance = bin(record['phash'] ^ query_phash).count('1')
            dhash_distance = bin(record['dhash'] ^ query_dhash).count('1')

            # 综合距离（加权平均）
            avg_distance = (phash_distance + dhash_distance) / 2

            if avg_distance <= max_distance:
                # 转换为相似度
                similarity = 1 - (avg_distance / 64)  # 64位哈希

                results.append({
                    'frame_id': record['frame_id'],
                    'bvid': record['bvid'],
                    'phash_distance': phash_distance,
                    'dhash_distance': dhash_distance,
                    'avg_distance': avg_distance,
                    'similarity': similarity
                })

        # 按相似度排序
        results.sort(key=lambda x: x['similarity'], reverse=True)

        return results[:limit]

    except Exception as e:
        logger.error(f"哈希匹配失败: {e}")
        return []


def get_hash_db_stats() -> Dict[str, Any]:
    """获取哈希数据库统计信息"""
    try:
        conn = sqlite3.connect(HASH_DB_PATH)
        total = conn.execute("SELECT COUNT(*) FROM hash_frames").fetchone()[0]
        conn.close()

        return {
            'total_frames': total,
            'db_path': str(HASH_DB_PATH),
            'db_exists': HASH_DB_PATH.exists(),
            'db_size_mb': HASH_DB_PATH.stat().st_size / (1024 * 1024) if HASH_DB_PATH.exists() else 0
        }
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return {}


# ==================== 主函数 ====================
def main():
    print("=" * 60)
    print("轻量级向量存储模块测试")
    print("=" * 60)
    print()

    # 初始化数据库
    init_hash_db()

    # 统计信息
    stats = get_hash_db_stats()
    print("数据库统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print()
    print("✓ 测试完成")


if __name__ == "__main__":
    main()