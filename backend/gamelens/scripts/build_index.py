#!/usr/bin/env python3
"""
帧探·GameLens - 视频索引构建脚本

流程: 下载视频 → 抽帧 → 提取特征 → 生成JSON索引

使用方法:
    python scripts/build_video_index.py

环境变量:
    FRAME_INTERVAL - 抽帧间隔(秒)，默认5秒

依赖:
    pip install -r scripts/requirements.txt
"""

import os
import sys
import json
import math
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

import cv2
import numpy as np
import tensorflow as tf
import yt_dlp
from tqdm import tqdm
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 配置 ====================
# 项目根目录（向上3级到 backend 目录）
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VIDEO_FRAMES_DIR = DATA_DIR / "video_frames"
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"
VIDEO_LIST_FILE = DATA_DIR / "videos.txt"
INDEX_FILE = DATA_DIR / "video_index.json"

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
    """从B站URL中提取BV号"""
    if "BV" in url:
        return url[url.find("BV"):url.find("BV") + 12]
    return ""


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
            url: B站视频URL

        Returns:
            视频信息字典，包含bvid, title, author, duration, path
        """
        bvid = get_bvid_from_url(url)

        ydl_opts = {
            # B站专用格式配置 - 选择1080P及以下，自动合并音视频
            'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
            'outtmpl': str(self.output_dir / '%(id)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            # 确保下载最佳质量
            'prefer_ffmpeg': True,
            # 合并格式
            'merge_output_format': 'mp4',
        }

        logger.info(f"正在下载: {url}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                video_info = {
                    'bvid': info.get('id', bvid),
                    'title': info.get('title', 'Unknown'),
                    'author': info.get('uploader', 'Unknown'),
                    'duration': int(info.get('duration', 0)),
                    'url': url,
                    'path': str(self.output_dir / f"{info['id']}.mp4")
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
            feature = self.extract(str(full_path))
            frame['feature'] = feature.tolist()  # 转换为列表以便JSON序列化

        logger.info("✓ 特征提取完成")

        return frames


# ==================== 索引构建模块 ====================

class IndexBuilder:
    """索引构建器 - 生成最终的视频索引JSON"""

    @staticmethod
    def build(videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        构建视频索引

        Args:
            videos: 视频信息列表（包含帧和特征）

        Returns:
            完整的索引字典
        """
        total_frames = sum(len(v.get('frames', [])) for v in videos)

        index = {
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'config': {
                'frame_interval': FRAME_INTERVAL,
                'top_k_results': TOP_K_RESULTS,
                'min_similarity': MIN_SIMILARITY,
                'feature_dimension': 1280  # MobileNetV2输出维度
            },
            'total_videos': len(videos),
            'total_frames': total_frames,
            'videos': videos
        }

        return index

    @staticmethod
    def merge_with_existing(new_videos: List[Dict[str, Any]], existing_index: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并新旧视频数据

        Args:
            new_videos: 新处理的视频列表
            existing_index: 现有索引数据

        Returns:
            合并后的完整索引
        """
        existing_bvids = {v['bvid'] for v in existing_index.get('videos', [])}

        # 只添加新的视频（避免重复）
        merged_videos = existing_index.get('videos', [])
        new_bvids = {v['bvid'] for v in new_videos}

        for video in new_videos:
            if video['bvid'] not in existing_bvids:
                merged_videos.append(video)
            else:
                # 如果BV号已存在，更新该视频的数据
                for i, v in enumerate(merged_videos):
                    if v['bvid'] == video['bvid']:
                        merged_videos[i] = video
                        break

        total_frames = sum(len(v.get('frames', [])) for v in merged_videos)

        index = {
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'config': existing_index.get('config', {
                'frame_interval': FRAME_INTERVAL,
                'top_k_results': TOP_K_RESULTS,
                'min_similarity': MIN_SIMILARITY,
                'feature_dimension': 1280
            }),
            'total_videos': len(merged_videos),
            'total_frames': total_frames,
            'videos': merged_videos
        }

        return index

    @staticmethod
    def save(index: Dict[str, Any], output_path: Path = INDEX_FILE):
        """保存索引到JSON文件"""
        logger.info(f"正在保存索引到: {output_path}")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"✓ 索引已保存 ({file_size_mb:.2f} MB)")


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


def load_existing_index() -> set:
    """加载现有索引，返回已处理的BV号集合"""
    if not INDEX_FILE.exists():
        return set()

    logger.info(f"检测到现有索引: {INDEX_FILE}")
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            index = json.load(f)

        processed_bvids = {video['bvid'] for video in index.get('videos', [])}
        logger.info(f"已处理 {len(processed_bvids)} 个视频，将跳过")
        return processed_bvids
    except Exception as e:
        logger.warning(f"读取现有索引失败: {e}，将重新处理所有视频")
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
    print()

    # 0. 加载现有索引（用于增量更新）
    processed_bvids = load_existing_index()
    existing_index = {}
    if processed_bvids:
        try:
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                existing_index = json.load(f)
        except:
            pass
    print()

    # 1. 加载视频列表
    urls = load_video_list()

    # 过滤出需要处理的视频（排除已处理的）
    new_urls = []
    for url in urls:
        bvid = get_bvid_from_url(url)
        if bvid not in processed_bvids:
            new_urls.append(url)
        else:
            logger.info(f"跳过已处理: {bvid}")

    if not new_urls:
        logger.info("所有视频都已处理，无需重新下载")
        logger.info(f"当前索引包含 {len(processed_bvids)} 个视频")
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

    # 5. 构建并保存索引
    logger.info("Phase 4: 构建索引")
    logger.info("-" * 40)

    # 移除视频文件路径（不需要在前端使用）
    for video in videos:
        video.pop('path', None)

    # 如果有现有索引，合并新旧数据
    if existing_index:
        logger.info("合并新旧索引数据...")
        index = IndexBuilder.merge_with_existing(videos, existing_index)
    else:
        index = IndexBuilder.build(videos)

    IndexBuilder.save(index)
    print()

    # 6. 汇总报告
    print("=" * 60)
    print("构建完成!")
    print("=" * 60)
    print(f"✓ 新处理视频数: {len(videos)}")
    print(f"✓ 索引总视频数: {index['total_videos']}")
    print(f"✓ 总帧数: {index['total_frames']}")
    print(f"✓ 索引文件: {INDEX_FILE}")
    print(f"✓ 帧目录: {VIDEO_FRAMES_DIR}")
    print()
    print("下一步:")
    print("  1. 运行前端服务: python -m http.server 8000")
    print("  2. 访问: http://localhost:8000")
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
