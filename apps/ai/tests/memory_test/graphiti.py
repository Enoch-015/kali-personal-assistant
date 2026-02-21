import asyncio
import os
from datetime import datetime, UTC, timezone
import json

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

# Gemini clients
from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.cross_encoder.gemini_reranker_client import GeminiRerankerClient


# ----------------------------
# Configuration
# ----------------------------

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"  # change this
GROUP_ID = "kali-personal-assistant"

GEMINI_API_KEY = "Your gemini key."
if not GEMINI_API_KEY:
    raise RuntimeError(
        "❌ GEMINI_API_KEY not set. Export it before running this script."
    )


# ----------------------------
# Initialize Graphiti
# ----------------------------

async def init_graphiti() -> Graphiti:
    print("🔌 Initializing Graphiti with Gemini...")

    graphiti = Graphiti(
        NEO4J_URI,
        NEO4J_USER,
        NEO4J_PASSWORD,
        llm_client=GeminiClient(
            config=LLMConfig(api_key=GEMINI_API_KEY, model="gemini-2.0-flash")
        ),
        embedder=GeminiEmbedder(
            config=GeminiEmbedderConfig(
                api_key=GEMINI_API_KEY, embedding_model="embedding-001"
            )
        ),
        cross_encoder=GeminiRerankerClient(
            config=LLMConfig(
                api_key=GEMINI_API_KEY,
                model="gemini-2.5-flash-lite-preview-06-17",
            )
        ),
    )

    await graphiti.build_indices_and_constraints()


# ----------------------------
# Ingest Conversations
# ----------------------------

