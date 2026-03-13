#!/usr/bin/env python3.12
"""
帧探·GameLens - 数据库管理模块

提供 SQLite 数据库连接和操作函数:
- videos: 视频元数据表
- frames: 帧信息表
- config: 系统配置表
"""

import sqlite3
import contextlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# ==================== 配置 ====================
# 从 core/ 目录向上三级到 backend 目录
DB_PATH = Path(__file__).parent.parent.parent / "data" / "video_frames.db"


# ==================== 上下文管理器 ====================
@contextlib.contextmanager
def get_db():
    """获取数据库连接上下文管理器

    Usage:
        with get_db() as conn:
            conn.execute("SELECT * FROM videos")
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 返回字典格式
    try:
        yield conn
    finally:
        conn.close()


@contextlib.contextmanager
def get_db_transaction():
    """获取事务性数据库连接（自动提交或回滚）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ==================== 数据库初始化 ====================
def init_db():
    """初始化数据库表结构"""
    with get_db() as conn:
        # 创建 videos 表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bvid TEXT UNIQUE NOT NULL,
                title TEXT,
                author TEXT,
                duration INTEGER,
                url TEXT,
                thumbnail_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建 frames 表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER NOT NULL,
                bvid TEXT NOT NULL,
                frame_index INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                seconds INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
            )
        """)

        # 创建 config 表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_frames_video_id ON frames(video_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_frames_bvid ON frames(bvid)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_frames_seconds ON frames(seconds)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_videos_bvid ON videos(bvid)")

        # 插入默认配置
        conn.execute("""
            INSERT OR IGNORE INTO config (key, value) VALUES
                ('frame_interval', '5'),
                ('top_k_results', '5'),
                ('min_similarity', '0.5'),
                ('feature_dimension', '1280'),
                ('faiss_index_type', 'IndexFlatL2'),
                ('db_version', '1.0')
        """)

        conn.commit()

    logger.info(f"数据库初始化完成: {DB_PATH}")


def drop_tables():
    """删除所有表（用于重建）"""
    with get_db() as conn:
        conn.execute("DROP TABLE IF EXISTS frames")
        conn.execute("DROP TABLE IF EXISTS videos")
        conn.execute("DROP TABLE IF EXISTS config")
        conn.commit()
    logger.info("数据库表已删除")


# ==================== 视频操作 ====================
def insert_video(video: Dict[str, Any]) -> int:
    """插入视频记录

    Args:
        video: 视频信息字典，包含 bvid, title, author, duration, url

    Returns:
        新插入视频的 ID
    """
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO videos (bvid, title, author, duration, url, thumbnail_url)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(bvid) DO UPDATE SET
                   title=excluded.title,
                   author=excluded.author,
                   duration=excluded.duration,
                   url=excluded.url,
                   updated_at=CURRENT_TIMESTAMP
               RETURNING id""",
            (video['bvid'], video.get('title', ''), video.get('author', ''),
             video.get('duration', 0), video.get('url', ''), video.get('thumbnail_url', ''))
        )
        result = cursor.fetchone()
        conn.commit()
        return result[0] if result else 0


def get_video_by_bvid(bvid: str) -> Optional[Dict[str, Any]]:
    """根据 BV 号获取视频信息"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM videos WHERE bvid = ?",
            (bvid,)
        ).fetchone()
        return dict(row) if row else None


def get_video_by_id(video_id: int) -> Optional[Dict[str, Any]]:
    """根据 ID 获取视频信息"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM videos WHERE id = ?",
            (video_id,)
        ).fetchone()
        return dict(row) if row else None


def get_all_videos() -> List[Dict[str, Any]]:
    """获取所有视频列表"""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]


def get_videos_with_frame_count() -> List[Dict[str, Any]]:
    """获取视频列表及其帧数统计"""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT v.*,
                   (SELECT COUNT(*) FROM frames WHERE video_id = v.id) as frame_count
            FROM videos v
            ORDER BY v.created_at DESC
        """).fetchall()
        return [dict(row) for row in rows]


def delete_video(bvid: str) -> bool:
    """删除视频（级联删除相关帧）"""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM videos WHERE bvid = ?", (bvid,))
        conn.commit()
        return cursor.rowcount > 0


def video_exists(bvid: str) -> bool:
    """检查视频是否存在"""
    with get_db() as conn:
        row = conn.execute("SELECT 1 FROM videos WHERE bvid = ?", (bvid,)).fetchone()
        return row is not None


def get_total_videos_count() -> int:
    """获取视频总数"""
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as count FROM videos").fetchone()
        return row[0] if row else 0


# ==================== 帧操作 ====================
def insert_frame(frame: Dict[str, Any]) -> int:
    """插入单帧记录

    Args:
        frame: 帧信息字典，包含 video_id, bvid, frame_index, timestamp, seconds, image_path

    Returns:
        新插入帧的 ID
    """
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO frames (video_id, bvid, frame_index, timestamp, seconds, image_path)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (frame['video_id'], frame['bvid'], frame['frame_index'],
             frame['timestamp'], frame['seconds'], frame['image_path'])
        )
        conn.commit()
        return cursor.lastrowid


def get_next_frame_id() -> int:
    """获取下一个可用的 frame_id

    Returns:
        下一个 frame_id
    """
    with get_db() as conn:
        result = conn.execute("SELECT MAX(id) FROM frames").fetchone()
        max_id = result[0] if result and result[0] else 0
        return max_id + 1


def insert_frames_batch(frames: List[Dict[str, Any]]) -> int:
    """批量插入帧记录

    Args:
        frames: 帧信息列表

    Returns:
        插入的帧数量
    """
    if not frames:
        return 0

    with get_db() as conn:
        conn.executemany(
            """INSERT INTO frames (video_id, bvid, frame_index, timestamp, seconds, image_path)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [(f['video_id'], f['bvid'], f['frame_index'],
              f['timestamp'], f['seconds'], f['image_path']) for f in frames]
        )
        conn.commit()
        return len(frames)


