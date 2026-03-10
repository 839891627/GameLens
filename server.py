#!/usr/bin/env python3
"""
帧探·GameLens - 后端服务器
提供视频管理和自动解析功能
"""

import os
import json
import threading
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 配置 ====================
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
VIDEO_LIST_FILE = DATA_DIR / "videos.txt"
VIDEO_INDEX_FILE = DATA_DIR / "video_index.json"
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build_video_index.py"

# ==================== Flask 应用 ====================
app = Flask(__name__, static_folder='.', static_url_path='')
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

    # 加载已处理的视频
    processed_bvids = set()
    if VIDEO_INDEX_FILE.exists():
        try:
            with open(VIDEO_INDEX_FILE, 'r', encoding='utf-8') as f:
                index = json.load(f)
                processed_bvids = {v['bvid'] for v in index.get('videos', [])}
        except Exception as e:
            logger.warning(f"读取索引文件失败: {e}")

    # 构建视频列表
    videos = []
    for url in urls:
        bvid = extract_bvid(url)
        videos.append({
            'url': url,
            'bvid': bvid,
            'processed': bvid in processed_bvids,
            'title': get_video_title(bvid, VIDEO_INDEX_FILE)
        })

    return videos


def extract_bvid(url: str) -> str:
    """从URL提取BV号"""
    if 'BV' in url:
        start = url.find('BV')
        return url[start:start + 12]
    return ''


def get_video_title(bvid: str, index_file: Path) -> str:
    """从索引文件获取视频标题"""
    if not index_file.exists():
        return ''

    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)

        for video in index.get('videos', []):
            if video['bvid'] == bvid:
                return video.get('title', '')
    except:
        pass

    return ''


def save_videos(videos: List[Dict[str, Any]]):
    """保存视频列表到文件"""
    urls = [v['url'] for v in videos]
    with open(VIDEO_LIST_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(urls))


def add_log(message: str, log_type: str = 'info'):
    """添加解析日志"""
    parse_status['logs'].append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'message': message,
        'type': log_type
    })
    # 只保留最近100条
    if len(parse_status['logs']) > 100:
        parse_status['logs'] = parse_status['logs'][-100:]


# ==================== 解析线程 ====================
def run_parse_script():
    """在后台线程运行解析脚本"""
    try:
        add_log('开始下载视频...', 'info')

        # 运行解析脚本
        result = subprocess.run(
            ['python', str(BUILD_SCRIPT)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=3600  # 1小时超时
        )

        # 记录输出
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip():
                    add_log(line.strip(), 'info')

        if result.stderr:
            for line in result.stderr.split('\n'):
                if line.strip():
                    logger.warning(f"解析脚本: {line.strip()}")

        if result.returncode == 0:
            add_log('✓ 解析完成！', 'success')
        else:
            add_log(f'✗ 解析失败 (退出码: {result.returncode})', 'error')

    except subprocess.TimeoutExpired:
        add_log('✗ 解析超时（超过1小时）', 'error')
    except Exception as e:
        add_log(f'✗ 解析出错: {str(e)}', 'error')
        logger.error(f"解析出错: {e}", exc_info=True)
    finally:
        parse_status['is_parsing'] = False
        parse_status['progress'] = 100


# ==================== API 路由 ====================

@app.route('/')
def index():
    """主页"""
    return send_from_directory('.', 'index.html')


@app.route('/admin.html')
def admin():
    """管理后台"""
    return send_from_directory('.', 'admin.html')


@app.route('/api/videos', methods=['GET'])
def get_videos_api():
    """获取视频列表"""
    try:
        videos = load_videos()
        return jsonify({
            'success': True,
            'data': videos
        })
    except Exception as e:
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
    """获取统计信息"""
    try:
        videos = load_videos()
        stats = {
            'total': len(videos),
            'processed': sum(1 for v in videos if v['processed']),
            'pending': sum(1 for v in videos if not v['processed'])
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


# ==================== 主函数 ====================
def main():
    print("=" * 60)
    print("帧探·GameLens - 后端服务器")
    print("=" * 60)
    print()
    print("服务地址:")
    print(f"  - 主页: http://localhost:5000")
    print(f"  - 管理后台: http://localhost:5000/admin.html")
    print()
    print("功能:")
    print("  - 自动视频解析")
    print("  - 视频管理 API")
    print("  - 实时解析状态")
    print()
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    print()

    # 确保数据目录存在
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 启动服务器
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)


if __name__ == '__main__':
    main()
