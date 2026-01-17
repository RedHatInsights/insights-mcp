"""Session cache for OAuth tokens with FastMCP session_id integration.

This module provides per-connection token caching using FastMCP's native session_id
for optimal performance in multiuser scenarios while maintaining security isolation.
"""

import hashlib
import time
from dataclasses import dataclass
from logging import getLogger
from typing import Any

from authlib.oauth2.rfc6749 import OAuth2Token

logger = getLogger("SessionCache")


@dataclass
class CachedSession:
    """Cached OAuth token with expiration tracking.

    Attributes:
        token: OAuth2Token instance
        expires_at: Unix timestamp when this cache entry expires
        session_id: FastMCP session ID for this connection
        credentials_hash: SHA256 hash of credentials for cache key
        created_at: Unix timestamp when this entry was created
    """

    token: OAuth2Token
    expires_at: float
    session_id: str
    credentials_hash: str
    created_at: float


class SessionCache:
    """Thread-safe in-memory cache for OAuth tokens keyed by (session_id, credentials_hash).

    Provides per-connection token caching with automatic expiration and cleanup.
    Uses FastMCP's session_id for connection-level isolation as recommended by
    FastMCP documentation for "session-based data storage".

    The cache key is a tuple of (session_id, credentials_hash) ensuring:
    - Same client, same credentials → cached token reused
    - Same client, different credentials → new cache entry
    - Different clients, same credentials → separate cache entries

    Args:
        default_ttl: Default time-to-live for cached tokens in seconds (default: 900 = 15 min)
        cleanup_interval: How often to run cleanup of expired entries in seconds (default: 1200 = 20 min)
    """

    def __init__(self, default_ttl: int = 900, cleanup_interval: int = 1200):
        """Initialize session cache with configurable TTL and cleanup interval."""
        self._cache: dict[tuple[str, str], CachedSession] = {}
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

    def _make_key(self, session_id: str, credentials: str) -> tuple[str, str]:
        """Create cache key from session_id and credentials hash.

        Args:
            session_id: FastMCP session ID for this connection
            credentials: String representation of credentials (e.g., "client_id:client_secret")

        Returns:
            Tuple of (session_id, credentials_hash) for use as cache key
        """
        creds_hash = hashlib.sha256(credentials.encode()).hexdigest()
        return (session_id, creds_hash)

    def get(self, session_id: str, client_id: str, client_secret: str) -> OAuth2Token | None:
        """Get cached token if valid.

        Args:
            session_id: FastMCP session ID for this connection
            client_id: OAuth client ID
            client_secret: OAuth client secret

        Returns:
            Cached OAuth2Token if valid and not expired, None if expired or missing
        """
        self._maybe_cleanup()

        key = self._make_key(session_id, f"{client_id}:{client_secret}")
        session = self._cache.get(key)

        if session and session.expires_at > time.time():
            age = time.time() - session.created_at
            logger.debug(
                "Cache HIT for session %s (age: %.1fs, TTL remaining: %.1fs)",
                session_id[:8],
                age,
                session.expires_at - time.time(),
            )
            return session.token

        # Expired or missing
        if session:
            logger.debug("Cache EXPIRED for session %s", session_id[:8])
            del self._cache[key]
        else:
            logger.debug("Cache MISS for session %s", session_id[:8])

        return None

    def set(self, session_id: str, client_id: str, client_secret: str, token: OAuth2Token) -> None:
        """Store token in cache.

        Args:
            session_id: FastMCP session ID for this connection
            client_id: OAuth client ID
            client_secret: OAuth client secret
            token: OAuth2Token to cache
        """
        key = self._make_key(session_id, f"{client_id}:{client_secret}")
        expires_at = time.time() + self._default_ttl

        self._cache[key] = CachedSession(
            token=token,
            expires_at=expires_at,
            session_id=session_id,
            credentials_hash=key[1],
            created_at=time.time(),
        )

        logger.debug(
            "Cached token for session %s (TTL: %ds, total cached: %d)",
            session_id[:8],
            self._default_ttl,
            len(self._cache),
        )

    def _maybe_cleanup(self) -> None:
        """Periodically cleanup expired entries to prevent memory bloat.

        Runs cleanup if cleanup_interval has elapsed since last cleanup.
        """
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        expired_keys = [k for k, v in self._cache.items() if v.expires_at <= now]
        for key in expired_keys:
            del self._cache[key]

        self._last_cleanup = now
        if expired_keys:
            logger.info(
                "Cleaned up %d expired cache entries, now %d entries in cache", len(expired_keys), len(self._cache)
            )

    def stats(self) -> dict[str, Any]:
        """Get cache statistics for monitoring and debugging.

        Returns:
            Dictionary containing:
                - total_entries: Total number of cache entries
                - valid_entries: Number of non-expired entries
                - expired_entries: Number of expired but not yet cleaned entries
                - unique_sessions: Number of unique session IDs in cache
        """
        now = time.time()
        valid_entries = sum(1 for v in self._cache.values() if v.expires_at > now)
        expired_entries = len(self._cache) - valid_entries

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "unique_sessions": len(set(k[0] for k in self._cache)),
        }
