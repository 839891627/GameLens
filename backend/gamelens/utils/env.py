#!/usr/bin/env python3
"""
环境检查工具
"""

import sys
import subprocess
from pathlib import Path


def check_environment(verbose=True):
    """检查运行环境"""
    if verbose:
        print("🔍 检查运行环境...\n")

    issues = []

    # 检查 Python 版本
    python_version = sys.version_info
    if python_version < (3, 8):
        issues.append(f"❌ Python 版本过低: {python_version.major}.{python_version.minor} (需要 >= 3.8)")
        if verbose:
            print(f"❌ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        if verbose:
            print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")

    # 检查依赖
    dependencies = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
        'yt_dlp': 'yt-dlp',
        'cv2': 'OpenCV',
        'tensorflow': 'TensorFlow',
        'numpy': 'NumPy',
        'PIL': 'Pillow'
    }

    for module, name in dependencies.items():
        try:
            __import__(module)
            if verbose:
                print(f"✅ {name}")
        except ImportError:
            if verbose:
                print(f"❌ {name} 未安装")
            issues.append(f"缺少依赖: {name}")

    # 检查 ffmpeg
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            timeout=2
        )
        if result.returncode == 0:
            if verbose:
                print("✅ FFmpeg")
        else:
            if verbose:
                print("❌ FFmpeg 未正确安装")
            issues.append("FFmpeg 未正确安装")
    except:
        if verbose:
            print("❌ FFmpeg 未安装")
        issues.append("FFmpeg 未安装（视频处理需要）")

    # 检查目录
    if verbose:
        print("\n📁 检查目录...")

    project_root = Path(__file__).parent.parent.parent
    dirs_to_check = [
        project_root / 'data',
        project_root / 'downloads',
        project_root / 'data' / 'video_frames'
    ]

    for dir_path in dirs_to_check:
        if dir_path.exists():
            if verbose:
                print(f"✅ {dir_path.relative_to(project_root)}/")
        else:
            if verbose:
                print(f"⚠️  {dir_path.relative_to(project_root)}/ (不存在，将自动创建)")
            dir_path.mkdir(parents=True, exist_ok=True)

    if issues and verbose:
        print(f"\n❌ 发现 {len(issues)} 个问题:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n💡 解决方案:")
        print("   python -m gamelens install")
        print("   sudo apt install ffmpeg  # Ubuntu/Debian")
        return False
    elif verbose:
        print("\n✅ 环境检查通过！")

    return len(issues) == 0
