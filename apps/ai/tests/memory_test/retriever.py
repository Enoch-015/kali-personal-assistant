"""
Memory retrieval orchestrator that coordinates:
1. Query tagging via Gemini
2. L1/L2 cache lookups
3. Graphiti fallback queries
4. Promotion/demotion logic
5. Result tagging and caching
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from graphiti_core import Graphiti
from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.cross_encoder.gemini_reranker_client import GeminiRerankerClient

from gemini_tagger import GeminiTagger
from memory_cache import MemoryCache, MemoryEntry
from hashing import memory_hash, build_canonical_key

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result of a memory retrieval operation."""
    query: str
    query_tags: dict
    l1_hits: list[MemoryEntry]
    l2_hits: list[MemoryEntry]
    graphiti_hits: list[MemoryEntry]
    promoted: list[str]  # Hashes promoted to L1
    demoted: list[str]   # Hashes demoted from L1
    total_time_ms: float
    cache_time_ms: float
    graphiti_time_ms: float
    tagging_time_ms: float
    
    @property
    def all_results(self) -> list[MemoryEntry]:
        """All results ordered by score (L1 > L2 > Graphiti)."""
        all_entries = []
        all_entries.extend(sorted(self.l1_hits, key=lambda x: x.score, reverse=True))
        all_entries.extend(sorted(self.l2_hits, key=lambda x: x.score, reverse=True))
        all_entries.extend(sorted(self.graphiti_hits, key=lambda x: x.score, reverse=True))
        return all_entries
    
    @property
    def hit_source(self) -> str:
        """Primary source of results."""
        if self.l1_hits:
            return "L1"
        if self.l2_hits:
            return "L2"
        if self.graphiti_hits:
            return "Graphiti"
        return "None"


