"""
Hashing utilities for memory keys using xxhash for O(1) lookups.
"""

import xxhash


def memory_hash(domain: str, entity: str, facet: str) -> str:
    """
    Generate a stable hash for a memory key.
    
    Format: <domain>|<entity>|<facet>
    Returns: 16-character hex digest
    """
    key = f"{domain.lower()}|{entity.lower()}|{facet.lower()}"
    return xxhash.xxh64(key).hexdigest()


def memory_hash_from_tags(tags: dict) -> list[str]:
    """
    Generate all hash combinations from a tag dictionary.
    
    Input: {"domains": ["health", "emotion"], "entities": ["weight", "stress"], "facets": ["current"]}
    Output: List of hashes for all combinations
    """
    domains = tags.get("domains", [])
    entities = tags.get("entities", [])
    facets = tags.get("facets", [])
    
    if not domains or not entities or not facets:
        return []
    
    hashes = []
    for domain in domains:
        for entity in entities:
            for facet in facets:
                hashes.append(memory_hash(domain, entity, facet))
    
    return hashes


def parse_key(canonical_key: str) -> tuple[str, str, str]:
    """
    Parse a canonical key back into components.
    
    Input: "health|weight|current"
    Output: ("health", "weight", "current")
    """
    parts = canonical_key.split("|")
    if len(parts) != 3:
        raise ValueError(f"Invalid canonical key format: {canonical_key}")
    return tuple(parts)


def build_canonical_key(domain: str, entity: str, facet: str) -> str:
    """Build canonical key string."""
    return f"{domain.lower()}|{entity.lower()}|{facet.lower()}"


def get_all_hashes_for_domain(domain: str, entities: list[str], facets: list[str]) -> list[str]:
    """
    Get all hashes for a given domain across entity/facet combinations.
    Useful for domain-based batch operations.
    """
    hashes = []
    for entity in entities:
        for facet in facets:
            hashes.append(memory_hash(domain, entity, facet))
    return hashes
