"""
Gemini-based intent tagging for queries and memory results.
Uses the Gemini API to classify domain, entity, and facet.

OPTIMIZATION: Redis-backed tag cache to avoid redundant API calls.
"""

import json
import logging
import hashlib
from typing import Any, Optional

import google.generativeai as genai
import redis.asyncio as redis

from domains import DOMAINS, ALL_FACETS

logger = logging.getLogger(__name__)

# Tag cache TTL: 24 hours (queries and content don't change often)
TAG_CACHE_TTL = 86400


class GeminiTagger:
    """Tags queries and memory content with domain/entity/facet labels.
    
    OPTIMIZATION: Uses Redis to cache tag results for 24 hours.
    This eliminates redundant Gemini API calls for repeated queries.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        redis_url: str = "redis://localhost:6379/0",
    ):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self._domains_str = ", ".join(DOMAINS)
        self._facets_str = ", ".join(ALL_FACETS[:30])  # truncate for prompt size
        self._redis: Optional[redis.Redis] = None
        self._redis_url = redis_url
        
        # Stats for monitoring
        self.cache_hits = 0
        self.cache_misses = 0

    async def _get_redis(self) -> redis.Redis:
        """Lazy Redis connection."""
        if self._redis is None:
            self._redis = await redis.from_url(self._redis_url)
        return self._redis

    def _cache_key(self, text: str, prefix: str = "tag") -> str:
        """Generate a short cache key from text."""
        text_hash = hashlib.md5(text.lower().strip().encode()).hexdigest()[:16]
        return f"gemini:{prefix}:{text_hash}"

    async def _get_cached_tags(self, key: str) -> Optional[dict]:
        """Try to get cached tags from Redis."""
        try:
            r = await self._get_redis()
            data = await r.get(key)
            if data:
                self.cache_hits += 1
                return json.loads(data)
        except Exception as e:
            logger.debug(f"Tag cache read failed: {e}")
        return None

    async def _set_cached_tags(self, key: str, tags: dict) -> None:
        """Cache tags in Redis."""
        try:
            r = await self._get_redis()
            await r.set(key, json.dumps(tags), ex=TAG_CACHE_TTL)
        except Exception as e:
            logger.debug(f"Tag cache write failed: {e}")

    async def tag_query(self, query: str) -> dict[str, Any]:
        """
        Tag a user query with domains, entities, and facets.
        
        OPTIMIZATION: Checks Redis cache first to avoid redundant API calls.
        
        Returns:
            {
                "domains": ["health", "emotion"],
                "entities": ["weight", "tracking"],
                "facets": ["current", "past"]
            }
        """
        # Check cache first
        cache_key = self._cache_key(query, "query")
        cached = await self._get_cached_tags(cache_key)
        if cached:
            logger.debug(f"Tag cache HIT for query: {query[:50]}...")
            return cached
        
        self.cache_misses += 1
        
        prompt = f"""You are a memory classification system. Analyze the user query and extract:
1. domains: Which life areas this relates to (pick 1-3 from: {self._domains_str})
2. entities: What specific things are mentioned (e.g., weight, flight, meeting, car)
3. facets: What contextual modifiers apply (e.g., current, past, future, recurring, deadline, stress)

User query: "{query}"

Respond ONLY with valid JSON in this exact format:
{{"domains": ["domain1"], "entities": ["entity1", "entity2"], "facets": ["facet1"]}}

Be concise. Pick the most relevant 1-3 items for each field."""

        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(text)
            
            # Normalize to lowercase
            result["domains"] = [d.lower() for d in result.get("domains", [])]
            result["entities"] = [e.lower().replace(" ", "_") for e in result.get("entities", [])]
            result["facets"] = [f.lower().replace(" ", "_") for f in result.get("facets", [])]
            
            # Cache the result
            await self._set_cached_tags(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.warning(f"Gemini tagging failed: {e}")
            return {"domains": [], "entities": [], "facets": []}

    async def tag_memory_result(self, content: str, description: str = "") -> dict[str, Any]:
        """
        Tag a memory/fact retrieved from Graphiti.
        
        OPTIMIZATION: Checks Redis cache first to avoid redundant API calls.
        
        Returns same format as tag_query.
        """
        # Check cache first (use content + description as key)
        cache_text = f"{content}|{description}"
        cache_key = self._cache_key(cache_text, "memory")
        cached = await self._get_cached_tags(cache_key)
        if cached:
            logger.debug(f"Tag cache HIT for memory: {content[:50]}...")
            return cached
        
        self.cache_misses += 1
        
        prompt = f"""You are a memory classification system. Analyze this memory content and extract:
1. domains: Which life areas this relates to (pick 1-3 from: {self._domains_str})
2. entities: What specific things are mentioned (e.g., weight, flight, meeting, car)
3. facets: What contextual modifiers apply (e.g., current, past, future, recurring, deadline)

Memory content: "{content}"
Description: "{description}"

Respond ONLY with valid JSON in this exact format:
{{"domains": ["domain1"], "entities": ["entity1"], "facets": ["facet1"]}}

Be concise. Pick the most relevant items."""

        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()
            
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(text)
            
            result["domains"] = [d.lower() for d in result.get("domains", [])]
            result["entities"] = [e.lower().replace(" ", "_") for e in result.get("entities", [])]
            result["facets"] = [f.lower().replace(" ", "_") for f in result.get("facets", [])]
            
            # Cache the result
            await self._set_cached_tags(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.warning(f"Gemini memory tagging failed: {e}")
            return {"domains": [], "entities": [], "facets": []}

    async def batch_tag_memories(
        self, memories: list[dict[str, str]]
    ) -> list[dict[str, Any]]:
        """
        Tag multiple memories in batch.
        
        Input: [{"content": "...", "description": "..."}, ...]
        Output: [{"domains": [...], "entities": [...], "facets": [...]}, ...]
        """
        results = []
        for mem in memories:
            tags = await self.tag_memory_result(
                mem.get("content", ""),
                mem.get("description", "")
            )
            results.append(tags)
        return results
