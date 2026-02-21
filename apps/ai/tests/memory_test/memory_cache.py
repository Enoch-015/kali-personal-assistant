"""
L1/L2 Memory Cache implementation using Redis.

L2 Cache (Warm): Persistent storage for tagged memories from Graphiti
L1 Cache (Hot): Session-specific working set with relevance scoring

Key Layout:
- L2: kali:l2:<hash> -> JSON memory payload
- L2 index: kali:l2:index:<domain> -> SET of hashes
- L1: kali:l1:<session_id> -> ZSET(hash -> relevance score)
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

import redis.asyncio as redis

from hashing import memory_hash, memory_hash_from_tags, build_canonical_key

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A cached memory entry."""
    hash_key: str
    canonical_key: str  # domain|entity|facet
    content: str
    description: str
    graphiti_id: Optional[str] = None
    score: float = 0.0
    timestamp: float = field(default_factory=time.time)
    tags: dict = field(default_factory=dict)
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, data: str) -> "MemoryEntry":
        return cls(**json.loads(data))


class MemoryCache:
    """Two-tier memory cache with L1 (hot) and L2 (warm) layers."""

    L2_PREFIX = "kali:l2:"
    L2_INDEX_PREFIX = "kali:l2:index:"
    L1_PREFIX = "kali:l1:"
    
    # Cache configuration
    L1_MAX_SIZE = 50  # Max entries in L1 per session
    L1_TTL = 3600  # 1 hour TTL for L1 entries
    L2_TTL = 86400 * 7  # 7 days TTL for L2 entries
    PROMOTION_THRESHOLD = 0.7  # Min relevance score to promote to L1
    DEMOTION_THRESHOLD = 0.3  # Below this, demote from L1

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self._redis_url = redis_url
        self._redis: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._redis is None:
            self._redis = redis.from_url(
                self._redis_url,
                decode_responses=True,
                max_connections=20,
            )
            logger.info("Connected to Redis for memory cache")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    # -------------------------------------------------------------------------
    # L2 Cache Operations (Warm Storage)
    # -------------------------------------------------------------------------

    async def l2_put(self, entry: MemoryEntry) -> bool:
        """
        Store or update a memory in L2 cache.
        Returns True if new entry, False if updated existing.
        """
        key = f"{self.L2_PREFIX}{entry.hash_key}"
        is_new = not await self._redis.exists(key)
        
        # Update timestamp on every put
        entry.timestamp = time.time()
        
        await self._redis.setex(key, self.L2_TTL, entry.to_json())
        
        # Update domain index
        for domain in entry.tags.get("domains", []):
            index_key = f"{self.L2_INDEX_PREFIX}{domain}"
            await self._redis.sadd(index_key, entry.hash_key)
        
        logger.debug(f"L2 {'inserted' if is_new else 'updated'}: {entry.hash_key}")
        return is_new

    async def l2_get(self, hash_key: str) -> Optional[MemoryEntry]:
        """Get a memory from L2 cache."""
        key = f"{self.L2_PREFIX}{hash_key}"
        data = await self._redis.get(key)
        if data:
            return MemoryEntry.from_json(data)
        return None

    async def l2_get_by_domain(self, domain: str) -> list[MemoryEntry]:
        """Get all memories for a domain from L2."""
        index_key = f"{self.L2_INDEX_PREFIX}{domain}"
        hash_keys = await self._redis.smembers(index_key)
        
        entries = []
        for hash_key in hash_keys:
            entry = await self.l2_get(hash_key)
            if entry:
                entries.append(entry)
        
        return entries

    async def l2_exists(self, hash_key: str) -> bool:
        """Check if hash exists in L2."""
        return await self._redis.exists(f"{self.L2_PREFIX}{hash_key}")

    async def l2_count(self) -> int:
        """Count total L2 entries."""
        keys = await self._redis.keys(f"{self.L2_PREFIX}*")
        # Exclude index keys
        return len([k for k in keys if ":index:" not in k])

    async def l2_bulk_load(self, entries: list[MemoryEntry]) -> int:
        """Bulk load entries into L2. Returns count of new entries."""
        new_count = 0
        for entry in entries:
            if await self.l2_put(entry):
                new_count += 1
        return new_count

    # -------------------------------------------------------------------------
    # L1 Cache Operations (Hot Working Set)
    # -------------------------------------------------------------------------

    async def l1_promote(
        self, session_id: str, hash_key: str, relevance: float
    ) -> bool:
        """
        Promote a memory from L2 to L1 (session working set).
        Only promotes if relevance exceeds threshold.
        Returns True if promoted.
        """
        if relevance < self.PROMOTION_THRESHOLD:
            logger.debug(f"Not promoting {hash_key}: relevance {relevance} < {self.PROMOTION_THRESHOLD}")
            return False
        
        # Check L2 exists
        if not await self.l2_exists(hash_key):
            logger.warning(f"Cannot promote {hash_key}: not in L2")
            return False
        
        l1_key = f"{self.L1_PREFIX}{session_id}"
        
        # Add to L1 sorted set with relevance as score
        await self._redis.zadd(l1_key, {hash_key: relevance})
        await self._redis.expire(l1_key, self.L1_TTL)
        
        # Trim L1 to max size (keep highest scoring)
        current_size = await self._redis.zcard(l1_key)
        if current_size > self.L1_MAX_SIZE:
            # Remove lowest scoring entries
            excess = current_size - self.L1_MAX_SIZE
            await self._redis.zpopmin(l1_key, excess)
        
        logger.debug(f"L1 promoted: {hash_key} with relevance {relevance}")
        return True

    async def l1_demote(self, session_id: str, hash_key: str) -> bool:
        """
        Remove a memory from L1 (demote back to L2-only).
        L2 entry remains unchanged.
        """
        l1_key = f"{self.L1_PREFIX}{session_id}"
        removed = await self._redis.zrem(l1_key, hash_key)
        if removed:
            logger.debug(f"L1 demoted: {hash_key}")
        return bool(removed)

    async def l1_get_all(self, session_id: str) -> list[tuple[str, float]]:
        """
        Get all L1 entries for a session.
        Returns list of (hash_key, relevance) tuples, highest first.
        """
        l1_key = f"{self.L1_PREFIX}{session_id}"
        return await self._redis.zrange(l1_key, 0, -1, withscores=True, desc=True)

    async def l1_get_entries(self, session_id: str) -> list[MemoryEntry]:
        """Get full MemoryEntry objects from L1, fetching content from L2."""
        l1_items = await self.l1_get_all(session_id)
        entries = []
        for hash_key, score in l1_items:
            entry = await self.l2_get(hash_key)
            if entry:
                entry.score = score  # Update with L1 relevance
                entries.append(entry)
        return entries

    async def l1_count(self, session_id: str) -> int:
        """Count L1 entries for session."""
        l1_key = f"{self.L1_PREFIX}{session_id}"
        return await self._redis.zcard(l1_key)

    async def l1_update_relevance(
        self, session_id: str, hash_key: str, new_relevance: float
    ) -> None:
        """Update relevance score for an L1 entry. May trigger demotion."""
        l1_key = f"{self.L1_PREFIX}{session_id}"
        
        if new_relevance < self.DEMOTION_THRESHOLD:
            await self.l1_demote(session_id, hash_key)
        else:
            await self._redis.zadd(l1_key, {hash_key: new_relevance})

    async def l1_clear(self, session_id: str) -> int:
        """Clear all L1 entries for a session. Returns count removed."""
        l1_key = f"{self.L1_PREFIX}{session_id}"
        count = await self._redis.zcard(l1_key)
        await self._redis.delete(l1_key)
        return count

    # -------------------------------------------------------------------------
    # Query Operations (L1 then L2 lookup)
    # -------------------------------------------------------------------------

    async def lookup(
        self,
        session_id: str,
        query_tags: dict,
        include_l2: bool = True,
    ) -> tuple[list[MemoryEntry], list[MemoryEntry]]:
        """
        Lookup memories matching query tags.
        
        Uses a relaxed matching strategy:
        1. First checks for exact hash matches (domain+entity+facet)
        2. Falls back to domain-based matches for broader coverage
        
        Returns: (l1_matches, l2_matches)
        - l1_matches: Entries found in L1 (already hot)
        - l2_matches: Entries found in L2 only (candidates for promotion)
        """
        # Generate all possible hashes from query tags (exact match)
        query_hashes = set(memory_hash_from_tags(query_tags))
        query_domains = set(query_tags.get("domains", []))
        query_entities = set(e.lower() for e in query_tags.get("entities", []))
        
        l1_matches = []
        l2_matches = []
        seen_hashes = set()
        
        # Check L1 first
        l1_items = await self.l1_get_all(session_id)
        l1_hash_set = {h for h, _ in l1_items}
        
        for hash_key, score in l1_items:
            entry = await self.l2_get(hash_key)
            if entry:
                # Check if entry matches query by domain/entity (relaxed match)
                entry_domains = set(entry.tags.get("domains", []))
                entry_entities = set(e.lower() for e in entry.tags.get("entities", []))
                
                if entry_domains & query_domains and entry_entities & query_entities:
                    entry.score = score
                    l1_matches.append(entry)
                    seen_hashes.add(hash_key)
        
        # Check L2 for matches by domain (broader lookup)
        if include_l2:
            for domain in query_domains:
                domain_entries = await self.l2_get_by_domain(domain)
                for entry in domain_entries:
                    if entry.hash_key in seen_hashes or entry.hash_key in l1_hash_set:
                        continue
                    
                    # Relaxed matching: accept any entry in the same domain
                    # This increases L2 hit rate and reduces Graphiti calls
                    entry_entities = set(e.lower() for e in entry.tags.get("entities", []))
                    
                    # Score by entity overlap (0.0 - 1.0)
                    if query_entities and entry_entities:
                        overlap = len(entry_entities & query_entities)
                        max_overlap = max(len(entry_entities), len(query_entities))
                        entry.score = 0.3 + (0.7 * overlap / max_overlap) if max_overlap > 0 else 0.3
                    else:
                        entry.score = 0.3  # Base score for domain match
                    
                    l2_matches.append(entry)
                    seen_hashes.add(entry.hash_key)
                    
                    # Limit L2 results to prevent too many low-relevance matches
                    if len(l2_matches) >= 10:
                        break
                
                if len(l2_matches) >= 10:
                    break
        
        # Sort L2 matches by score (entity overlap)
        l2_matches.sort(key=lambda x: x.score, reverse=True)
        
        return l1_matches, l2_matches

    # -------------------------------------------------------------------------
    # Stats & Diagnostics
    # -------------------------------------------------------------------------

    async def get_stats(self, session_id: str) -> dict:
        """Get cache statistics."""
        return {
            "l2_total": await self.l2_count(),
            "l1_session": await self.l1_count(session_id),
            "l1_max_size": self.L1_MAX_SIZE,
            "promotion_threshold": self.PROMOTION_THRESHOLD,
            "demotion_threshold": self.DEMOTION_THRESHOLD,
        }

    async def l1_clear_session(self, session_id: str) -> None:
        """Clear L1 cache for a specific session."""
        l1_key = f"{self.L1_PREFIX}{session_id}"
        await self._redis.delete(l1_key)
        logger.debug(f"Cleared L1 session cache: {session_id}")

    async def clear_all(self) -> None:
        """Clear all cache data (for testing)."""
        keys = await self._redis.keys("kali:*")
        if keys:
            await self._redis.delete(*keys)
        logger.info("Cleared all cache data")