def get_frame_by_id(frame_id: int) -> Optional[Dict[str, Any]]:
    """根据 ID 获取帧信息"""
    with get_db() as conn:
        row = conn.execute(
            """SELECT f.*, v.title, v.author, v.url, v.bvid as video_bvid
               FROM frames f
               JOIN videos v ON f.video_id = v.id
               WHERE f.id = ?""",
            (frame_id,)
        ).fetchone()
        return dict(row) if row else None


def get_frames_by_video_id(video_id: int) -> List[Dict[str, Any]]:
    """获取指定视频的所有帧"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM frames WHERE video_id = ? ORDER BY seconds ASC",
            (video_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_frames_by_bvid(bvid: str) -> List[Dict[str, Any]]:
    """获取指定 BV 号的所有帧"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM frames WHERE bvid = ? ORDER BY seconds ASC",
            (bvid,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_frames_by_ids(frame_ids: List[int]) -> List[Dict[str, Any]]:
    """根据 ID 列表批量获取帧信息

    Args:
        frame_ids: 帧 ID 列表

    Returns:
        帧信息字典列表（按输入顺序返回）
    """
    if not frame_ids:
        return []

    with get_db() as conn:
        placeholders = ','.join('?' * len(frame_ids))
        rows = conn.execute(
            f"""SELECT f.*, v.title, v.author, v.url, v.bvid as video_bvid
               FROM frames f
               JOIN videos v ON f.video_id = v.id
               WHERE f.id IN ({placeholders})""",
            frame_ids
        ).fetchall()

        # 创建 ID 到行索引的映射
        row_map = {dict(row)['id']: dict(row) for row in rows}

        # 按输入顺序返回
        return [row_map.get(fid) for fid in frame_ids if fid in row_map]


def get_total_frames_count() -> int:
    """获取总帧数"""
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as count FROM frames").fetchone()
        return row[0] if row else 0


def delete_frames_by_video_id(video_id: int) -> int:
    """删除指定视频的所有帧"""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM frames WHERE video_id = ?", (video_id,))
        conn.commit()
        return cursor.rowcount


# ==================== 配置操作 ====================
def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """获取配置值"""
    with get_db() as conn:
        row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default


def set_config(key: str, value: str):
    """设置配置值"""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO config (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP""",
            (key, value)
        )
        conn.commit()


def get_all_config() -> Dict[str, str]:
    """获取所有配置"""
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM config").fetchall()
        return {row['key']: row['value'] for row in rows}


# ==================== 统计操作 ====================
def get_stats() -> Dict[str, Any]:
    """获取数据库统计信息"""
    with get_db() as conn:
        total_videos = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        total_frames = conn.execute("SELECT COUNT(*) FROM frames").fetchone()[0]

        # 获取最近处理的视频
        latest_video = conn.execute(
            "SELECT bvid, title FROM videos ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()

        return {
            'total_videos': total_videos,
            'total_frames': total_frames,
            'latest_video': dict(latest_video) if latest_video else None
        }


def db_exists() -> bool:
    """检查数据库文件是否存在"""
    return DB_PATH.exists()


def get_db_size() -> int:
    """获取数据库文件大小（字节）"""
    if db_exists():
        return DB_PATH.stat().st_size
    return 0


# ==================== 主函数 ====================
def main():
    """测试数据库功能"""
    print("=" * 60)
    print("数据库模块测试")
    print("=" * 60)
    print(f"数据库路径: {DB_PATH}")
    print()

    # 初始化数据库
    print("1. 初始化数据库...")
    init_db()

    # 统计信息
    print("\n2. 统计信息:")
    stats = get_stats()
    print(f"   视频数: {stats['total_videos']}")
    print(f"   帧数: {stats['total_frames']}")
    print(f"   数据库大小: {get_db_size() / 1024:.2f} KB")

    # 配置
    print("\n3. 系统配置:")
    config = get_all_config()
    for key, value in config.items():
        print(f"   {key}: {value}")

    print("\n✓ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
