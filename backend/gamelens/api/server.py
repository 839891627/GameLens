#!/usr/bin/env python3.12
"""
帧探·GameLens - 后端服务器
提供视频管理和自动解析功能
"""

import os
import re
import threading
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

import faiss
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

import sys

# 导入核心模块
from gamelens.core.database import (
    get_db, init_db, get_videos_with_frame_count, get_video_by_bvid,
    get_total_videos_count, get_total_frames_count, get_stats, db_exists, DB_PATH
)
from gamelens.core.vector_store import VectorStore, load_or_create_store, IndexNotInitialized
from gamelens.core.feature_cache import get_feature_cache, get_cached_feature, cache_feature

# 配置日志（无缓冲，强制刷新）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# 确保日志处理器无缓冲
for handler in logger.handlers:
    handler.flush = lambda: handler.stream.flush()

# ==================== 配置 ====================
# 项目根目录（从 api/ 向上三级到 backend 目录）
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VIDEO_LIST_FILE = DATA_DIR / "videos.txt"
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build_index.py"
VIDEO_FRAMES_DIR = DATA_DIR / "video_frames"
DATABASE_FILE = DB_PATH
LOG_FILE = DATA_DIR / "parse.log"  # 解析日志文件

# ==================== Flask 应用 ====================
# 纯 API 服务器，不托管静态文件（前后端分离）
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局状态
parse_status = {
    'is_parsing': False,
    'progress': 0,
    'logs': []
}


# ==================== 工具函数 ====================
def load_videos() -> List[Dict[str, Any]]:
    """加载视频列表"""
    if not VIDEO_LIST_FILE.exists():
        return []

    with open(VIDEO_LIST_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # 从数据库加载已处理的视频
    processed_bvids = set()
    video_titles = {}

    if db_exists():
        try:
            with get_db() as conn:
                videos = conn.execute("SELECT bvid, title FROM videos").fetchall()
                for v in videos:
                    processed_bvids.add(v['bvid'])
                    video_titles[v['bvid']] = v['title']
        except Exception as e:
            logger.warning(f"从数据库读取已处理视频失败: {e}")

    # 构建视频列表
    videos = []
    for url in urls:
        bvid = extract_bvid(url)
        videos.append({
            'url': url,
            'bvid': bvid,
            'processed': bvid in processed_bvids,
            'title': video_titles.get(bvid, '')
        })

    return videos


def extract_bvid(url: str) -> str:
    """从URL提取BV号和分P信息，返回唯一标识符"""
    # 提取BV号（BV号长度通常是10-12位）
    bv_match = re.search(r'(BV[0-9a-zA-Z]{10,12})', url)
    bvid = bv_match.group(1) if bv_match else ""

    # 提取分P序号
    p_match = re.search(r'[?&]p=(\d+)', url)
    part = p_match.group(1) if p_match else None

    # 如果有分P，返回带分P的标识符
    if part:
        return f"{bvid}_p{part}"
    return bvid


def get_video_title(bvid: str, index_file: Path = None) -> str:
    """从数据库获取视频标题"""
    # 从数据库获取
    if db_exists():
        try:
            video = get_video_by_bvid(bvid)
            if video:
                return video.get('title', '')
        except Exception:
            pass

    return ''


def save_videos(videos: List[Dict[str, Any]]):
    """保存视频列表到文件"""
    urls = [v['url'] for v in videos]
    with open(VIDEO_LIST_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(urls))


def add_log(message: str, log_type: str = 'info'):
    """添加解析日志（同时保存到文件）"""
    log_entry = {
        'time': datetime.now().strftime('%H:%M:%S'),
        'message': message,
        'type': log_type
    }
    parse_status['logs'].append(log_entry)

    # 只保留最近100条
    if len(parse_status['logs']) > 100:
        parse_status['logs'] = parse_status['logs'][-100:]

    # 写入日志文件
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] [{log_type.upper()}] {message}\n")
    except Exception as e:
        logger.error(f"写入日志文件失败: {e}")


