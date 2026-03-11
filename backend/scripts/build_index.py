#!/usr/bin/env python3
"""
帧探·GameLens - 视频索引构建脚本

流程: 下载视频 → 抽帧 → 提取特征 → 保存到 SQLite + FAISS

使用方法:
    cd backend
    python scripts/build_index.py

环境变量:
    FRAME_INTERVAL - 抽帧间隔(秒)，默认5秒

依赖:
    pip install faiss-cpu numpy tensorflow yt-dlp opencv-python pillow tqdm python-dotenv
"""

import os
import sys
import json
import math
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

import cv2
import numpy as np
import tensorflow as tf
import yt_dlp
from tqdm import tqdm
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from gamelens.core.database import init_db, insert_video, insert_frames_batch, video_exists
from gamelens.core.vector_store import VectorStore, load_or_create_store

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 配置 ====================
# 项目根目录（向上2级到 backend 目录）
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VIDEO_FRAMES_DIR = DATA_DIR / "video_frames"
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"
VIDEO_LIST_FILE = DATA_DIR / "videos.txt"
DATABASE_FILE = DATA_DIR / "video_frames.db"
FAISS_INDEX_FILE = DATA_DIR / "faiss_index.index"

# 从环境变量读取配置，使用默认值
FRAME_INTERVAL = int(os.getenv("FRAME_INTERVAL", "5"))  # 抽帧间隔（秒）
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))   # 匹配结果数量
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.5"))  # 最低相似度

# 创建必要的目录
VIDEO_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 工具函数 ====================

def format_timestamp(seconds: int) -> str:
    """将秒数转换为时间戳格式 MM:SS"""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def get_bvid_from_url(url: str) -> str:
    """从B站URL中提取BV号和分P信息

    Returns:
        (bvid, part_number) - BV号和分P序号，如果没有分P则返回 (bvid, None)
    """
    import re

    # 提取BV号
    bv_match = re.search(r'(BV[\w]+)', url)
    bvid = bv_match.group(1) if bv_match else ""

    # 提取分P序号
    p_match = re.search(r'[?&]p=(\d+)', url)
    part = int(p_match.group(1)) if p_match else None

    return bvid, part


def get_video_identifier(url: str) -> str:
    """获取视频唯一标识符（包含分P信息）"""
    bvid, part = get_bvid_from_url(url)
    if part:
        return f"{bvid}_p{part}"
    return bvid


# ==================== 视频下载模块 ====================

