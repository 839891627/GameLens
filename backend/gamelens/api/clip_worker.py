#!/usr/bin/env python3
"""
CLIP 特征提取工作进程
在单独的进程中运行，避免 FAISS 和 CLIP 的库冲突
"""

import sys
import io
import base64
import multiprocessing as mp

# 在工作进程中导入 CLIP 相关模块
import torch
import clip
from PIL import Image
import numpy as np


def extract_feature_from_image(image_bytes):
    """
    从图片字节中提取 CLIP 特征

    Args:
        image_bytes: 图片字节数据

    Returns:
        特征向量 (numpy array)
    """
    try:
        # 加载 CLIP 模型
        device = "cpu"
        model, preprocess = clip.load("ViT-B/32", device=device)

        # 从字节加载图片
        image = Image.open(io.BytesIO(image_bytes))

        # 预处理
        image_input = preprocess(image).unsqueeze(0).to(device)

        # 提取特征
        with torch.no_grad():
            feature = model.encode_image(image_input)

        # 转换为 numpy
        feature_np = feature.cpu().numpy().flatten()

        return feature_np

    except Exception as e:
        raise Exception(f"CLIP 特征提取失败: {str(e)}")


def worker_extract_feature(image_bytes, result_queue):
    """
    工作进程函数：提取特征并放入结果队列

    Args:
        image_bytes: 图片字节数据
        result_queue: 结果队列
    """
    try:
        import sys
        import traceback

        feature = extract_feature_from_image(image_bytes)
        result_queue.put(('success', feature))
    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        result_queue.put(('error', error_msg))


if __name__ == '__main__':
    # 用于测试
    if len(sys.argv) > 1:
        # 测试模式
        print("CLIP Worker 测试模式")
        test_image = Image.new('RGB', (224, 224), color='blue')
        from io import BytesIO
        buffer = BytesIO()
        test_image.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()

        feature = extract_feature_from_image(image_bytes)
        print(f"✓ 特征提取成功: {feature.shape}")
    else:
        print("CLIP Worker 进程已启动")
