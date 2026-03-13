#!/usr/bin/env python3.12
"""
帧探·GameLens - 环境检查脚本

快速验证开发环境是否准备就绪

使用方法:
    python scripts/check_env.py
"""

import sys
from pathlib import Path


def check_python_version():
    """检查Python版本"""
    print("检查Python版本...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"  ✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  ✗ Python版本过低: {version.major}.{version.minor}.{version.micro}")
        print(f"  需要Python 3.8或更高版本")
        return False


def check_dependencies():
    """检查Python依赖"""
    print("\n检查Python依赖...")

    required = {
        'cv2': 'opencv-python',
        'tensorflow': 'tensorflow',
        'yt_dlp': 'yt-dlp',
        'numpy': 'numpy',
        'PIL': 'pillow',
        'tqdm': 'tqdm',
        'dotenv': 'python-dotenv'
    }

    missing = []

    for module, package in required.items():
        try:
            __import__(module)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - 未安装")
            missing.append(package)

    if missing:
        print(f"\n缺少依赖: {', '.join(missing)}")
        print(f"请运行: pip install -r scripts/requirements.txt")
        return False

    return True


def check_directories():
    """检查目录结构"""
    print("\n检查目录结构...")

    project_root = Path(__file__).parent.parent
    required_dirs = [
        'data',
        'data/video_frames',
        'scripts',
        'js',
        'css',
        'docs'
    ]

    all_exist = True
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            print(f"  ✓ {dir_path}/")
        else:
            print(f"  ✗ {dir_path}/ - 不存在")
            all_exist = False

    return all_exist


def check_video_list():
    """检查视频列表"""
    print("\n检查视频列表...")

    video_list = Path(__file__).parent.parent / "data" / "videos.txt"
    example_list = Path(__file__).parent.parent / "data" / "videos.txt.example"

    if video_list.exists():
        with open(video_list, 'r') as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]

        if lines:
            print(f"  ✓ videos.txt 存在，包含 {len(lines)} 个视频链接")
            return True
        else:
            print(f"  ⚠ videos.txt 存在但为空")
            print(f"  请编辑 data/videos.txt 添加B站视频链接")
            return False
    else:
        print(f"  ⚠ videos.txt 不存在")
        print(f"  请复制 videos.txt.example 并添加视频链接")
        if example_list.exists():
            print(f"\n  运行以下命令创建:")
            print(f"  cp data/videos.txt.example data/videos.txt")
        return False


def check_ffmpeg():
    """检查FFmpeg（可选）"""
    print("\n检查FFmpeg（可选）...")

    import shutil
    if shutil.which('ffmpeg') is not None:
        print(f"  ✓ FFmpeg 已安装")
        return True
    else:
        print(f"  ⚠ FFmpeg 未安装（非必需，但建议安装）")
        print(f"  安装方法: brew install ffmpeg (macOS)")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("帧探·GameLens - 环境检查")
    print("=" * 60)

    results = {
        'Python版本': check_python_version(),
        'Python依赖': check_dependencies(),
        '目录结构': check_directories(),
        '视频列表': check_video_list(),
        'FFmpeg': check_ffmpeg()
    }

    print("\n" + "=" * 60)
    print("检查结果汇总")
    print("=" * 60)

    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 未通过"
        print(f"{name}: {status}")

    # 核心项检查
    critical = ['Python版本', 'Python依赖', '目录结构']
    all_critical_passed = all(results[k] for k in critical)

    print("\n" + "=" * 60)

    if all_critical_passed:
        if results['视频列表']:
            print("✓ 环境准备完成！")
            print("\n下一步:")
            print("  1. 确保 data/videos.txt 包含视频链接")
            print("  2. 运行: python scripts/build_video_index.py")
        else:
            print("⚠ 环境基本就绪，但需要添加视频链接")
            print("\n请编辑 data/videos.txt 添加B站视频链接")
    else:
        print("✗ 环境未就绪，请完成上述检查项")
        print("\n安装依赖:")
        print("  pip install -r scripts/requirements.txt")

    print("=" * 60)

    return 0 if all_critical_passed else 1


if __name__ == "__main__":
    sys.exit(main())
