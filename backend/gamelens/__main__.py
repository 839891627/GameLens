#!/usr/bin/env python3.12
"""
帧探·GameLens - 命令行入口

使用:
    python -m gamelens           # 启动服务器
    python -m gamelens check     # 检查环境
    python -m gamelens install   # 安装依赖
"""

import sys
import argparse
from .cli import main as cli_main


def main():
    """命令行入口"""
    cli_main()


if __name__ == '__main__':
    main()