class MemoryRetriever:
    """
    Orchestrates memory retrieval across cache layers and Graphiti.
    """

    def __init__(
        self,
        graphiti: Graphiti,
        cache: MemoryCache,
        tagger: GeminiTagger,
        group_id: str = "kali-personal-assistant",
    ):
        self.graphiti = graphiti
        self.cache = cache
        self.tagger = tagger
        self.group_id = group_id

    async def retrieve(
        self,
        query: str,
        session_id: str,
        max_results: int = 5,
        skip_graphiti: bool = False,
        skip_cache: bool = False,
    ) -> RetrievalResult:
        """
        Retrieve memories for a query using the cache hierarchy.
        
        Flow:
        1. Tag the query with Gemini
        2. Look up L1 cache (session hot set)
        3. Look up L2 cache (warm storage)
        4. Fall back to Graphiti if needed
        5. Tag and cache Graphiti results
        6. Promote relevant results to L1
        7. Demote stale L1 entries
        
        Args:
            skip_cache: If True, bypass L1/L2 cache entirely (direct Graphiti mode)
        """
        start_time = time.perf_counter()
        
        # Step 1: Tag the query
        tag_start = time.perf_counter()
        query_tags = await self.tagger.tag_query(query)
        tagging_time = (time.perf_counter() - tag_start) * 1000
        
        logger.info(f"Query tagged: {query_tags}")
        
        l1_hits = []
        l2_hits = []
        cache_time = 0.0
        
        # Step 2-3: Cache lookup (skip if direct mode)
        if not skip_cache:
            cache_start = time.perf_counter()
            l1_hits, l2_hits = await self.cache.lookup(session_id, query_tags)
            cache_time = (time.perf_counter() - cache_start) * 1000
            
            logger.info(f"Cache hits: L1={len(l1_hits)}, L2={len(l2_hits)}")
        
        # Step 4: Graphiti fallback if cache insufficient or skip_cache mode
        graphiti_hits = []
        graphiti_time = 0.0
        
        total_cache_hits = len(l1_hits) + len(l2_hits)
        need_graphiti = skip_cache or (not skip_graphiti and total_cache_hits < max_results)
        
        if need_graphiti:
            needed_count = max_results if skip_cache else (max_results - total_cache_hits)
            graphiti_start = time.perf_counter()
            graphiti_hits = await self._query_graphiti(query, needed_count)
            graphiti_time = (time.perf_counter() - graphiti_start) * 1000
            
            logger.info(f"Graphiti hits: {len(graphiti_hits)}")
            
            # Step 5: Tag and cache Graphiti results (skip if in direct mode)
            if not skip_cache:
                for entry in graphiti_hits:
                    entry_tags = await self.tagger.tag_memory_result(
                        entry.content, entry.description
                    )
                    entry.tags = entry_tags
                    
                    # Generate hash from tags
                    if entry_tags.get("domains") and entry_tags.get("entities") and entry_tags.get("facets"):
                        canonical = build_canonical_key(
                            entry_tags["domains"][0],
                            entry_tags["entities"][0],
                            entry_tags["facets"][0],
                        )
                        entry.canonical_key = canonical
                        entry.hash_key = memory_hash(
                            entry_tags["domains"][0],
                            entry_tags["entities"][0],
                            entry_tags["facets"][0],
                        )
                        
                        # Store in L2
                        await self.cache.l2_put(entry)
        
        # Step 6: Promote relevant results to L1 (skip if in direct mode)
        promoted = []
        demoted = []
        
        if not skip_cache:
            all_candidates = l2_hits + graphiti_hits
            for entry in all_candidates:
                # Calculate relevance (simple: based on tag overlap)
                relevance = self._calculate_relevance(entry.tags, query_tags)
                entry.score = relevance
                
                if await self.cache.l1_promote(session_id, entry.hash_key, relevance):
                    promoted.append(entry.hash_key)
            
            # Step 7: Demote stale L1 entries (those not matching current query)
            current_l1 = await self.cache.l1_get_all(session_id)
            relevant_hashes = {e.hash_key for e in l1_hits + all_candidates}
            
            for hash_key, old_score in current_l1:
                if hash_key not in relevant_hashes:
                    # Decay relevance for non-matching entries
                    new_score = old_score * 0.8
                    await self.cache.l1_update_relevance(session_id, hash_key, new_score)
                    if new_score < self.cache.DEMOTION_THRESHOLD:
                        demoted.append(hash_key)
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        return RetrievalResult(
            query=query,
            query_tags=query_tags,
            l1_hits=l1_hits,
            l2_hits=l2_hits,
            graphiti_hits=graphiti_hits,
            promoted=promoted,
            demoted=demoted,
            total_time_ms=total_time,
            cache_time_ms=cache_time,
            graphiti_time_ms=graphiti_time,
            tagging_time_ms=tagging_time,
        )

    async def _query_graphiti(self, query: str, limit: int) -> list[MemoryEntry]:
        """Query Graphiti and convert results to MemoryEntry objects."""
        try:
            results = await self.graphiti.search(query, num_results=limit)
            
            entries = []
            for i, result in enumerate(results or []):
                fact = getattr(result, "fact", None)
                if isinstance(fact, str) and fact.strip():
                    entry = MemoryEntry(
                        hash_key=f"graphiti_{i}_{hash(fact)}",
                        canonical_key="unknown|unknown|unknown",
                        content=fact.strip(),
                        description=f"Graphiti result {i+1}",
                        graphiti_id=getattr(result, "uuid", None),
                        score=0.5,  # Default score for Graphiti results
                    )
                    entries.append(entry)
            
            return entries
            
        except Exception as e:
            logger.error(f"Graphiti query failed: {e}")
            return []

    def _calculate_relevance(self, entry_tags: dict, query_tags: dict) -> float:
        """
        Calculate relevance score based on tag overlap.
        Returns score between 0.0 and 1.0.
        """
        if not entry_tags or not query_tags:
            return 0.5
        
        score = 0.0
        weights = {"domains": 0.4, "entities": 0.4, "facets": 0.2}
        
        for key, weight in weights.items():
            entry_set = set(entry_tags.get(key, []))
            query_set = set(query_tags.get(key, []))
            
            if entry_set and query_set:
                overlap = len(entry_set & query_set)
                union = len(entry_set | query_set)
                score += weight * (overlap / union if union > 0 else 0)
        
        return min(1.0, score + 0.3)  # Base score + overlap


async def create_retriever(
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    gemini_api_key: str,
    redis_url: str = "redis://localhost:6379/0",
    group_id: str = "kali-personal-assistant",
) -> MemoryRetriever:
    """Factory function to create a fully initialized MemoryRetriever."""
    
    # Initialize Graphiti
    graphiti = Graphiti(
        neo4j_uri,
        neo4j_user,
        neo4j_password,
        llm_client=GeminiClient(
            config=LLMConfig(api_key=gemini_api_key, model="gemini-2.0-flash")
        ),
        embedder=GeminiEmbedder(
            config=GeminiEmbedderConfig(
                api_key=gemini_api_key, embedding_model="embedding-001"
            )
        ),
        cross_encoder=GeminiRerankerClient(
            config=LLMConfig(
                api_key=gemini_api_key,
                model="gemini-2.5-flash-lite-preview-06-17",
            )
        ),
    )
    
    # Initialize cache
    cache = MemoryCache(redis_url)
    await cache.connect()
    
    # Initialize tagger with Redis for tag caching
    tagger = GeminiTagger(gemini_api_key, redis_url=redis_url)
    
    return MemoryRetriever(graphiti, cache, tagger, group_id)
