#!/usr/bin/env python3
"""
ResNet50 特征提取工作进程
使用 torchvision 的 ResNet50，避免 CLIP 库冲突
"""

import sys
import io
import multiprocessing as mp

# 在工作进程中导入相关模块
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import numpy as np


class ResNetExtractor:
    """ResNet50 特征提取器"""

    def __init__(self):
        self.device = "cpu"
        self.model = None
        self.preprocess = None

    def load_model(self):
        """加载 ResNet50 模型"""
        if self.model is None:
            # 加载预训练的 ResNet50
            self.model = models.resnet50(pretrained=True)
            # 移除最后的分类层，只保留特征提取部分
            self.model = torch.nn.Sequential(*list(self.model.children())[:-1])
            self.model.eval()
            self.model.to(self.device)

            # 标准的 ImageNet 预处理
            self.preprocess = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])

    def extract_feature(self, image_bytes):
        """
        从图片字节中提取 ResNet50 特征

        Args:
            image_bytes: 图片字节数据

        Returns:
            特征向量 (numpy array)
        """
        if self.model is None:
            self.load_model()

        # 从字节加载图片
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # 预处理
        image_input = self.preprocess(image).unsqueeze(0).to(self.device)

        # 提取特征
        with torch.no_grad():
            feature = self.model(image_input)

        # 转换为 numpy 并展平
        feature_np = feature.cpu().numpy().flatten()

        return feature_np


# 全局提取器
_extractor = None


def get_extractor():
    """获取全局提取器实例"""
    global _extractor
    if _extractor is None:
        _extractor = ResNetExtractor()
    return _extractor


def extract_feature_from_image(image_bytes):
    """从图片字节中提取特征"""
    extractor = get_extractor()
    return extractor.extract_feature(image_bytes)


def worker_extract_feature(image_bytes, result_queue):
    """
    工作进程函数：提取特征并放入结果队列

    Args:
        image_bytes: 图片字节数据
        result_queue: 结果队列
    """
    try:
        import traceback
        feature = extract_feature_from_image(image_bytes)
        result_queue.put(('success', feature))
    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        result_queue.put(('error', error_msg))


if __name__ == '__main__':
    # 用于测试
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        print("ResNet Worker 测试模式")
        test_image = Image.new('RGB', (224, 224), color='blue')
        from io import BytesIO
        buffer = BytesIO()
        test_image.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()

        feature = extract_feature_from_image(image_bytes)
        print(f"✓ 特征提取成功: {feature.shape}")
        print(f"  特征维度: {len(feature)}")
    else:
        print("ResNet Worker 进程已启动")