class VideoDownloader:
    """视频下载器 - 使用yt-dlp下载B站视频"""

    def __init__(self, output_dir: Path = DOWNLOADS_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download(self, url: str) -> Dict[str, Any]:
        """
        下载单个视频

        Args:
            url: B站视频URL（支持分P）

        Returns:
            视频信息字典，包含bvid, title, author, duration, path
        """
        bvid, part = get_bvid_from_url(url)
        video_id = get_video_identifier(url)
        video_file = self.output_dir / f"{video_id}.mp4"

        # 检查视频文件是否已存在
        if video_file.exists():
            logger.info(f"视频文件已存在，跳过下载: {video_id}")
            # 仍然需要获取视频元数据
            try:
                with yt_dlp.YoutubeDL({
                    'quiet': True,
                    'noplaylist': True,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'referer': 'https://www.bilibili.com/'
                }) as ydl:
                    info = ydl.extract_info(url, download=False)
                    return {
                        'bvid': video_id,  # 使用包含分P的标识符
                        'title': info.get('title', 'Unknown'),
                        'author': info.get('uploader', 'Unknown'),
                        'duration': int(info.get('duration', 0)),
                        'url': url,
                        'path': str(video_file)
                    }
            except Exception as e:
                logger.warning(f"获取视频信息失败: {e}")
                return None

        ydl_opts = {
            # B站专用格式配置 - 选择1080P及以下，自动合并音视频
            'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
            'outtmpl': str(self.output_dir / f'{video_id}.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            # 确保下载最佳质量
            'prefer_ffmpeg': True,
            # 合并格式
            'merge_output_format': 'mp4',
            # 不覆盖已存在文件
            'nooverwrites': True,
            # 不下载播放列表（合集/分P），只下载单个视频
            'noplaylist': True,
            # 添加User-Agent绕过反爬虫
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # 添加Referer
            'referer': 'https://www.bilibili.com/',
            # 使用cookies（可选）
            'cookies': '',
            # 禁用SSL验证（如果需要）
            'nocheckcertificate': False,
        }

        logger.info(f"正在下载: {url} (标识符: {video_id})")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                video_info = {
                    'bvid': video_id,  # 使用包含分P的标识符
                    'title': info.get('title', 'Unknown'),
                    'author': info.get('uploader', 'Unknown'),
                    'duration': int(info.get('duration', 0)),
                    'url': url,
                    'path': str(self.output_dir / f"{video_id}.mp4")
                }

                logger.info(f"✓ 下载完成: {video_info['title']}")
                return video_info

        except Exception as e:
            logger.error(f"✗ 下载失败: {url} - {e}")
            return None


# ==================== 帧提取模块 ====================

class FrameExtractor:
    """视频帧提取器 - 使用OpenCV提取关键帧"""

    def __init__(self, output_dir: Path = VIDEO_FRAMES_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract(self, video_info: Dict[str, Any], interval: int = FRAME_INTERVAL) -> List[Dict[str, Any]]:
        """
        从视频中提取帧

        Args:
            video_info: 视频信息字典
            interval: 抽帧间隔（秒）

        Returns:
            帧信息列表，每帧包含timestamp, seconds, image_path
        """
        video_path = video_info['path']
        bvid = video_info['bvid']

        # 创建该视频的帧目录
        frame_dir = self.output_dir / bvid
        frame_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"正在提取帧: {video_info['title']}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"无法打开视频: {video_path}")
            return []

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = video_info['duration']

        frames = []
        frame_interval = int(fps * interval)

        # 遍历视频帧
        with tqdm(total=duration // interval + 1, desc=f"  提取进度") as pbar:
            for time_seconds in range(0, duration, interval):
                # 跳转到指定时间点
                cap.set(cv2.CAP_PROP_POS_MSEC, time_seconds * 1000)

                ret, frame = cap.read()
                if not ret:
                    break

                # 保存帧
                frame_filename = f"frame_{time_seconds:06d}.jpg"
                frame_path = frame_dir / frame_filename
                cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

                frames.append({
                    'timestamp': format_timestamp(time_seconds),
                    'seconds': time_seconds,
                    'image_path': str(frame_path.relative_to(PROJECT_ROOT))
                })

                pbar.update(1)

        cap.release()
        logger.info(f"✓ 提取完成: 共{len(frames)}帧")

        return frames


# ==================== 特征提取模块 ====================

class FeatureExtractor:
    """图像特征提取器 - 使用MobileNetV2提取特征"""

    def __init__(self):
        self.model = None
        logger.info("正在加载MobileNetV2模型...")

    def load_model(self):
        """加载TensorFlow MobileNetV2模型"""
        if self.model is None:
            # 使用MobileNetV2作为特征提取器
            self.model = tf.keras.applications.MobileNetV2(
                include_top=False,  # 不包含分类层
                pooling='avg',      # 全局平均池化
                weights='imagenet'  # 使用预训练权重
            )
            logger.info("✓ MobileNetV2模型加载完成")

    def extract(self, image_path: str) -> np.ndarray:
        """
        提取单张图片的特征向量

        Args:
            image_path: 图片路径

        Returns:
            1280维特征向量 (Float32Array)
        """
        if self.model is None:
            self.load_model()

        # 加载并预处理图片
        img = tf.keras.preprocessing.image.load_img(
            image_path,
            target_size=(224, 224)
        )
        img_array = tf.keras.preprocessing.image.img_to_array(img)

        # 预处理（MobileNetV2的预处理方式）
        img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
        img_array = np.expand_dims(img_array, axis=0)

        # 提取特征
        feature = self.model.predict(img_array, verbose=0)[0]

        return feature.astype(np.float32)

    def extract_batch(self, frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量提取多张图片的特征

        Args:
            frames: 帧信息列表

        Returns:
            添加了feature字段的帧信息列表
        """
        self.load_model()

        logger.info(f"正在提取{len(frames)}张图片的特征...")

        for frame in tqdm(frames, desc="  特征提取"):
            full_path = PROJECT_ROOT / frame['image_path']
            try:
                feature = self.extract(str(full_path))
                frame['feature'] = feature.tolist()  # 转换为列表以便JSON序列化
            except Exception as e:
                logger.error(f"  特征提取失败: {frame['image_path']} - {e}")
                frame['feature'] = None

        # 检查特征提取结果
        with_feature = sum(1 for f in frames if f.get('feature') is not None)
        logger.info(f"✓ 特征提取完成: {with_feature}/{len(frames)} 帧成功提取特征")

        return frames


# ==================== 索引构建模块 ====================

class IndexBuilder:
    """索引构建器 - 将视频和帧数据保存到 SQLite + FAISS"""

    def __init__(self):
        """初始化索引构建器"""
        # 确保数据库已初始化
        init_db()

        # 创建或加载 FAISS 索引
        self.vector_store = load_or_create_store()
        logger.info(f"FAISS 索引状态: {self.vector_store.get_vector_count()} 个向量")

    def save_video(self, video_info: Dict[str, Any], frames: List[Dict[str, Any]]) -> bool:
        """
        保存单个视频及其帧到数据库

        Args:
            video_info: 视频信息（bvid, title, author, duration, url）
            frames: 帧信息列表，包含 timestamp, seconds, image_path, feature

        Returns:
            是否成功保存
        """
        try:
            bvid = video_info['bvid']

            # 1. 插入视频记录
            video_id = insert_video(video_info)
            logger.info(f"  插入视频记录: {bvid} (ID: {video_id})")

            # 2. 准备帧数据和向量
            frame_records = []
            vectors = []

            logger.info(f"  开始准备 {len(frames)} 个帧的数据和向量...")

            for idx, frame in enumerate(frames):
                frame_records.append({
                    'video_id': video_id,
                    'bvid': bvid,
                    'frame_index': idx,
                    'timestamp': frame['timestamp'],
                    'seconds': frame['seconds'],
                    'image_path': frame['image_path']
                })

                if 'feature' in frame:
                    vectors.append(frame['feature'])
                else:
                    logger.warning(f"  帧 {idx} ({frame.get('image_path')}) 缺少特征向量")

            logger.info(f"  准备完成: {len(frame_records)} 条帧记录, {len(vectors)} 个特征向量")

            # 3. 批量插入帧记录
            insert_frames_batch(frame_records)
            logger.info(f"  插入 {len(frame_records)} 条帧记录")

            # 4. 添加向量到 FAISS
            if vectors:
                vectors_array = np.array(vectors, dtype='float32')
                n_added = self.vector_store.add_vectors(vectors_array)
                logger.info(f"  添加 {n_added} 个向量到 FAISS 索引")
            else:
                logger.warning(f"  警告: 无特征向量，请检查特征提取是否正常")

            return True

        except Exception as e:
            logger.error(f"保存视频 {video_info.get('bvid')} 失败: {e}")
            return False

    def finalize(self):
        """完成索引构建，保存 FAISS 索引"""
        try:
            self.vector_store.save_index()
            logger.info("✓ FAISS 索引已保存")
        except Exception as e:
            logger.error(f"保存 FAISS 索引失败: {e}")


# ==================== 主流程 ====================

def load_video_list() -> List[str]:
    """从videos.txt加载视频URL列表"""
    if not VIDEO_LIST_FILE.exists():
        logger.error(f"视频列表文件不存在: {VIDEO_LIST_FILE}")
        logger.info(f"请创建 {VIDEO_LIST_FILE} 并添加B站视频链接")
        logger.info(f"可以参考 {VIDEO_LIST_FILE}.example")
        sys.exit(1)

    with open(VIDEO_LIST_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    if not urls:
        logger.error(f"视频列表为空: {VIDEO_LIST_FILE}")
        sys.exit(1)

    logger.info(f"找到 {len(urls)} 个视频链接")
    return urls


def load_existing_videos() -> set:
    """从数据库加载已处理的BV号集合"""
    if not DATABASE_FILE.exists():
        return set()

    logger.info(f"检测到现有数据库: {DATABASE_FILE}")
    try:
        from gamelens.core.database import get_all_videos
        videos = get_all_videos()
        processed_bvids = {v['bvid'] for v in videos}
        logger.info(f"已处理 {len(processed_bvids)} 个视频，将跳过")
        return processed_bvids
    except Exception as e:
        logger.warning(f"读取数据库失败: {e}，将重新处理所有视频")
        return set()


def main():
    """主函数：执行完整的索引构建流程"""
    print("=" * 60)
    print("帧探·GameLens - 视频索引构建工具")
    print("=" * 60)
    print()

    # 配置信息
    logger.info(f"配置信息:")
    logger.info(f"  - 抽帧间隔: {FRAME_INTERVAL}秒")
    logger.info(f"  - 特征维度: 1280 (MobileNetV2)")
    logger.info(f"  - 输出目录: {DATA_DIR}")
    logger.info(f"  - 帧保存目录: {VIDEO_FRAMES_DIR}")
    logger.info(f"  - 数据库: {DATABASE_FILE}")
    logger.info(f"  - FAISS 索引: {FAISS_INDEX_FILE}")
    print()

    # 0. 加载现有索引（用于增量更新）
    processed_bvids = load_existing_videos()
    print()

    # 1. 加载视频列表
    urls = load_video_list()

    # 过滤出需要处理的视频（排除已处理的）
    new_urls = []
    for url in urls:
        video_id = get_video_identifier(url)
        if video_id not in processed_bvids:
            new_urls.append(url)
        else:
            logger.info(f"跳过已处理: {video_id}")

    if not new_urls:
        logger.info("所有视频都已处理，无需重新下载")
        logger.info(f"当前数据库包含 {len(processed_bvids)} 个视频")
        return

    logger.info(f"需要处理 {len(new_urls)} 个新视频")
    print()

    # 2. 下载视频
    logger.info("Phase 1: 下载视频")
    logger.info("-" * 40)
    downloader = VideoDownloader()
    videos = []

    for url in new_urls:
        video_info = downloader.download(url)
        if video_info:
            videos.append(video_info)
    print()

    if not videos:
        logger.error("没有成功下载任何视频，退出")
        sys.exit(1)

    # 3. 提取帧
    logger.info("Phase 2: 提取视频帧")
    logger.info("-" * 40)
    extractor = FrameExtractor()

    for video in videos:
        frames = extractor.extract(video)
        video['frames'] = frames
    print()

    # 4. 提取特征
    logger.info("Phase 3: 提取图像特征")
    logger.info("-" * 40)
    feature_extractor = FeatureExtractor()

    for video in videos:
        if video.get('frames'):
            feature_extractor.extract_batch(video['frames'])
    print()

    # 5. 保存到数据库
    logger.info("Phase 4: 保存到数据库")
    logger.info("-" * 40)
    index_builder = IndexBuilder()

    for video in videos:
        # 移除视频文件路径（不需要保存到数据库）
        video_for_db = {
            'bvid': video['bvid'],
            'title': video.get('title', ''),
            'author': video.get('author', ''),
            'duration': video.get('duration', 0),
            'url': video.get('url', ''),
            'thumbnail_url': video.get('thumbnail_url', '')
        }

        if index_builder.save_video(video_for_db, video.get('frames', [])):
            logger.info(f"✓ 保存视频: {video['bvid']} ({len(video.get('frames', []))} 帧)")
        else:
            logger.error(f"✗ 保存视频失败: {video['bvid']}")

    print()

    # 6. 完成并保存 FAISS 索引
    logger.info("Phase 5: 完成索引构建")
    logger.info("-" * 40)
    index_builder.finalize()
    print()

    # 7. 汇总报告
    print("=" * 60)
    print("构建完成!")
    print("=" * 60)
    print(f"✓ 新处理视频数: {len(videos)}")

    # 从数据库获取统计信息
    from gamelens.core.database import get_stats
    stats = get_stats()
    print(f"✓ 数据库总视频数: {stats['total_videos']}")
    print(f"✓ 数据库总帧数: {stats['total_frames']}")
    print(f"✓ 数据库文件: {DATABASE_FILE}")
    print(f"✓ FAISS 索引文件: {FAISS_INDEX_FILE}")
    print(f"✓ 帧目录: {VIDEO_FRAMES_DIR}")
    print()
    print("下一步:")
    print("  1. 启动后端服务: python -m gamelens.server")
    print("  2. 启动前端服务: cd frontend && python -m http.server 8000")
    print("  3. 访问: http://localhost:8000")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n用户中断，退出程序")
        sys.exit(0)
    except Exception as e:
        logger.error(f"发生错误: {e}", exc_info=True)
        sys.exit(1)
