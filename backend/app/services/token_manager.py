"""
Redis-backed Spotify token management with concurrency protection
"""

import json
import time
import logging
import asyncio
from typing import Dict, Any, Optional
import base64
import httpx
import redis.asyncio as redis
from contextlib import asynccontextmanager

from ..core.config import settings

logger = logging.getLogger(__name__)


class SpotifyTokenManager:
    """
    Redis-backed token manager with distributed locking and cache-aside pattern.
    Handles Spotify access token caching, refresh, and concurrency protection.
    """
    
    # Redis keys
    TOKEN_KEY = "spotify:access_token"
    LOCK_KEY = "spotify:token_lock"
    METRICS_KEY = "spotify:metrics"
    
    # Configuration
    REFRESH_THRESHOLD_SECONDS = 300  # 5 minutes before expiry
    LOCK_TIMEOUT_SECONDS = 30
    REDIS_TTL_BUFFER = 60  # Buffer for Redis TTL vs token expiry
    
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._connection_initialized = False
        
    async def _get_redis_client(self) -> redis.Redis:
        """Get or create Redis connection with proper error handling."""
        if not self._connection_initialized:
            try:
                self._redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    retry_on_timeout=True,
                    retry_on_error=[ConnectionError, TimeoutError],
                    health_check_interval=30
                )
                # Test connection
                await self._redis_client.ping()
                self._connection_initialized = True
                logger.info("Connected to Redis for token management")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                logger.warning("Token management will fall back to direct refresh")
                self._redis_client = None
                
        return self._redis_client
    
    async def get_valid_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        This is the main entry point for token access.
        """
        try:
            redis_client = await self._get_redis_client()
            if not redis_client:
                # Redis unavailable, direct refresh
                return await self._direct_token_refresh()
            
            # Try to get cached token
            token_data = await redis_client.hgetall(self.TOKEN_KEY)
            
            if token_data and self._is_token_still_valid(token_data):
                await self._update_metrics("cache_hit")
                logger.debug("Using cached access token")
                return token_data["access_token"]
            
            # Token missing or expired, need refresh
            await self._update_metrics("cache_miss")
            return await self._refresh_token_with_lock()
            
        except Exception as e:
            logger.error(f"Error in get_valid_token: {e}")
            # Fallback to direct refresh
            return await self._direct_token_refresh()
    
    def _is_token_still_valid(self, token_data: Dict[str, str]) -> bool:
        """Check if cached token is still valid (not expired and not close to expiry)."""
        if not token_data or not token_data.get("expires_at"):
            return False
            
        try:
            expires_at = float(token_data["expires_at"])
            time_until_expiry = expires_at - time.time()
            return time_until_expiry > self.REFRESH_THRESHOLD_SECONDS
        except (ValueError, TypeError):
            logger.warning("Invalid expires_at in cached token data")
            return False
    
    async def _refresh_token_with_lock(self) -> str:
        """Refresh token with distributed lock to prevent stampedes."""
        redis_client = await self._get_redis_client()
        if not redis_client:
            return await self._direct_token_refresh()
        
        async with self._acquire_refresh_lock():
            # Double-check: another process might have refreshed while we waited
            token_data = await redis_client.hgetall(self.TOKEN_KEY)
            if token_data and self._is_token_still_valid(token_data):
                logger.debug("Token was refreshed by another process")
                return token_data["access_token"]
            
            # Actually refresh the token
            logger.info("Refreshing Spotify access token with Redis cache")
            return await self._refresh_and_cache_token()
    
    @asynccontextmanager
    async def _acquire_refresh_lock(self):
        """Acquire distributed lock for token refresh operations."""
        redis_client = await self._get_redis_client()
        if not redis_client:
            # No locking possible, proceed directly
            yield
            return
        
        lock_acquired = False
        try:
            # Try to acquire lock
            lock_acquired = await redis_client.set(
                self.LOCK_KEY, 
                "locked", 
                nx=True,  # Only set if not exists
                ex=self.LOCK_TIMEOUT_SECONDS  # Auto-expire
            )
            
            if not lock_acquired:
                # Wait for lock to be released, then retry once
                logger.debug("Token refresh lock held by another process, waiting...")
                await asyncio.sleep(1)
                for _ in range(self.LOCK_TIMEOUT_SECONDS):
                    lock_acquired = await redis_client.set(
                        self.LOCK_KEY, "locked", nx=True, ex=self.LOCK_TIMEOUT_SECONDS
                    )
                    if lock_acquired:
                        break
                    await asyncio.sleep(1)
                
                if not lock_acquired:
                    logger.warning("Could not acquire refresh lock, proceeding without lock")
            
            await self._update_metrics("lock_acquired" if lock_acquired else "lock_failed")
            yield
            
        finally:
            if lock_acquired and redis_client:
                try:
                    await redis_client.delete(self.LOCK_KEY)
                except Exception as e:
                    logger.debug(f"Error releasing refresh lock: {e}")
    
    async def _refresh_and_cache_token(self) -> str:
        """Refresh token via Spotify API and cache the result."""
        try:
            # Refresh token via Spotify API
            token_response = await self._request_token_refresh()
            access_token = token_response["access_token"]
            expires_in = token_response.get("expires_in", 3600)
            
            # Calculate expiry time
            expires_at = time.time() + expires_in
            
            # Cache the token in Redis
            await self._cache_token_data(access_token, expires_at, token_response)
            
            await self._update_metrics("refresh_success")
            logger.info(f"Successfully refreshed and cached access token (expires at {time.ctime(expires_at)})")
            
            return access_token
            
        except Exception as e:
            await self._update_metrics("refresh_failure")
            logger.error(f"Failed to refresh and cache token: {e}")
            raise
    
    async def _cache_token_data(self, access_token: str, expires_at: float, token_response: Dict[str, Any]):
        """Store token data in Redis with appropriate TTL."""
        redis_client = await self._get_redis_client()
        if not redis_client:
            return
        
        try:
            token_data = {
                "access_token": access_token,
                "expires_at": str(expires_at),
                "scope": token_response.get("scope", ""),
                "cached_at": str(time.time())
            }
            
            # Store with TTL slightly less than actual expiry
            ttl_seconds = int(expires_at - time.time() - self.REDIS_TTL_BUFFER)
            if ttl_seconds > 0:
                await redis_client.hset(self.TOKEN_KEY, mapping=token_data)
                await redis_client.expire(self.TOKEN_KEY, ttl_seconds)
                logger.debug(f"Cached token with TTL of {ttl_seconds} seconds")
            else:
                logger.warning("Token expires too soon to cache effectively")
                
        except Exception as e:
            logger.error(f"Failed to cache token data: {e}")
    
    async def _request_token_refresh(self) -> Dict[str, Any]:
        """Make HTTP request to refresh the access token."""
        if not settings.spotify_service_refresh_token:
            raise ValueError("SPOTIFY_SERVICE_REFRESH_TOKEN not configured")
        
        async with httpx.AsyncClient() as client:
            # Prepare refresh request
            token_data = {
                "grant_type": "refresh_token",
                "refresh_token": settings.spotify_service_refresh_token,
            }
            
            # Basic auth header
            credentials = base64.b64encode(
                f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
            ).decode()
            
            headers = {
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            
            # Make request
            response = await client.post(
                settings.spotify_token_url, 
                data=token_data, 
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code != 200:
                error_msg = f"Token refresh failed: Status {response.status_code}, Body: {response.text}"
                logger.error(error_msg)
                
                if response.status_code == 400:
                    logger.error("❌ Bad request - likely invalid refresh token")
                    logger.error("💡 SOLUTION: Run 'python generate_refresh_token.py' to get a new refresh token")
                elif response.status_code == 401:
                    logger.error("❌ Unauthorized - check client credentials")
                
                raise Exception(error_msg)
            
            token_response = response.json()
            
            if not token_response.get("access_token"):
                raise Exception("No access token in refresh response")
            
            # Handle new refresh token if provided
            new_refresh_token = token_response.get("refresh_token")
            if new_refresh_token:
                logger.warning("🔄 Received new refresh token - update your SPOTIFY_SERVICE_REFRESH_TOKEN")
                logger.warning(f"New refresh token: {new_refresh_token}")
            
            return token_response
    
    async def _direct_token_refresh(self) -> str:
        """Direct token refresh without caching (fallback mode)."""
        logger.warning("Performing direct token refresh (Redis unavailable)")
        token_response = await self._request_token_refresh()
        return token_response["access_token"]
    
    async def force_refresh(self) -> str:
        """Force immediate token refresh, bypassing cache. Use for 401 error recovery."""
        logger.info("Force refreshing access token")
        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                # Clear cached token
                await redis_client.delete(self.TOKEN_KEY)
            
            async with self._acquire_refresh_lock():
                token = await self._refresh_and_cache_token()
                await self._update_metrics("force_refresh")
                return token
                
        except Exception as e:
            logger.error(f"Force refresh failed: {e}")
            return await self._direct_token_refresh()
    
    async def _update_metrics(self, metric_type: str):
        """Update token management metrics in Redis."""
        redis_client = await self._get_redis_client()
        if not redis_client:
            return
        
        try:
            timestamp = int(time.time())
            await redis_client.hincrby(self.METRICS_KEY, metric_type, 1)
            await redis_client.hset(self.METRICS_KEY, f"{metric_type}_last", timestamp)
            # Keep metrics for 24 hours
            await redis_client.expire(self.METRICS_KEY, 86400)
        except Exception as e:
            logger.debug(f"Failed to update metrics: {e}")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get token management metrics for monitoring."""
        redis_client = await self._get_redis_client()
        if not redis_client:
            return {"error": "Redis unavailable"}
        
        try:
            metrics_data = await redis_client.hgetall(self.METRICS_KEY)
            return {
                "cache_hits": int(metrics_data.get("cache_hit", 0)),
                "cache_misses": int(metrics_data.get("cache_miss", 0)),
                "refresh_successes": int(metrics_data.get("refresh_success", 0)),
                "refresh_failures": int(metrics_data.get("refresh_failure", 0)),
                "lock_acquisitions": int(metrics_data.get("lock_acquired", 0)),
                "lock_failures": int(metrics_data.get("lock_failed", 0)),
                "force_refreshes": int(metrics_data.get("force_refresh", 0)),
                "last_refresh": metrics_data.get("refresh_success_last"),
                "redis_connected": True
            }
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for token management system."""
        try:
            redis_client = await self._get_redis_client()
            redis_status = "connected" if redis_client else "unavailable"
            
            token_data = {}
            if redis_client:
                cached_token = await redis_client.hgetall(self.TOKEN_KEY)
                if cached_token:
                    expires_at = float(cached_token.get("expires_at", 0))
                    token_data = {
                        "cached": True,
                        "expires_at": time.ctime(expires_at),
                        "time_until_expiry": max(0, expires_at - time.time()),
                        "needs_refresh": expires_at - time.time() < self.REFRESH_THRESHOLD_SECONDS
                    }
                else:
                    token_data = {"cached": False}
            
            return {
                "status": "healthy",
                "redis_status": redis_status,
                "token_info": token_data,
                "configuration": {
                    "refresh_threshold": self.REFRESH_THRESHOLD_SECONDS,
                    "lock_timeout": self.LOCK_TIMEOUT_SECONDS
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global token manager instance
spotify_token_manager = SpotifyTokenManager()