# ==================== 解析线程 ====================
def run_parse_script():
    """在后台线程运行解析脚本"""
    try:
        add_log('开始下载视频...', 'info')

        # 检查脚本是否存在
        if not BUILD_SCRIPT.exists():
            add_log(f'✗ 解析脚本不存在: {BUILD_SCRIPT}', 'error')
            logger.error(f"解析脚本不存在: {BUILD_SCRIPT}")
            return

        # 检查 Python 环境
        add_log('检查 Python 环境...', 'info')
        check_result = subprocess.run(
            [sys.executable, '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if check_result.returncode == 0:
            add_log(f'Python 版本: {check_result.stdout.strip()}', 'info')
        else:
            add_log('✗ Python 不可用', 'error')
            return

        # 检查依赖
        add_log('检查必要依赖...', 'info')
        dependencies = ['yt_dlp', 'cv2', 'tensorflow', 'numpy']
        missing_deps = []
        for dep in dependencies:
            try:
                result = subprocess.run(
                    [sys.executable, '-c', f'import {dep.split(".")[0]}'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode != 0:
                    missing_deps.append(dep)
            except:
                missing_deps.append(dep)

        if missing_deps:
            add_log(f'✗ 缺少依赖: {", ".join(missing_deps)}', 'error')
            add_log('请在服务器上运行: pip install -r scripts/requirements.txt', 'error')
            return

        # 确保必要目录存在
        add_log('创建必要目录...', 'info')
        try:
            (PROJECT_ROOT / "downloads").mkdir(parents=True, exist_ok=True)
            (PROJECT_ROOT / "video_frames").mkdir(parents=True, exist_ok=True)
            add_log('✓ 目录创建完成', 'info')
        except Exception as e:
            add_log(f'✗ 创建目录失败: {e}', 'error')
            logger.error(f"创建目录失败: {e}")
            return

        # 运行解析脚本
        add_log(f'执行解析脚本: {BUILD_SCRIPT}', 'info')
        logger.info(f"工作目录: {PROJECT_ROOT}")

        # 使用 PPIPE 实时捕获输出
        process = subprocess.Popen(
            [sys.executable, str(BUILD_SCRIPT)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 将 stderr 合并到 stdout
            text=True,
            bufsize=1,  # 行缓冲
            universal_newlines=True
        )

        # 实时读取输出
        try:
            for line in process.stdout:
                line = line.strip()
                if line:
                    add_log(line, 'info')
                    logger.info(f"[解析脚本] {line}")

        except Exception as e:
            add_log(f'✗ 读取输出时出错: {str(e)}', 'error')
            logger.error(f"读取输出时出错: {e}")

        # 等待进程结束
        returncode = process.wait()

        if returncode == 0:
            add_log('✓ 解析完成！', 'success')
        else:
            add_log(f'✗ 解析失败 (退出码: {returncode})', 'error')

    except Exception as e:
        add_log(f'✗ 解析出错: {str(e)}', 'error')
        logger.error(f"解析出错: {e}", exc_info=True)
    finally:
        parse_status['is_parsing'] = False
        parse_status['progress'] = 100


# ==================== API 路由 ====================

# 注意：前端采用前后端分离架构，静态文件由前端独立提供
# 后端仅提供 API 接口

@app.route('/frames/<path:filepath>')
def serve_frame(filepath):
    """提供视频帧图片文件"""
    try:
        # 安全检查：确保路径不包含 .. 等危险字符
        if '..' in filepath or filepath.startswith('/'):
            return jsonify({'success': False, 'error': 'Invalid path'}), 400

        # 构建完整路径
        frame_path = DATA_DIR / 'video_frames' / filepath

        # 检查文件是否存在
        if not frame_path.exists():
            return jsonify({'success': False, 'error': 'File not found'}), 404

        # 返回文件
        return send_from_directory(str(frame_path.parent), frame_path.name)
    except Exception as e:
        logger.error(f"提供文件失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/videos', methods=['GET'])
def get_videos_api():
    """获取视频列表（用于 admin 页面，不含详细帧数据）"""
    try:
        # 优先从 SQLite 数据库加载
        if db_exists():
            videos = get_videos_with_frame_count()

            # 格式化输出
            formatted_videos = []
            for video in videos:
                formatted_videos.append({
                    'bvid': video['bvid'],
                    'url': video['url'],
                    'title': video.get('title', ''),
                    'author': video.get('author', ''),
                    'duration': video.get('duration', 0),
                    'processed': True,  # 在数据库中的视频都是已解析的
                    'frame_count': video['frame_count']
                })

            return jsonify({
                'success': True,
                'data': formatted_videos
            })

        # 如果数据库不存在，返回简化列表（从 videos.txt）
        videos = load_videos()
        return jsonify({
            'success': True,
            'data': videos
        })
    except Exception as e:
        logger.error(f"获取视频列表失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/videos/index', methods=['GET'])
def get_video_index_api():
    """获取完整视频索引（包含帧数据，用于匹配功能）"""
    try:
        if not db_exists():
            return jsonify({
                'success': False,
                'error': '数据库不存在，请先解析视频'
            }), 404

        # 从 SQLite 获取所有视频和帧数据
        with get_db() as conn:
            videos = conn.execute("""
                SELECT * FROM videos
                ORDER BY created_at DESC
            """).fetchall()

            result = []
            for video in videos:
                video_dict = dict(video)

                # 获取该视频的所有帧
                frames = conn.execute("""
                    SELECT * FROM frames
                    WHERE video_id = ?
                    ORDER BY seconds ASC
                """, (video['id'],)).fetchall()

                # 格式化帧数据（不包含特征向量，太大）
                video_dict['frames'] = []
                for frame in frames:
                    frame_dict = {
                        'id': frame['id'],
                        'frame_index': frame['frame_index'],
                        'timestamp': frame['timestamp'],
                        'seconds': frame['seconds'],
                        'image_path': frame['image_path']
                    }
                    video_dict['frames'].append(frame_dict)

                result.append(video_dict)

            return jsonify({
                'success': True,
                'data': result
            })
    except Exception as e:
        logger.error(f"获取视频索引失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/videos', methods=['POST'])
def add_video_api():
    """添加单个视频"""
    try:
        data = request.json
        url = data.get('url', '').strip()

        if not url:
            return jsonify({
                'success': False,
                'error': '请提供视频链接'
            }), 400

        # 验证B站链接
        if 'bilibili.com/video/' not in url or 'BV' not in url:
            return jsonify({
                'success': False,
                'error': '无效的B站视频链接'
            }), 400

        # 加载现有视频
        videos = load_videos()
        bvid = extract_bvid(url)

        # 检查是否已存在
        if any(v['bvid'] == bvid for v in videos):
            return jsonify({
                'success': False,
                'error': f'视频 {bvid} 已存在'
            }), 400

        # 添加视频
        videos.insert(0, {
            'url': url,
            'bvid': bvid,
            'processed': False,
            'title': ''
        })

        # 保存到文件
        save_videos(videos)

        add_log(f'已添加视频: {bvid}', 'success')

        return jsonify({
            'success': True,
            'message': f'已添加视频: {bvid}'
        })
    except Exception as e:
        logger.error(f"添加视频失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/videos/bulk', methods=['POST'])
def add_bulk_videos_api():
    """批量添加视频"""
    try:
        data = request.json
        urls_text = data.get('urls', '')

        urls = [line.strip() for line in urls_text.split('\n') if line.strip()]

        if not urls:
            return jsonify({
                'success': False,
                'error': '请提供视频链接'
            }), 400

        # 过滤有效链接
        valid_urls = [
            url for url in urls
            if 'bilibili.com/video/' in url and 'BV' in url
        ]

        if not valid_urls:
            return jsonify({
                'success': False,
                'error': '没有有效的B站视频链接'
            }), 400

        # 加载现有视频
        videos = load_videos()
        existing_bvids = {v['bvid'] for v in videos}

        # 添加新视频
        added_count = 0
        for url in valid_urls:
            bvid = extract_bvid(url)
            if bvid and bvid not in existing_bvids:
                videos.insert(0, {
                    'url': url,
                    'bvid': bvid,
                    'processed': False,
                    'title': ''
                })
                added_count += 1

        # 保存到文件
        save_videos(videos)

        add_log(f'批量添加完成: 新增 {added_count} 个视频', 'success')

        return jsonify({
            'success': True,
            'message': f'批量添加完成: 新增 {added_count} 个视频'
        })
    except Exception as e:
        logger.error(f"批量添加失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/videos/<int:index>', methods=['DELETE'])
def delete_video_api(index):
    """删除视频"""
    try:
        videos = load_videos()

        if index < 0 or index >= len(videos):
            return jsonify({
                'success': False,
                'error': '无效的视频索引'
            }), 400

        deleted_video = videos.pop(index)
        save_videos(videos)

        add_log(f'已删除视频: {deleted_video["bvid"]}', 'info')

        return jsonify({
            'success': True,
            'message': f'已删除视频: {deleted_video["bvid"]}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats', methods=['GET'])
def get_stats_api():
    """获取统计信息（轻量级，从 SQLite 获取）"""
    try:
        # 从 videos.txt 获取总视频数
        total = 0
        if VIDEO_LIST_FILE.exists():
            with open(VIDEO_LIST_FILE, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                total = len(urls)

        # 从 SQLite 获取已处理视频数和帧数
        processed = 0
        total_frames = 0
        if db_exists():
            processed = get_total_videos_count()
            total_frames = get_total_frames_count()

        stats = {
            'total': total,
            'processed': processed,
            'pending': total - processed,
            'total_frames': total_frames
        }
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/parse/start', methods=['POST'])
def start_parse_api():
    """开始解析视频"""
    global parse_status

    if parse_status['is_parsing']:
        return jsonify({
            'success': False,
            'error': '已有解析任务正在进行中'
        }), 400

    try:
        # 检查是否有待解析的视频
        videos = load_videos()
        pending = [v for v in videos if not v['processed']]

        if not pending:
            return jsonify({
                'success': False,
                'error': '没有待解析的视频'
            }), 400

        # 启动解析线程
        parse_status['is_parsing'] = True
        parse_status['progress'] = 0
        parse_status['logs'] = []

        thread = threading.Thread(target=run_parse_script)
        thread.daemon = True
        thread.start()

        add_log(f'开始解析 {len(pending)} 个视频...', 'info')

        return jsonify({
            'success': True,
            'message': f'开始解析 {len(pending)} 个视频'
        })
    except Exception as e:
        parse_status['is_parsing'] = False
        logger.error(f"启动解析失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/parse/status', methods=['GET'])
def get_parse_status_api():
    """获取解析状态"""
    return jsonify({
        'success': True,
        'data': {
            'is_parsing': parse_status['is_parsing'],
            'progress': parse_status['progress'],
            'logs': parse_status['logs']
        }
    })


@app.route('/api/parse/logs', methods=['GET'])
def get_parse_logs_api():
    """获取完整的解析日志文件内容"""
    try:
        if not LOG_FILE.exists():
            return jsonify({
                'success': True,
                'data': {
                    'logs': '日志文件不存在'
                }
            })

        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

        return jsonify({
            'success': True,
            'data': {
                'logs': content,
                'file_path': str(LOG_FILE)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/match', methods=['POST'])
def match_image_api():
    """服务端图片匹配接口 - CLIP + FAISS + SQLite + Re-ranking 版本"""
    import base64
    import io
    import numpy as np
    import multiprocessing as mp
    from PIL import Image

    try:
        data = request.json
        image_data = data.get('image', '')
        max_results = data.get('max_results', 5)
        min_similarity = data.get('min_similarity', 0.5)  # 默认最低相似度 0.5

        logger.info(f"收到匹配请求，图片数据长度: {len(image_data) if image_data else 0}")

        if not image_data:
            return jsonify({
                'success': False,
                'error': '请提供图片数据'
            }), 400

        # 检查数据库是否存在
        if not db_exists():
            logger.error("数据库不存在")
            return jsonify({
                'success': False,
                'error': '数据库不存在，请先解析视频或运行迁移脚本'
            }), 404

        # 加载 FAISS 向量索引（包含一致性校验）
        try:
            vector_store = load_or_create_store()
        except IndexNotInitialized as e:
            logger.error(f"索引加载失败: {e}")
            return jsonify({
                'success': False,
                'error': '索引与数据库不一致，需要重建索引。请删除 data/faiss_index.index 和 data/video_frames.db 后重新解析视频。',
                'requires_rebuild': True
            }), 500

        if vector_store.is_empty():
            logger.error("FAISS 索引为空")
            return jsonify({
                'success': False,
                'error': '向量索引为空，请先解析视频'
            }), 404

        # 解码 Base64 图片
        try:
            # 移除可能的数据 URL 前缀
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]

            image_bytes = base64.b64decode(image_data)
            logger.info(f"Base64 解码成功，图片大小: {len(image_bytes)} bytes")
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"图片解码失败: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'图片解码失败: {str(e)}'
            }), 400

        # 检查特征缓存
        query_feature = get_cached_feature(image_bytes)
        if query_feature is not None:
            logger.info("命中特征缓存")
        else:
            # 缓存未命中，调用 MobileNet 服务提取特征
            logger.info("调用 MobileNet 服务提取特征...")
            sys.stdout.flush()

            try:
                import requests

                # 调用 MobileNet 服务
                mobilenet_service_url = "http://127.0.0.1:9998/extract"
                response = requests.post(
                    mobilenet_service_url,
                    json={'image': image_data},
                    timeout=30
                )

                if response.status_code != 200:
                    logger.error(f"MobileNet 服务返回错误: {response.status_code}")
                    return jsonify({
                        'success': False,
                        'error': f'MobileNet 服务错误: HTTP {response.status_code}'
                    }), 500

                result = response.json()
                if not result.get('success'):
                    logger.error(f"MobileNet 服务提取失败: {result.get('error')}")
                    return jsonify({
                        'success': False,
                        'error': f"MobileNet 服务提取失败: {result.get('error')}"
                    }), 500

                # 提取特征向量
                query_feature = np.array(result['feature'], dtype=np.float32)

                # 归一化特征（用于余弦相似度）
                norm = np.linalg.norm(query_feature)
                if norm > 0:
                    query_feature = query_feature / norm

                # 存入缓存
                cache_feature(image_bytes, query_feature)

                logger.info(f"MobileNet 特征提取完成: {query_feature.shape}")
                sys.stdout.flush()

            except requests.exceptions.ConnectionError:
                logger.error("无法连接到 MobileNet 服务")
                return jsonify({
                    'success': False,
                    'error': 'MobileNet 服务未运行，请先启动: python mobilenet_service.py'
                }), 500
            except requests.exceptions.Timeout:
                logger.error("MobileNet 服务请求超时")
                return jsonify({
                    'success': False,
                    'error': 'MobileNet 服务请求超时'
                }), 500
            except Exception as e:
                logger.error(f"MobileNet 服务调用异常: {e}", exc_info=True)
                sys.stdout.flush()
                return jsonify({
                    'success': False,
                    'error': f'MobileNet 服务调用异常: {str(e)}'
                }), 500

        # ==================== Re-ranking 机制 ====================
        # 第一阶段：FAISS 粗选（获取更多候选结果）
        rerank_candidate_count = min(max(20, max_results * 4), vector_store.get_vector_count())
        distances, frame_ids = vector_store.search(
            query_feature,
            k=rerank_candidate_count,
            min_similarity=0.0  # 第一阶段不过滤
        )

        # SQLite 查询元数据
        candidates = []
        with get_db() as conn:
            for faiss_idx, distance in zip(frame_ids, distances):
                if faiss_idx < 0:  # FAISS 返回 -1 表示无效结果
                    continue

                # 判断返回的是索引位置还是 frame_id
                if isinstance(vector_store.index, faiss.IndexIDMap):
                    # IndexIDMap 直接返回 frame_id
                    db_frame_id = int(faiss_idx)
                else:
                    # 旧索引：需要转换（索引位置 + 1）
                    db_frame_id = int(faiss_idx) + 1

                # 查询帧信息
                frame = conn.execute(
                    """SELECT f.*, v.title, v.author, v.url, v.bvid as video_bvid
                       FROM frames f
                       JOIN videos v ON f.video_id = v.id
                       WHERE f.id = ?""",
                    (db_frame_id,)
                ).fetchone()

                if frame:
                    # 计算相似度
                    if vector_store.use_cosine:
                        # 余弦相似度：直接使用 distance（已经是余弦相似度）
                        similarity = vector_store.distance_to_similarity(float(distance))
                    else:
                        # L2 距离转换
                        similarity = vector_store.distance_to_similarity(float(distance))

                    # 处理图片路径
                    image_path = frame['image_path']
                    if image_path.startswith('data/video_frames/'):
                        relative_path = image_path.replace('data/video_frames/', '')
                        image_path = f"/frames/{relative_path}"

                    candidates.append({
                        'bvid': frame['video_bvid'],
                        'similarity': similarity,
                        'cosine_similarity': float(distance) if vector_store.use_cosine else None,
                        'frame': {
                            'seconds': frame['seconds'],
                            'image_path': image_path
                        },
                        'frame_id': db_frame_id
                    })
                else:
                    logger.warning(f"FAISS 结果 {faiss_idx} (DB ID {db_frame_id}) 在数据库中不存在")

        # 如果没有候选结果
        if not candidates:
            logger.error("所有匹配结果都查询失败，索引和数据库不同步")
            return jsonify({
                'success': False,
                'error': '索引和数据库不同步，请删除 data/faiss_index.index 和 data/video_frames.db 后重新解析视频',
                'requires_rebuild': True
            }), 500

        # 第二阶段：按相似度排序并应用阈值
        candidates.sort(key=lambda x: x['similarity'], reverse=True)

        # 应用相似度阈值过滤
        filtered_candidates = [c for c in candidates if c['similarity'] >= min_similarity]

        # 取前 N 个结果
        results = filtered_candidates[:max_results]

        logger.info(f"匹配完成: 粗选 {len(candidates)} 个 -> 过滤后 {len(filtered_candidates)} 个 -> 返回 {len(results)} 个")

        return jsonify({
            'success': True,
            'data': {
                'matches': results,
                'candidates_count': len(candidates),
                'filtered_count': len(filtered_candidates),
                'threshold': min_similarity
            }
        })

    except ImportError as e:
        logger.error(f"缺少必要的依赖: {e}")
        return jsonify({
            'success': False,
            'error': f'服务端缺少必要依赖: {str(e)}'
        }), 500
    except Exception as e:
        logger.error(f"图片匹配失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/system/check', methods=['GET'])
def check_system_api():
    """检查系统环境和依赖"""
    checks = {
        'python': False,
        'dependencies': {},
        'directories': {},
        'ffmpeg': False,
        'errors': []
    }

    # 检查 Python
    try:
        result = subprocess.run(
            [sys.executable, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        checks['python'] = result.returncode == 0
        checks['python_version'] = result.stdout.strip() if result.returncode == 0 else 'N/A'
        checks['python_path'] = sys.executable  # 记录实际使用的 Python 路径
    except:
        checks['errors'].append('Python 不可用')

    # 检查依赖
    dependencies = {
        'yt_dlp': 'yt-dlp',
        'cv2': 'opencv-python',
        'tensorflow': 'tensorflow',
        'numpy': 'numpy',
        'PIL': 'pillow'
    }

    for module, package in dependencies.items():
        try:
            result = subprocess.run(
                [sys.executable, '-c', f'import {module}'],
                capture_output=True,
                timeout=5
            )
            checks['dependencies'][package] = result.returncode == 0
            if result.returncode != 0:
                checks['errors'].append(f'缺少依赖: {package}')
        except:
            checks['dependencies'][package] = False
            checks['errors'].append(f'无法检查依赖: {package}')

    # 检查目录
    dirs_to_check = {
        'data': DATA_DIR,
        'downloads': PROJECT_ROOT / "downloads",
        'video_frames': DATA_DIR / "video_frames"
    }

    for name, path in dirs_to_check.items():
        exists = path.exists()
        checks['directories'][name] = {
            'exists': exists,
            'path': str(path),
            'writable': exists and os.access(path, os.W_OK)
        }

    # 检查 ffmpeg
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            timeout=5
        )
        checks['ffmpeg'] = result.returncode == 0
        if result.returncode != 0:
            checks['errors'].append('ffmpeg 未安装（视频处理需要）')
    except:
        checks['ffmpeg'] = False
        checks['errors'].append('ffmpeg 未安装（视频处理需要）')

    return jsonify({
        'success': True,
        'data': checks
    })


# ==================== 主函数 ====================
def main():
    print("=" * 60)
    print("🎮 帧探·GameLens - 后端 API 服务器")
    print("=" * 60)
    print()
    print("📡 API 服务地址:")
    print(f"   - API Base: http://localhost:8080/api")
    print()
    print("🌐 前端需要单独启动:")
    print(f"   - 开发模式: cd frontend && npm run dev")
    print(f"   - 生产模式: cd frontend && npm run build && npm run preview")
    print()
    print("📍 前端访问地址（开发模式）:")
    print(f"   - 主页: http://localhost:3000")
    print(f"   - 管理后台: http://localhost:3000/admin.html")
    print()
    print("按 Ctrl+C 停止 API 服务器")
    print("=" * 60)
    print()

    # 确保数据目录存在
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 启动服务器
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)


if __name__ == '__main__':
    main()
