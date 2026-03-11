#!/usr/bin/env python3
"""
帧探·GameLens - 数据迁移脚本

从 video_index.json 迁移数据到 SQLite + FAISS 架构

功能:
1. 读取现有的 video_index.json
2. 将元数据写入 SQLite
3. 将特征向量写入 FAISS 索引
4. 验证迁移结果

使用方法:
    cd backend
    python scripts/migrate_to_db.py

依赖:
    pip install faiss-cpu numpy
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from tqdm import tqdm

from gamelens.core.database import init_db, insert_video, insert_frames_batch, get_stats
from gamelens.core.vector_store import VectorStore

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 配置 ====================
DATA_DIR = PROJECT_ROOT / "data"
VIDEO_INDEX_FILE = DATA_DIR / "video_index.json"
BACKUP_INDEX_FILE = DATA_DIR / "video_index.json.backup"


# ==================== 迁移类 ====================
class DatabaseMigrator:
    """数据库迁移器"""

    def __init__(self):
        self.vector_store = VectorStore()
        self.vector_store.create_index()

    def validate_json_file(self) -> bool:
        """验证 JSON 文件是否存在且格式正确"""
        if not VIDEO_INDEX_FILE.exists():
            logger.error(f"索引文件不存在: {VIDEO_INDEX_FILE}")
            return False

        try:
            with open(VIDEO_INDEX_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查基本结构
            if 'videos' not in data:
                logger.error("JSON 文件缺少 'videos' 字段")
                return False

            logger.info(f"✓ JSON 文件验证通过: {len(data['videos'])} 个视频")
            return True

        except json.JSONDecodeError as e:
            logger.error(f"JSON 格式错误: {e}")
            return False
        except Exception as e:
            logger.error(f"验证失败: {e}")
            return False

    def backup_json_file(self) -> bool:
        """备份原始 JSON 文件"""
        try:
            if VIDEO_INDEX_FILE.exists():
                import shutil
                shutil.copy2(VIDEO_INDEX_FILE, BACKUP_INDEX_FILE)
                logger.info(f"✓ 备份完成: {BACKUP_INDEX_FILE}")
                return True
        except Exception as e:
            logger.error(f"备份失败: {e}")
            return False

    def load_json_index(self) -> Dict[str, Any]:
        """加载 JSON 索引"""
        logger.info(f"正在加载: {VIDEO_INDEX_FILE}")

        with open(VIDEO_INDEX_FILE, 'r', encoding='utf-8') as f:
            index = json.load(f)

        total_videos = len(index.get('videos', []))
        total_frames = index.get('total_frames', 0)

        logger.info(f"✓ 加载完成: {total_videos} 视频, {total_frames} 帧")
        return index

    def migrate_video(self, video_data: Dict[str, Any]) -> int:
        """迁移单个视频

        Returns:
            该视频的帧数
        """
        bvid = video_data['bvid']

        # 1. 插入视频记录
        video_id = insert_video({
            'bvid': bvid,
            'title': video_data.get('title', ''),
            'author': video_data.get('author', ''),
            'duration': video_data.get('duration', 0),
            'url': video_data.get('url', ''),
            'thumbnail_url': video_data.get('thumbnail_url', '')
        })

        # 2. 准备帧数据和向量
        frames = video_data.get('frames', [])
        if not frames:
            logger.warning(f"  视频 {bvid} 没有帧数据")
            return 0

        frame_records = []
        vectors = []

        for frame in frames:
            frame_records.append({
                'video_id': video_id,
                'bvid': bvid,
                'frame_index': frame.get('frame_index', len(frame_records)),
                'timestamp': frame['timestamp'],
                'seconds': frame['seconds'],
                'image_path': frame['image_path']
            })

            # 提取特征向量
            if 'feature' in frame:
                vectors.append(frame['feature'])

        # 3. 批量插入帧记录
        if frame_records:
            insert_frames_batch(frame_records)

        # 4. 添加向量到 FAISS
        if vectors:
            vectors_array = np.array(vectors, dtype='float32')
            self.vector_store.add_vectors(vectors_array)

        return len(frames)

    def migrate(self) -> bool:
        """执行完整迁移流程"""
        print("=" * 60)
        print("帧探·GameLens - 数据库迁移工具")
        print("=" * 60)
        print()

        # 1. 验证 JSON 文件
        print("Phase 1: 验证数据源")
        print("-" * 40)
        if not self.validate_json_file():
            return False
        print()

        # 2. 备份原始文件
        print("Phase 2: 备份原始文件")
        print("-" * 40)
        if not self.backup_json_file():
            logger.warning("备份失败，但继续迁移")
        print()

        # 3. 初始化数据库
        print("Phase 3: 初始化数据库")
        print("-" * 40)
        init_db()
        print()

        # 4. 加载 JSON 数据
        print("Phase 4: 加载 JSON 数据")
        print("-" * 40)
        index = self.load_json_index()
        videos = index.get('videos', [])
        print()

        # 5. 迁移数据
        print("Phase 5: 迁移数据")
        print("-" * 40)

        total_frames_migrated = 0

        for video in tqdm(videos, desc="  迁移进度"):
            try:
                frame_count = self.migrate_video(video)
                total_frames_migrated += frame_count
            except Exception as e:
                logger.error(f"  迁移视频 {video.get('bvid')} 失败: {e}")
                continue

        print()
        print(f"✓ 迁移完成: {len(videos)} 视频, {total_frames_migrated} 帧")
        print()

        # 6. 保存 FAISS 索引
        print("Phase 6: 保存 FAISS 索引")
        print("-" * 40)
        try:
            self.vector_store.save_index()
            print()
        except Exception as e:
            logger.error(f"保存 FAISS 索引失败: {e}")
            return False

        # 7. 验证结果
        print("Phase 7: 验证结果")
        print("-" * 40)
        self.verify_migration(len(videos), total_frames_migrated)
        print()

        # 8. 完成报告
        print("=" * 60)
        print("迁移完成!")
        print("=" * 60)
        print(f"✓ 视频数: {len(videos)}")
        print(f"✓ 帧数: {total_frames_migrated}")
        print(f"✓ SQLite 数据库: {PROJECT_ROOT / 'data' / 'video_frames.db'}")
        print(f"✓ FAISS 索引: {PROJECT_ROOT / 'data' / 'faiss_index.index'}")
        print()
        print("下一步:")
        print("  1. 测试匹配功能")
        print("  2. 如确认无误，可删除原始 JSON 文件:")
        print(f"     rm {VIDEO_INDEX_FILE}")
        print("=" * 60)

        return True

    def verify_migration(self, expected_videos: int, expected_frames: int):
        """验证迁移结果"""
        stats = get_stats()

        # 检查视频数
        actual_videos = stats['total_videos']
        if actual_videos == expected_videos:
            print(f"✓ 视频数验证通过: {actual_videos}")
        else:
            print(f"⚠ 视频数不匹配: 期望 {expected_videos}, 实际 {actual_videos}")

        # 检查帧数
        actual_frames = stats['total_frames']
        if actual_frames == expected_frames:
            print(f"✓ 帧数验证通过: {actual_frames}")
        else:
            print(f"⚠ 帧数不匹配: 期望 {expected_frames}, 实际 {actual_frames}")

        # 检查 FAISS 索引
        faiss_count = self.vector_store.get_vector_count()
        if faiss_count == expected_frames:
            print(f"✓ FAISS 向量数验证通过: {faiss_count}")
        else:
            print(f"⚠ FAISS 向量数不匹配: 期望 {expected_frames}, 实际 {faiss_count}")


# ==================== 主函数 ====================
def main():
    """主函数"""
    try:
        migrator = DatabaseMigrator()
        success = migrator.migrate()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("\n用户中断，退出程序")
        sys.exit(1)
    except Exception as e:
        logger.error(f"迁移失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
