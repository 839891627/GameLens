#!/usr/bin/env python3.12
"""
帧探·GameLens - 命令行工具

使用:
    python -m gamelens           # 启动服务器
    python -m gamelens check     # 检查环境
    python -m gamelens install   # 安装依赖
"""

import sys
import subprocess
import argparse
from pathlib import Path

from . import __version__, __description__
from .utils.env import check_environment
from .api.server import app


def print_banner():
    """打印欢迎横幅"""
    print("=" * 60)
    print("🎮 帧探·GameLens - 手游攻略智能匹配工具")
    print(f"版本: {__version__}")
    print("=" * 60)
    print()


def cmd_install(args):
    """安装依赖"""
    print("📦 安装依赖...\n")

    requirements_files = [
        Path(__file__).parent.parent / "scripts" / "requirements.txt",
    ]

    for req_file in requirements_files:
        if req_file.exists():
            print(f"从 {req_file} 安装...")
            subprocess.run([
                sys.executable, '-m', 'pip', 'install',
                '-r', str(req_file)
            ])

    print("\n✅ 依赖安装完成！")


def cmd_check(args):
    """检查环境"""
    print_banner()
    success = check_environment(verbose=True)
    sys.exit(0 if success else 1)


def cmd_start(args):
    """启动服务器"""
    print_banner()

    # 检查环境
    if not check_environment(verbose=False):
        print("\n⚠️  环境检查未通过，但仍将尝试启动服务器")

    print("\n📍 服务地址:")
    print(f"   - API 服务器: http://localhost:{args.port}/api")
    print()
    print("🌐 前端需要单独启动:")
    print(f"   - 开发模式: cd frontend && npm run dev")
    print(f"   - 生产模式: cd frontend && npm run build && npm run preview")
    print()
    print("按 Ctrl+C 停止服务器\n")
    print("=" * 60)
    print()

    # 启动服务器
    app.run(host='0.0.0.0', port=args.port, debug=False, threaded=True)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        prog='gamelens',
        description=__description__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python -m gamelens              启动服务器（默认端口8080）
    python -m gamelens --port 9000  启动服务器（端口9000）
    python -m gamelens check        检查运行环境
    python -m gamelens install      安装依赖
        """
    )

    parser.add_argument(
        '--version', '-v',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # start 子命令
    parser_start = subparsers.add_parser('start', help='启动服务器')
    parser_start.add_argument(
        '--port', '-p',
        type=int,
        default=8080,
        help='服务器端口（默认: 8080）'
    )

    # check 子命令
    subparsers.add_parser('check', help='检查运行环境')

    # install 子命令
    subparsers.add_parser('install', help='安装依赖')

    args = parser.parse_args()

    # 如果没有指定命令，默认启动服务器
    if args.command is None:
        args.command = 'start'
        args.port = 8080

    # 执行对应命令
    if args.command == 'start':
        cmd_start(args)
    elif args.command == 'check':
        cmd_check(args)
    elif args.command == 'install':
        cmd_install(args)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
        sys.exit(0)
