"""
CAYE v3.0 — Redis Cache Manager
Handles all API response caching with TTL management.
Conservative fallback: always False on API failure.
"""

import json
import hashlib
from typing import Any, Optional
from loguru import logger

import redis as redis_client

from backend.config import get_settings

settings = get_settings()


class CacheManager:
    """
    Redis-backed cache manager for all API signal responses.
    Prevents excessive API calls and handles rate limiting.
    """

    def __init__(self):
        self._redis: Optional[redis_client.Redis] = None

    def _get_redis(self) -> Optional[redis_client.Redis]:
        """
        Returns Redis connection, creates if not exists.
        Returns None if Redis is unavailable.
        """
        if self._redis is None:
            try:
                self._redis = redis_client.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                self._redis.ping()
            except Exception as e:
                logger.warning(f"Redis unavailable: {e}")
                self._redis = None
        return self._redis

    def _make_key(self, namespace: str, params: str = "") -> str:
        """
        Creates a cache key from namespace and params.
        Format: cache:{namespace}:{hash_of_params}
        """
        if params:
            param_hash = hashlib.md5(
                params.encode()
            ).hexdigest()[:8]
            return f"cache:{namespace}:{param_hash}"
        return f"cache:{namespace}"

    def get(self, namespace: str, params: str = "") -> Optional[Any]:
        """
        Retrieves cached value.
        Returns None if cache miss or Redis unavailable.
        """
        r = self._get_redis()
        if not r:
            return None

        try:
            key = self._make_key(namespace, params)
            value = r.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def set(
        self,
        namespace: str,
        data: Any,
        ttl: int,
        params: str = ""
    ) -> bool:
        """
        Stores value in cache with TTL in seconds.
        Returns True if successful.
        """
        r = self._get_redis()
        if not r:
            return False

        try:
            key = self._make_key(namespace, params)
            r.setex(key, ttl, json.dumps(data, default=str))
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    def delete(self, namespace: str, params: str = "") -> bool:
        """
        Deletes a cache entry.
        """
        r = self._get_redis()
        if not r:
            return False

        try:
            key = self._make_key(namespace, params)
            r.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False

    def get_stale(
        self,
        namespace: str,
        params: str = ""
    ) -> Optional[Any]:
        """
        Retrieves cached value regardless of TTL expiry.
        Used as last-resort fallback when API is unavailable.
        Requires storing with stale key prefix.
        """
        r = self._get_redis()
        if not r:
            return None

        try:
            stale_key = f"stale:{self._make_key(namespace, params)}"
            value = r.get(stale_key)
            if value:
                logger.warning(f"Serving STALE cache: {stale_key}")
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Stale cache error: {e}")
            return None

    def set_with_stale(
        self,
        namespace: str,
        data: Any,
        ttl: int,
        params: str = ""
    ) -> bool:
        """
        Stores value in both regular cache and stale cache.
        Stale cache has much longer TTL (24 hours).
        """
        self.set(namespace, data, ttl, params)

        r = self._get_redis()
        if not r:
            return False

        try:
            key = self._make_key(namespace, params)
            stale_key = f"stale:{key}"
            r.setex(
                stale_key,
                86400,  # 24 hours stale TTL
                json.dumps(data, default=str)
            )
            return True
        except Exception as e:
            logger.warning(f"Stale cache set error: {e}")
            return False

    def is_available(self) -> bool:
        """
        Returns True if Redis is accessible.
        """
        r = self._get_redis()
        if not r:
            return False
        try:
            r.ping()
            return True
        except Exception:
            return False


# ─────────────────────────────────────────
# SINGLETON CACHE INSTANCE
# Import this everywhere
# ─────────────────────────────────────────
cache = CacheManager()