#!/usr/bin/env python3
"""
帧探·GameLens - 管理API服务器
提供视频管理和解析的API接口
"""

import os
import sys
import json
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ==================== 配置 ====================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VIDEO_LIST_FILE = DATA_DIR / "videos.txt"
INDEX_FILE = DATA_DIR / "video_index.json"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
BUILD_SCRIPT = SCRIPTS_DIR / "build_video_index.py"

# ==================== Flask应用 ====================
app = Flask(__name__, static_folder=str(PROJECT_ROOT), static_url_path='')
CORS(app)  # 允许跨域请求

# ==================== 全局状态 ====================
parsing_status = {
    'is_parsing': False,
    'progress': 0,
    'current_step': '',
    'logs': [],
    'error': None
}

# ==================== 工具函数 ====================
def get_bvid_from_url(url: str) -> str:
    """从B站URL中提取BV号"""
    if "BV" in url:
        return url[url.find("BV"):url.find("BV") + 12]
    return ""

def is_valid_bilibili_url(url: str) -> bool:
    """验证是否是有效的B站视频链接"""
    return 'bilibili.com/video/' in url and 'BV' in url

def load_videos() -> List[str]:
    """加载视频列表"""
    if not VIDEO_LIST_FILE.exists():
        return []
    
    with open(VIDEO_LIST_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

def save_videos(videos: List[str]):
    """保存视频列表"""
    VIDEO_LIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(VIDEO_LIST_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(videos))

def get_processed_bvids() -> set:
    """获取已处理的BV号"""
    if not INDEX_FILE.exists():
        return set()
    
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            index = json.load(f)
        return {v['bvid'] for v in index.get('videos', [])}
    except:
        return set()

def add_log(message: str, log_type: str = 'info'):
    """添加日志"""
    parsing_status['logs'].insert(0, {
        'time': datetime.now().strftime('%H:%M:%S'),
        'message': message,
        'type': log_type
    })
    # 只保留最近100条
    if len(parsing_status['logs']) > 100:
        parsing_status['logs'] = parsing_status['logs'][:100]

# ==================== API路由 ====================

@app.route('/')
def index():
    """主页重定向"""
    return send_from_directory(PROJECT_ROOT, 'index.html')

@app.route('/admin.html')
def admin():
    """管理后台页面"""
    return send_from_directory(PROJECT_ROOT, 'admin.html')

@app.route('/api/videos', methods=['GET'])
def get_videos_api():
    """获取视频列表"""
    try:
        videos = load_videos()
        processed_bvids = get_processed_bvids()
        
        result = []
        for url in videos:
            bvid = get_bvid_from_url(url)
            result.append({
                'url': url,
                'bvid': bvid,
                'processed': bvid in processed_bvids
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/videos', methods=['POST'])
def add_video_api():
    """添加视频"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({
                'success': False,
                'error': '视频链接不能为空'
            }), 400
        
        if not is_valid_bilibili_url(url):
            return jsonify({
                'success': False,
                'error': '无效的B站视频链接'
            }), 400
        
        videos = load_videos()
        bvid = get_bvid_from_url(url)
        
        # 检查是否已存在
        if any(get_bvid_from_url(v) == bvid for v in videos):
            return jsonify({
                'success': False,
                'error': f'视频 {bvid} 已存在'
            }), 400
        
        # 添加视频
        videos.insert(0, url)
        save_videos(videos)
        
        return jsonify({
            'success': True,
            'message': f'已添加视频: {bvid}',
            'data': {
                'url': url,
                'bvid': bvid,
                'processed': False
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/videos/bulk', methods=['POST'])
def add_videos_bulk_api():
    """批量添加视频"""
    try:
        data = request.get_json()
        urls_text = data.get('urls', '').strip()
        
        if not urls_text:
            return jsonify({
                'success': False,
                'error': '视频链接不能为空'
            }), 400
        
        urls = [line.strip() for line in urls_text.split('\n')]
        valid_urls = [u for u in urls if u and is_valid_bilibili_url(u)]
        
        if not valid_urls:
            return jsonify({
                'success': False,
                'error': '没有有效的视频链接'
            }), 400
        
        videos = load_videos()
        added_count = 0
        skipped_count = 0
        
        for url in valid_urls:
            bvid = get_bvid_from_url(url)
            if not any(get_bvid_from_url(v) == bvid for v in videos):
                videos.insert(0, url)
                added_count += 1
            else:
                skipped_count += 1
        
        save_videos(videos)
        
        return jsonify({
            'success': True,
            'message': f'批量添加完成: 新增 {added_count} 个，跳过 {skipped_count} 个',
            'data': {
                'added': added_count,
                'skipped': skipped_count
            }
        })
    except Exception as e:
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
                'error': '无效的索引'
            }), 400
        
        removed_video = videos.pop(index)
        save_videos(videos)
        
        return jsonify({
            'success': True,
            'message': '视频已删除',
            'data': {
                'url': removed_video,
                'bvid': get_bvid_from_url(removed_video)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/parse/start', methods=['POST'])
def start_parsing_api():
    """开始解析"""
    try:
        if parsing_status['is_parsing']:
            return jsonify({
                'success': False,
                'error': '解析正在进行中'
            }), 400
        
        # 重置状态
        parsing_status['is_parsing'] = True
        parsing_status['progress'] = 0
        parsing_status['current_step'] = '准备中...'
        parsing_status['logs'] = []
        parsing_status['error'] = None
        
        add_log('开始解析视频...', 'info')
        
        # 在后台线程中运行解析
        def parse_in_background():
            try:
                add_log('运行解析脚本...', 'info')
                parsing_status['current_step'] = '正在解析...'
                
                # 运行解析脚本
                result = subprocess.run(
                    [sys.executable, str(BUILD_SCRIPT)],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
                
                # 记录输出
                for line in result.stdout.split('\n'):
                    if line.strip():
                        add_log(line, 'info')
                
                if result.returncode == 0:
                    parsing_status['progress'] = 100
                    parsing_status['current_step'] = '解析完成'
                    add_log('✓ 解析完成！', 'success')
                else:
                    parsing_status['error'] = result.stderr
                    add_log(f'解析失败: {result.stderr}', 'error')
                    
            except Exception as e:
                parsing_status['error'] = str(e)
                add_log(f'解析出错: {str(e)}', 'error')
            finally:
                parsing_status['is_parsing'] = False
        
        thread = threading.Thread(target=parse_in_background, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': '解析已开始'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/parse/status', methods=['GET'])
def parse_status_api():
    """获取解析状态"""
    return jsonify({
        'success': True,
        'data': parsing_status
    })

@app.route('/api/stats', methods=['GET'])
def get_stats_api():
    """获取统计信息"""
    try:
        videos = load_videos()
        processed_bvids = get_processed_bvids()
        
        total = len(videos)
        processed = len(processed_bvids)
        pending = total - processed
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'processed': processed,
                'pending': pending
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 启动服务器 ====================
def main():
    print("=" * 60)
    print("帧探·GameLens - 管理API服务器")
    print("=" * 60)
    print()
    print("服务地址:")
    print("  - 主页: http://localhost:8000")
    print("  - 管理后台: http://localhost:8000/admin.html")
    print("  - API文档: http://localhost:8000/api/stats")
    print()
    print("功能:")
    print("  ✓ 静态文件托管")
    print("  ✓ 视频管理API")
    print("  ✓ 一键解析")
    print("  ✓ 实时进度查询")
    print()
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    print()
    
    # 启动Flask开发服务器
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=True
    )

if __name__ == '__main__':
    main()
