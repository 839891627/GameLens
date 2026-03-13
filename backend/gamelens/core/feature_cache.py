#!/usr/bin/env python3
"""
帧探·GameLens - 特征缓存模块

使用 LRU 缓存缓存已提取的特征，避免重复计算
"""

import hashlib
import base64
import logging
from functools import lru_cache
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class FeatureCache:
    """特征缓存器 - 基于图片内容的 LRU 缓存"""

    def __init__(self, maxsize: int = 1000):
        """初始化特征缓存

        Args:
            maxsize: 最大缓存数量
        """
        self.maxsize = maxsize
        self._cache = {}
        self._access_order = []

    def _compute_hash(self, image_bytes: bytes) -> str:
        """计算图片内容的哈希值"""
        return hashlib.sha256(image_bytes).hexdigest()

    def get(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """从缓存获取特征

        Args:
            image_bytes: 图片字节数据

        Returns:
            特征向量，如果不存在则返回 None
        """
        cache_key = self._compute_hash(image_bytes)

        if cache_key in self._cache:
            # 更新访问顺序
            self._access_order.remove(cache_key)
            self._access_order.append(cache_key)
            logger.debug(f"缓存命中: {cache_key[:16]}...")
            return self._cache[cache_key].copy()

        return None

    def put(self, image_bytes: bytes, feature: np.ndarray):
        """将特征存入缓存

        Args:
            image_bytes: 图片字节数据
            feature: 特征向量
        """
        cache_key = self._compute_hash(image_bytes)

        # 如果缓存已满，删除最久未使用的项
        if len(self._cache) >= self.maxsize and cache_key not in self._cache:
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]
            logger.debug(f"缓存已满，删除: {oldest_key[:16]}...")

        self._cache[cache_key] = feature.copy()
        self._access_order.append(cache_key)
        logger.debug(f"缓存添加: {cache_key[:16]}...")

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._access_order.clear()
        logger.info("特征缓存已清空")

    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            'size': len(self._cache),
            'max_size': self.maxsize,
            'hit_ratio': getattr(self, '_hits', 0) / max(1, getattr(self, '_requests', 0))
        }


# 全局缓存实例
_global_cache: Optional[FeatureCache] = None


def get_feature_cache(maxsize: int = 1000) -> FeatureCache:
    """获取全局特征缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = FeatureCache(maxsize)
    return _global_cache


def compute_image_hash(image_bytes: bytes) -> str:
    """计算图片哈希值（用于缓存键）"""
    return hashlib.sha256(image_bytes).hexdigest()


def get_cached_feature(image_bytes: bytes) -> Optional[np.ndarray]:
    """从全局缓存获取特征"""
    cache = get_feature_cache()
    return cache.get(image_bytes)


def cache_feature(image_bytes: bytes, feature: np.ndarray):
    """将特征存入全局缓存"""
    cache = get_feature_cache()
    cache.put(image_bytes, feature)


def clear_feature_cache():
    """清空全局特征缓存"""
    global _global_cache
    if _global_cache:
        _global_cache.clear()


# 装饰器：带缓存的特征提取函数
def with_feature_cache(extract_func):
    """装饰器：为特征提取函数添加缓存支持

    Args:
        extract_func: 特征提取函数，签名为 extract_func(image_data: bytes) -> np.ndarray

    Returns:
        带缓存的特征提取函数
    """
    def wrapper(image_data: bytes) -> np.ndarray:
        # 尝试从缓存获取
        cached = get_cached_feature(image_data)
        if cached is not None:
            return cached

        # 缓存未命中，执行特征提取
        feature = extract_func(image_data)

        # 存入缓存
        cache_feature(image_data, feature)

        return feature

    return wrapper