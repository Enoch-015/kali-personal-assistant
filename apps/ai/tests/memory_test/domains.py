"""
Domain and facet definitions for memory tagging.
"""

# Primary domains (stable, ~15-25)
DOMAINS = [
    "health",
    "travel",
    "smart_home",
    "work",
    "finance",
    "social",
    "shopping",
    "education",
    "vehicle",
    "entertainment",
    "identity",
    "relationship",
    "emotion",
    "task",
    "schedule",
    "location",
    "preference",
    "habit",
    "memory_event",
    "coping",
]

# Facets organized by category
FACETS = {
    # Universal facets (apply to all domains)
    "universal": [
        "current",
        "past",
        "future",
        "recurring",
        "temporary",
        "confirmed",
        "uncertain",
        "changed",
        "contradicted",
    ],
    # Emotional facets
    "emotional": [
        "stress",
        "anxiety",
        "excitement",
        "sadness",
        "confidence",
        "motivation",
        "fatigue",
    ],
    # Cognitive / Intent facets
    "cognitive": [
        "planning",
        "reflection",
        "decision",
        "complaint",
        "request",
        "update",
        "correction",
    ],
    # Temporal facets
    "temporal": [
        "immediate",
        "short_term",
        "long_term",
        "deadline",
        "postponed",
    ],
    # Domain-specific entity facets
    "health": [
        "weight_log",
        "symptom_tracking",
        "activity_log",
        "sleep_analysis",
        "dietary_tracking",
    ],
    "travel": [
        "flight_itinerary",
        "travel_reminder",
        "accommodation",
        "destination_briefing",
        "train_reservation",
    ],
    "smart_home": [
        "thermostat_log",
        "device_maintenance",
        "device_error",
        "automation_routine",
        "security_alert",
    ],
    "work": [
        "calendar_event",
        "project_deadline",
        "crm_contact",
        "task_management",
        "performance_feedback",
    ],
    "finance": [
        "expense_log",
        "bill_reminder",
        "investment_summary",
        "subscription",
        "transaction_log",
    ],
    "social": [
        "birthday_reminder",
        "person_detail",
        "event_planning",
        "gift_planning",
        "recurring_reminder",
    ],
    "shopping": [
        "shopping_list",
        "delivery_status",
        "order_confirmation",
        "wishlist",
        "errand",
    ],
    "education": [
        "course_progress",
        "study_task",
        "language_learning",
        "reading_tracker",
        "study_note",
    ],
    "vehicle": [
        "vehicle_alert",
        "maintenance_log",
        "vehicle_registration",
        "service_history",
        "parking_location",
    ],
    "entertainment": [
        "watch_history",
        "watchlist",
        "music_preference",
        "gaming_log",
        "user_preference",
    ],
}

# Flatten all facets for validation
ALL_FACETS = []
for category_facets in FACETS.values():
    ALL_FACETS.extend(category_facets)
ALL_FACETS = list(set(ALL_FACETS))


def get_domain_facets(domain: str) -> list[str]:
    """Get all applicable facets for a domain."""
    facets = []
    facets.extend(FACETS.get("universal", []))
    facets.extend(FACETS.get("temporal", []))
    facets.extend(FACETS.get("cognitive", []))
    facets.extend(FACETS.get(domain, []))
    return list(set(facets))


def validate_domain(domain: str) -> bool:
    """Check if domain is valid."""
    return domain.lower() in DOMAINS


def validate_facet(facet: str) -> bool:
    """Check if facet is valid."""
    return facet.lower() in ALL_FACETS
