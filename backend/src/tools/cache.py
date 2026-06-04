"""简单 TTL 缓存 — 减少重复高德 API 调用。

面试可讲：因为旅游规划中同城市天气/POI 在短时间内不会变化，
用 TTL 缓存避免重复 API 调用，既省钱又加速。
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TTLCache:
    """内存 TTL 缓存，适合单进程部署。"""

    def __init__(self, ttl: int = 3600) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl
        self._lock = asyncio.Lock()

    def _key(self, *args: Any, **kwargs: Any) -> str:
        raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(raw.encode()).hexdigest()

    async def get_or_set(self, key_args: tuple, key_kwargs: dict, factory):
        """获取缓存，未命中则调用 factory 并缓存结果。"""
        cache_key = self._key(*key_args, **key_kwargs)

        async with self._lock:
            if cache_key in self._store:
                ts, value = self._store[cache_key]
                if time.time() - ts < self._ttl:
                    logger.debug("Cache HIT: %s", cache_key[:8])
                    return value
                del self._store[cache_key]

        # 缓存未命中，调用 factory
        result = await factory(*key_args, **key_kwargs)
        async with self._lock:
            self._store[cache_key] = (time.time(), result)
            # 简单 LRU：超过 500 条清理最早的一半
            if len(self._store) > 500:
                sorted_items = sorted(self._store.items(), key=lambda x: x[1][0])
                for k, _ in sorted_items[:250]:
                    del self._store[k]
        return result

    def clear(self) -> None:
        self._store.clear()


# 全局单例
weather_cache = TTLCache(ttl=1800)   # 天气缓存 30 分钟
poi_cache = TTLCache(ttl=3600)       # POI 缓存 1 小时
