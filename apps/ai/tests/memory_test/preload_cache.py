"""
Pre-load Graphiti data into L2 cache for benchmarking.
This script fetches all episodes from Graphiti, tags them with Gemini, and caches them.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.cross_encoder.gemini_reranker_client import GeminiRerankerClient

from gemini_tagger import GeminiTagger
from memory_cache import MemoryCache, MemoryEntry
from hashing import memory_hash, build_canonical_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
GEMINI_API_KEY = "Your gemini key"
REDIS_URL = "redis://localhost:6379/0"

# Episodes to preload (same as graphiti.py ingestion)
EPISODES = [
    # HEALTH & FITNESS
    {"content": "I weighed in at 165 lbs this morning, which is down 2 lbs from last week.", "description": "weight log"},
    {"content": "The user reported feeling a mild migraine after lunch at 2:00 PM.", "description": "symptom tracking"},
    {"content": "Completed a 5k run in 28 minutes on Saturday morning.", "description": "activity log"},
    {"content": json.dumps({"date": "2023-10-24", "sleep_duration": "6h 45m", "sleep_quality_score": 72, "deep_sleep": "1h 10m"}), "description": "sleep analysis"},
    {"content": json.dumps({"meal": "Lunch", "calories": 650, "macros": {"protein": "40g", "carbs": "50g", "fat": "20g"}, "items": ["Grilled Chicken", "Brown Rice", "Avocado"]}), "description": "dietary tracking"},
    
    # TRAVEL & LOGISTICS
    {"content": "Flight UA455 to Chicago departs at 8:30 AM from Gate B12.", "description": "flight itinerary"},
    {"content": "Remember to pack the universal power adapter for the London trip.", "description": "travel reminder"},
    {"content": json.dumps({"hotel_name": "Grand Hyatt Tokyo", "check_in": "2024-03-10", "check_out": "2024-03-15", "reservation_id": "GH-998877"}), "description": "accommodation details"},
    {"content": json.dumps({"destination": "Paris", "visa_required": False, "currency": "EUR", "weather_forecast": "Rainy, 12°C"}), "description": "destination briefing"},
    {"content": "The train from Rome to Florence is booked for seat 4A, carriage 3.", "description": "train reservation"},
    
    # SMART HOME & IOT
    {"content": "The living room thermostat was set to 72 degrees at 6:00 PM.", "description": "thermostat log"},
    {"content": "Front door smart lock battery is critically low (10%).", "description": "device maintenance"},
    {"content": json.dumps({"device": "Robot Vacuum", "status": "Stuck", "location": "Master Bedroom", "error_code": "E4"}), "description": "device error log"},
    {"content": json.dumps({"routine": "Good Morning", "lights": "50% Brightness", "blinds": "Open", "coffee_maker": "On"}), "description": "automation routine"},
    {"content": "Garage door was left open for more than 30 minutes.", "description": "security alert"},
    
    # PROFESSIONAL WORK
    {"content": "Meeting with the engineering team regarding the Q3 roadmap is scheduled for Tuesday.", "description": "calendar event"},
    {"content": "The deadline for the 'Project Apollo' design review is next Friday.", "description": "project deadline"},
    {"content": json.dumps({"client": "Acme Corp", "contact_person": "Jane Doe", "email": "jane@acme.com", "last_contact": "2023-11-01"}), "description": "CRM contact info"},
    {"content": json.dumps({"task_id": "TSK-402", "title": "Fix login bug", "status": "In Progress", "priority": "High"}), "description": "task management"},
    {"content": "Feedback from the boss: focus more on user retention metrics in the next report.", "description": "performance feedback"},
    
    # PERSONAL FINANCE
    {"content": "Spent $120 on groceries at Whole Foods yesterday.", "description": "expense log"},
    {"content": "Car insurance renewal of $600 is due on the 15th of next month.", "description": "bill reminder"},
    {"content": json.dumps({"portfolio_value": 45000, "daily_change": "+1.2%", "top_gainer": "NVDA", "top_loser": "TSLA"}), "description": "investment summary"},
    {"content": json.dumps({"category": "Subscriptions", "netflix": 15.99, "spotify": 9.99, "chatgpt": 20.00, "total": 45.98}), "description": "monthly subscriptions"},
    {"content": "Transferred $500 to the High Yield Savings Account.", "description": "transaction log"},
    
    # SOCIAL & NETWORK
    {"content": "Sarah's birthday is coming up on November 12th.", "description": "birthday reminder"},
    {"content": "Met with John from Marketing; he mentioned he loves hiking and vintage wines.", "description": "person detail"},
    {"content": json.dumps({"event": "College Reunion", "date": "2024-06-01", "location": "Boston", "attendees_confirmed": ["Mike", "Jessica", "Sam"]}), "description": "event planning"},
    {"content": json.dumps({"gift_idea": "Mechanical Keyboard", "recipient": "Brother", "occasion": "Christmas", "budget": 150}), "description": "gift planning"},
    {"content": "Reminder to call Grandma every Sunday at 4 PM.", "description": "recurring reminder"},
    
    # SHOPPING & INVENTORY
    {"content": "We are out of olive oil and laundry detergent.", "description": "shopping list"},
    {"content": "The new ergonomic office chair was delivered to the front porch.", "description": "delivery status"},
    {"content": json.dumps({"order_id": "AMZ-112233", "items": ["HDMI Cable", "USB-C Hub"], "total": 45.50, "estimated_arrival": "Tomorrow"}), "description": "order confirmation"},
    {"content": json.dumps({"item": "Winter Coat", "size": "M", "brand_preference": ["North Face", "Patagonia"], "color": "Black or Navy"}), "description": "wishlist item"},
    {"content": "Return the defective headphones to Best Buy by Saturday.", "description": "errand"},
    
    # EDUCATION & LEARNING
    {"content": "Completed Chapter 4 of 'Introduction to Python' on Coursera.", "description": "course progress"},
    {"content": "Need to research 'Transformers architecture' for the AI blog post.", "description": "study task"},
    {"content": json.dumps({"topic": "Spanish Vocabulary", "words_learned": ["Gato", "Perro", "Casa", "Biblioteca"], "fluency_level": "Beginner"}), "description": "language learning"},
    {"content": json.dumps({"book": "Thinking, Fast and Slow", "author": "Daniel Kahneman", "current_page": 120, "total_pages": 499}), "description": "reading tracker"},
    {"content": "Key takeaway: Compound interest is the eighth wonder of the world.", "description": "study note"},
    
    # VEHICLE & MAINTENANCE
    {"content": "The check engine light came on while driving on the highway.", "description": "vehicle alert"},
    {"content": "Tires were rotated at 45,000 miles.", "description": "maintenance log"},
    {"content": json.dumps({"vehicle": "Tesla Model 3", "license_plate": "ABC-1234", "vin": "5YJ3E1EA1JF...", "insurance_provider": "Geico"}), "description": "vehicle registration"},
    {"content": json.dumps({"service": "Oil Change", "garage": "Jiffy Lube", "cost": 89.99, "next_due_date": "2024-05-20"}), "description": "service history"},
    {"content": "Parked on level 3, spot 305 at the airport.", "description": "parking location"},
    
    # MEDIA & ENTERTAINMENT
    {"content": "Watched the season finale of 'Succession' last night.", "description": "watch history"},
    {"content": "Added 'Dune: Part Two' to the watchlist.", "description": "watchlist"},
    {"content": json.dumps({"playlist_name": "Focus Mode", "genre": "Lo-Fi Beats", "platform": "Spotify", "duration": "4 hours"}), "description": "music preference"},
    {"content": json.dumps({"game": "Elden Ring", "achievement": "Defeated Malenia", "playtime_hours": 120}), "description": "gaming log"},
    {"content": "Don't recommend movies with excessive jump scares.", "description": "user preference"},
]


async def preload_l2_cache():
    """Pre-load all episodes into L2 cache with Gemini tagging."""
    
    logger.info("Initializing cache and tagger...")
    
    cache = MemoryCache(REDIS_URL)
    await cache.connect()
    
    tagger = GeminiTagger(GEMINI_API_KEY)
    
    # Clear existing cache
    await cache.clear_all()
    logger.info("Cleared existing cache")
    
    loaded = 0
    failed = 0
    
    for i, episode in enumerate(EPISODES):
        content = episode["content"]
        description = episode["description"]
        
        logger.info(f"[{i+1}/{len(EPISODES)}] Processing: {description}")
        
        try:
            # Tag with Gemini
            tags = await tagger.tag_memory_result(content, description)
            
            if not tags.get("domains") or not tags.get("entities") or not tags.get("facets"):
                logger.warning(f"  Incomplete tags: {tags}")
                # Use fallback tags
                tags = {
                    "domains": ["memory_event"],
                    "entities": [description.replace(" ", "_")],
                    "facets": ["past"],
                }
            
            # Build canonical key and hash
            canonical = build_canonical_key(
                tags["domains"][0],
                tags["entities"][0],
                tags["facets"][0],
            )
            hash_key = memory_hash(
                tags["domains"][0],
                tags["entities"][0],
                tags["facets"][0],
            )
            
            # Create entry
            entry = MemoryEntry(
                hash_key=hash_key,
                canonical_key=canonical,
                content=content,
                description=description,
                graphiti_id=f"episode_{i}",
                score=0.5,
                tags=tags,
            )
            
            # Store in L2
            is_new = await cache.l2_put(entry)
            if is_new:
                loaded += 1
                logger.info(f"  ✅ Cached: {canonical}")
            else:
                logger.info(f"  🔄 Updated: {canonical}")
            
            # Rate limit for Gemini API
            await asyncio.sleep(0.2)
            
        except Exception as e:
            logger.error(f"  ❌ Failed: {e}")
            failed += 1
    
    # Print summary
    stats = await cache.get_stats("preload")
    print("\n" + "=" * 50)
    print("PRELOAD SUMMARY")
    print("=" * 50)
    print(f"Total Episodes:   {len(EPISODES)}")
    print(f"Successfully Loaded:  {loaded}")
    print(f"Failed:               {failed}")
    print(f"L2 Cache Size:        {stats['l2_total']}")
    print("=" * 50)
    
    await cache.close()


async def verify_l2_cache():
    """Verify L2 cache contents."""
    
    cache = MemoryCache(REDIS_URL)
    await cache.connect()
    
    stats = await cache.get_stats("verify")
    print(f"\nL2 Cache contains {stats['l2_total']} entries")
    
    # Sample some domains
    for domain in ["health", "finance", "travel", "work"]:
        entries = await cache.l2_get_by_domain(domain)
        print(f"  {domain}: {len(entries)} entries")
        for entry in entries[:2]:
            print(f"    - {entry.canonical_key}: {entry.content[:50]}...")
    
    await cache.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        asyncio.run(verify_l2_cache())
    else:
        asyncio.run(preload_l2_cache())