async def main():
    #################################################
    # INITIALIZATION WITH GEMINI
    #################################################
    graphiti = Graphiti(
        NEO4J_URI,
        NEO4J_USER,
        NEO4J_PASSWORD,
        llm_client=GeminiClient(
            config=LLMConfig(api_key=GEMINI_API_KEY, model="gemini-2.0-flash")
        ),
        embedder=GeminiEmbedder(
            config=GeminiEmbedderConfig(
                api_key=GEMINI_API_KEY, embedding_model="embedding-001"
            )
        ),
        cross_encoder=GeminiRerankerClient(
            config=LLMConfig(
                api_key=GEMINI_API_KEY,
                model="gemini-2.5-flash-lite-preview-06-17",
            )
        ),
    )

    try:
        # Initialize indices and constraints
        await graphiti.build_indices_and_constraints()

        #################################################
        # ADDING BUSINESS EPISODES
        #################################################
        episodes = [
        # ---------------------------------------------------------
        # DOMAIN 1: HEALTH & FITNESS
        # ---------------------------------------------------------
        {
            "content": "I weighed in at 165 lbs this morning, which is down 2 lbs from last week.",
            "type": EpisodeType.text,
            "description": "weight log",
        },
        {
            "content": "The user reported feeling a mild migraine after lunch at 2:00 PM.",
            "type": EpisodeType.text,
            "description": "symptom tracking",
        },
        {
            "content": "Completed a 5k run in 28 minutes on Saturday morning.",
            "type": EpisodeType.text,
            "description": "activity log",
        },
        {
            "content": {
                "date": "2023-10-24",
                "sleep_duration": "6h 45m",
                "sleep_quality_score": 72,
                "deep_sleep": "1h 10m"
            },
            "type": EpisodeType.json,
            "description": "sleep analysis",
        },
        {
            "content": {
                "meal": "Lunch",
                "calories": 650,
                "macros": {"protein": "40g", "carbs": "50g", "fat": "20g"},
                "items": ["Grilled Chicken", "Brown Rice", "Avocado"]
            },
            "type": EpisodeType.json,
            "description": "dietary tracking",
        },

        # ---------------------------------------------------------
        # DOMAIN 2: TRAVEL & LOGISTICS
        # ---------------------------------------------------------
        {
            "content": "Flight UA455 to Chicago departs at 8:30 AM from Gate B12.",
            "type": EpisodeType.text,
            "description": "flight itinerary",
        },
        {
            "content": "Remember to pack the universal power adapter for the London trip.",
            "type": EpisodeType.text,
            "description": "travel reminder",
        },
        {
            "content": {
                "hotel_name": "Grand Hyatt Tokyo",
                "check_in": "2024-03-10",
                "check_out": "2024-03-15",
                "reservation_id": "GH-998877"
            },
            "type": EpisodeType.json,
            "description": "accommodation details",
        },
        {
            "content": {
                "destination": "Paris",
                "visa_required": False,
                "currency": "EUR",
                "weather_forecast": "Rainy, 12°C"
            },
            "type": EpisodeType.json,
            "description": "destination briefing",
        },
        {
            "content": "The train from Rome to Florence is booked for seat 4A, carriage 3.",
            "type": EpisodeType.text,
            "description": "train reservation",
        },

        # ---------------------------------------------------------
        # DOMAIN 3: SMART HOME & IOT
        # ---------------------------------------------------------
        {
            "content": "The living room thermostat was set to 72 degrees at 6:00 PM.",
            "type": EpisodeType.text,
            "description": "thermostat log",
        },
        {
            "content": "Front door smart lock battery is critically low (10%).",
            "type": EpisodeType.text,
            "description": "device maintenance",
        },
        {
            "content": {
                "device": "Robot Vacuum",
                "status": "Stuck",
                "location": "Master Bedroom",
                "error_code": "E4"
            },
            "type": EpisodeType.json,
            "description": "device error log",
        },
        {
            "content": {
                "routine": "Good Morning",
                "lights": "50% Brightness",
                "blinds": "Open",
                "coffee_maker": "On"
            },
            "type": EpisodeType.json,
            "description": "automation routine",
        },
        {
            "content": "Garage door was left open for more than 30 minutes.",
            "type": EpisodeType.text,
            "description": "security alert",
        },

        # ---------------------------------------------------------
        # DOMAIN 4: PROFESSIONAL WORK
        # ---------------------------------------------------------
        {
            "content": "Meeting with the engineering team regarding the Q3 roadmap is scheduled for Tuesday.",
            "type": EpisodeType.text,
            "description": "calendar event",
        },
        {
            "content": "The deadline for the 'Project Apollo' design review is next Friday.",
            "type": EpisodeType.text,
            "description": "project deadline",
        },
        {
            "content": {
                "client": "Acme Corp",
                "contact_person": "Jane Doe",
                "email": "jane@acme.com",
                "last_contact": "2023-11-01"
            },
            "type": EpisodeType.json,
            "description": "CRM contact info",
        },
        {
            "content": {
                "task_id": "TSK-402",
                "title": "Fix login bug",
                "status": "In Progress",
                "priority": "High"
            },
            "type": EpisodeType.json,
            "description": "task management",
        },
        {
            "content": "Feedback from the boss: focus more on user retention metrics in the next report.",
            "type": EpisodeType.text,
            "description": "performance feedback",
        },

        # ---------------------------------------------------------
        # DOMAIN 5: PERSONAL FINANCE
        # ---------------------------------------------------------
        {
            "content": "Spent $120 on groceries at Whole Foods yesterday.",
            "type": EpisodeType.text,
            "description": "expense log",
        },
        {
            "content": "Car insurance renewal of $600 is due on the 15th of next month.",
            "type": EpisodeType.text,
            "description": "bill reminder",
        },
        {
            "content": {
                "portfolio_value": 45000,
                "daily_change": "+1.2%",
                "top_gainer": "NVDA",
                "top_loser": "TSLA"
            },
            "type": EpisodeType.json,
            "description": "investment summary",
        },
        {
            "content": {
                "category": "Subscriptions",
                "netflix": 15.99,
                "spotify": 9.99,
                "chatgpt": 20.00,
                "total": 45.98
            },
            "type": EpisodeType.json,
            "description": "monthly subscriptions",
        },
        {
            "content": "Transferred $500 to the High Yield Savings Account.",
            "type": EpisodeType.text,
            "description": "transaction log",
        },

        # ---------------------------------------------------------
        # DOMAIN 6: SOCIAL & NETWORK
        # ---------------------------------------------------------
        {
            "content": "Sarah's birthday is coming up on November 12th.",
            "type": EpisodeType.text,
            "description": "birthday reminder",
        },
        {
            "content": "Met with John from Marketing; he mentioned he loves hiking and vintage wines.",
            "type": EpisodeType.text,
            "description": "person detail",
        },
        {
            "content": {
                "event": "College Reunion",
                "date": "2024-06-01",
                "location": "Boston",
                "attendees_confirmed": ["Mike", "Jessica", "Sam"]
            },
            "type": EpisodeType.json,
            "description": "event planning",
        },
        {
            "content": {
                "gift_idea": "Mechanical Keyboard",
                "recipient": "Brother",
                "occasion": "Christmas",
                "budget": 150
            },
            "type": EpisodeType.json,
            "description": "gift planning",
        },
        {
            "content": "Reminder to call Grandma every Sunday at 4 PM.",
            "type": EpisodeType.text,
            "description": "recurring reminder",
        },

        # ---------------------------------------------------------
        # DOMAIN 7: SHOPPING & INVENTORY
        # ---------------------------------------------------------
        {
            "content": "We are out of olive oil and laundry detergent.",
            "type": EpisodeType.text,
            "description": "shopping list",
        },
        {
            "content": "The new ergonomic office chair was delivered to the front porch.",
            "type": EpisodeType.text,
            "description": "delivery status",
        },
        {
            "content": {
                "order_id": "AMZ-112233",
                "items": ["HDMI Cable", "USB-C Hub"],
                "total": 45.50,
                "estimated_arrival": "Tomorrow"
            },
            "type": EpisodeType.json,
            "description": "order confirmation",
        },
        {
            "content": {
                "item": "Winter Coat",
                "size": "M",
                "brand_preference": ["North Face", "Patagonia"],
                "color": "Black or Navy"
            },
            "type": EpisodeType.json,
            "description": "wishlist item",
        },
        {
            "content": "Return the defective headphones to Best Buy by Saturday.",
            "type": EpisodeType.text,
            "description": "errand",
        },

        # ---------------------------------------------------------
        # DOMAIN 8: EDUCATION & LEARNING
        # ---------------------------------------------------------
        {
            "content": "Completed Chapter 4 of 'Introduction to Python' on Coursera.",
            "type": EpisodeType.text,
            "description": "course progress",
        },
        {
            "content": "Need to research 'Transformers architecture' for the AI blog post.",
            "type": EpisodeType.text,
            "description": "study task",
        },
        {
            "content": {
                "topic": "Spanish Vocabulary",
                "words_learned": ["Gato", "Perro", "Casa", "Biblioteca"],
                "fluency_level": "Beginner"
            },
            "type": EpisodeType.json,
            "description": "language learning",
        },
        {
            "content": {
                "book": "Thinking, Fast and Slow",
                "author": "Daniel Kahneman",
                "current_page": 120,
                "total_pages": 499
            },
            "type": EpisodeType.json,
            "description": "reading tracker",
        },
        {
            "content": "Key takeaway: Compound interest is the eighth wonder of the world.",
            "type": EpisodeType.text,
            "description": "study note",
        },

        # ---------------------------------------------------------
        # DOMAIN 9: VEHICLE & MAINTENANCE
        # ---------------------------------------------------------
        {
            "content": "The check engine light came on while driving on the highway.",
            "type": EpisodeType.text,
            "description": "vehicle alert",
        },
        {
            "content": "Tires were rotated at 45,000 miles.",
            "type": EpisodeType.text,
            "description": "maintenance log",
        },
        {
            "content": {
                "vehicle": "Tesla Model 3",
                "license_plate": "ABC-1234",
                "vin": "5YJ3E1EA1JF...",
                "insurance_provider": "Geico"
            },
            "type": EpisodeType.json,
            "description": "vehicle registration",
        },
        {
            "content": {
                "service": "Oil Change",
                "garage": "Jiffy Lube",
                "cost": 89.99,
                "next_due_date": "2024-05-20"
            },
            "type": EpisodeType.json,
            "description": "service history",
        },
        {
            "content": "Parked on level 3, spot 305 at the airport.",
            "type": EpisodeType.text,
            "description": "parking location",
        },

        # ---------------------------------------------------------
        # DOMAIN 10: MEDIA & ENTERTAINMENT
        # ---------------------------------------------------------
        {
            "content": "Watched the season finale of 'Succession' last night.",
            "type": EpisodeType.text,
            "description": "watch history",
        },
        {
            "content": "Added 'Dune: Part Two' to the watchlist.",
            "type": EpisodeType.text,
            "description": "watchlist",
        },
        {
            "content": {
                "playlist_name": "Focus Mode",
                "genre": "Lo-Fi Beats",
                "platform": "Spotify",
                "duration": "4 hours"
            },
            "type": EpisodeType.json,
            "description": "music preference",
        },
        {
            "content": {
                "game": "Elden Ring",
                "achievement": "Defeated Malenia",
                "playtime_hours": 120
            },
            "type": EpisodeType.json,
            "description": "gaming log",
        },
        {
            "content": "Don't recommend movies with excessive jump scares.",
            "type": EpisodeType.text,
            "description": "user preference",
        }
    ]

        for i, episode in enumerate(episodes):
            await graphiti.add_episode(
                name=f"Episode {i}",
                episode_body=episode["content"]
                if isinstance(episode["content"], str)
                else json.dumps(episode["content"]),
                source=episode["type"],
                source_description=episode["description"],
                reference_time=datetime.now(timezone.utc),
            )
            print(
                f"✅ Added episode: Episode {i} ({episode['type'].value})"
            )

        #################################################
        # BUSINESS QUERIES
        #################################################
        queries = [
            "What was my weight last week?",
            "When is my car insurance due?",
            "What was the status of my robot vacuum?",
            "Where did I park at the airport?",
            "What is the name of the hotel for my Tokyo trip?",
            "What was my sleep quality score on October 24th?",
            "What feedback did my boss give me?",
            "What is the estimated arrival for my Amazon order?",
            "What is the deadline for Project Apollo?",
            "What was my top stock gainer recently?"
        ]

        for q in queries:
            print(f"\n🔎 Searching for: '{q}'")
            results = await graphiti.search(q)

        if results:
            best_result = results[0]  # ✅ only the first, most relevant
            print(f"✅ Answer: {best_result.fact}")
        else:
            print("⚠️ No results found.")


    finally:
        await graphiti.close()
        print("\n🔌 Connection closed")


if __name__ == "__main__":
    asyncio.run(main())