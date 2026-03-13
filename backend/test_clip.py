#!/usr/bin/env python3
"""测试 CLIP 模型加载"""

import sys
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_clip_import():
    """测试1: CLIP 导入"""
    print("=" * 60)
    print("测试1: 导入 CLIP 模块")
    print("=" * 60)
    try:
        import clip
        print("✓ CLIP 导入成功")
        return True
    except Exception as e:
        print(f"✗ CLIP 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_clip_load():
    """测试2: CLIP 模型加载"""
    print("\n" + "=" * 60)
    print("测试2: 加载 CLIP 模型")
    print("=" * 60)
    try:
        import clip
        import torch

        print("开始加载 CLIP 模型 (ViT-B/32)...")
        sys.stdout.flush()

        device = "cpu"
        model, preprocess = clip.load("ViT-B/32", device=device)

        print(f"✓ CLIP 模型加载成功")
        print(f"  模型类型: {type(model)}")
        print(f"  设备: {device}")
        print(f"  输入分辨率: {model.visual.input_resolution}")
        print(f"  输出维度: {model.visual.output_dim}")

        return True
    except Exception as e:
        print(f"✗ CLIP 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_clip_inference():
    """测试3: CLIP 推理"""
    print("\n" + "=" * 60)
    print("测试3: CLIP 图像编码测试")
    print("=" * 60)
    try:
        import clip
        import torch
        import numpy as np
        from PIL import Image
        from io import BytesIO
        import base64

        # 创建一个简单的测试图片
        print("创建测试图片...")
        test_image = Image.new('RGB', (224, 224), color='red')

        # 加载模型
        print("加载 CLIP 模型...")
        sys.stdout.flush()
        device = "cpu"
        model, preprocess = clip.load("ViT-B/32", device=device)
        print("✓ 模型加载完成")

        # 预处理
        print("预处理图片...")
        sys.stdout.flush()
        image_input = preprocess(test_image).unsqueeze(0).to(device)
        print("✓ 预处理完成")

        # 提取特征
        print("提取图片特征...")
        sys.stdout.flush()
        with torch.no_grad():
            feature = model.encode_image(image_input)
        print("✓ 特征提取完成")

        # 转换为 numpy
        feature_np = feature.cpu().numpy().flatten()
        print(f"✓ 特征向量: {feature_np.shape}, 类型: {feature_np.dtype}")

        return True
    except Exception as e:
        print(f"✗ CLIP 推理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "=" * 60)
    print("CLIP 模型诊断测试")
    print("=" * 60)

    results = []

    # 测试1: 导入
    results.append(("CLIP 导入", test_clip_import()))

    # 测试2: 加载
    results.append(("CLIP 模型加载", test_clip_load()))

    # 测试3: 推理
    results.append(("CLIP 推理", test_clip_inference()))

    # 汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有测试通过！CLIP 模块工作正常")
    else:
        print("✗ 部分测试失败，请检查上述错误信息")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
