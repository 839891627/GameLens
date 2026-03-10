#!/usr/bin/env python3
"""
帧探·GameLens - 后端服务器
提供视频管理和自动解析功能
"""

import os
import json
import re
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
# 项目根目录（向上两级到 backend 目录）
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VIDEO_LIST_FILE = DATA_DIR / "videos.txt"
VIDEO_INDEX_FILE = DATA_DIR / "video_index.json"
BUILD_SCRIPT = PROJECT_ROOT / "gamelens" / "scripts" / "build_index.py"

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

        # 检查脚本是否存在
        if not BUILD_SCRIPT.exists():
            add_log(f'✗ 解析脚本不存在: {BUILD_SCRIPT}', 'error')
            logger.error(f"解析脚本不存在: {BUILD_SCRIPT}")
            return

        # 检查 Python 环境
        add_log('检查 Python 环境...', 'info')
        check_result = subprocess.run(
            ['python', '--version'],
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
                    ['python', '-c', f'import {dep.split(".")[0]}'],
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
            (PROJECT_ROOT / "backend" / "data" / "downloads").mkdir(parents=True, exist_ok=True)
            (PROJECT_ROOT / "backend" / "data" / "video_frames").mkdir(parents=True, exist_ok=True)
            add_log('✓ 目录创建完成', 'info')
        except Exception as e:
            add_log(f'✗ 创建目录失败: {e}', 'error')
            logger.error(f"创建目录失败: {e}")
            return

        # 运行解析脚本
        add_log(f'执行解析脚本: {BUILD_SCRIPT}', 'info')
        logger.info(f"工作目录: {PROJECT_ROOT}")

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
                    logger.warning(f"解析脚本错误: {line.strip()}")
                    # 只记录重要错误到前端
                    if 'Error' in line or 'error' in line or '失败' in line or '错误' in line:
                        add_log(f'错误: {line.strip()}', 'error')

        if result.returncode == 0:
            add_log('✓ 解析完成！', 'success')
        else:
            add_log(f'✗ 解析失败 (退出码: {result.returncode})', 'error')
            add_log('请检查服务器日志获取详细错误信息', 'error')

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
        # 优先从 video_index.json 加载
        if VIDEO_INDEX_FILE.exists():
            with open(VIDEO_INDEX_FILE, 'r', encoding='utf-8') as f:
                index = json.load(f)
                # 提取视频基本信息，移除详细的帧数据
                videos = []
                for video in index.get('videos', []):
                    videos.append({
                        'bvid': video.get('bvid'),
                        'url': video.get('url'),
                        'title': video.get('title', ''),
                        'author': video.get('author', ''),
                        'duration': video.get('duration', ''),
                        'processed': True,  # 在索引中的视频都是已解析的
                        'frame_count': len(video.get('frames', []))
                    })
                return jsonify({
                    'success': True,
                    'data': videos
                })

        # 如果索引文件不存在，返回简化列表
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
        if VIDEO_INDEX_FILE.exists():
            with open(VIDEO_INDEX_FILE, 'r', encoding='utf-8') as f:
                index = json.load(f)
                return jsonify({
                    'success': True,
                    'data': index.get('videos', [])
                })
        else:
            return jsonify({
                'success': False,
                'error': '视频索引不存在，请先解析视频'
            }), 404
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
    """获取统计信息（轻量级，不加载完整 JSON）"""
    try:
        # 从 videos.txt 获取总视频数
        total = 0
        if VIDEO_LIST_FILE.exists():
            with open(VIDEO_LIST_FILE, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                total = len(urls)

        # 从 video_index.json 获取已处理视频数（只读取文件开头，不加载完整内容）
        processed = 0
        if VIDEO_INDEX_FILE.exists():
            try:
                # 只读取前 2KB，足以获取 total_videos 字段
                with open(VIDEO_INDEX_FILE, 'r', encoding='utf-8') as f:
                    header = f.read(2048)
                    # 使用正则表达式提取 total_videos 的值
                    match = re.search(r'"total_videos":\s*(\d+)', header)
                    if match:
                        processed = int(match.group(1))
            except Exception as e:
                logger.warning(f"读取索引文件失败: {e}")

        stats = {
            'total': total,
            'processed': processed,
            'pending': total - processed
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
            ['python', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        checks['python'] = result.returncode == 0
        checks['python_version'] = result.stdout.strip() if result.returncode == 0 else 'N/A'
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
                ['python', '-c', f'import {module}'],
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
    print(f"   - 在项目根目录运行: ./start.sh")
    print(f"   - 或手动启动: cd frontend && python -m http.server 8000 --directory public")
    print()
    print("📍 前端访问地址:")
    print(f"   - 主页: http://localhost:8000")
    print(f"   - 管理后台: http://localhost:8000/admin.html")
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
