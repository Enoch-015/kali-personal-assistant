import os
import json
import uuid
from typing import Optional, Set

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

try:  # Token builder
    from livekit.api.access_token import AccessToken, VideoGrants  # type: ignore
except Exception:  # pragma: no cover
    AccessToken = None  # type: ignore
    VideoGrants = None  # type: ignore

try:  # For remote room listing uniqueness (optional)
    from livekit.api import LiveKitAPI, ListRoomsRequest  # type: ignore
except Exception:  # pragma: no cover
    LiveKitAPI = None  # type: ignore
    ListRoomsRequest = None  # type: ignore


def generate_room_name(existing: Optional[Set[str]] = None) -> str:
    existing = existing or set()
    name = f"room-{uuid.uuid4().hex[:8]}"
    while name in existing:
        name = f"room-{uuid.uuid4().hex[:8]}"
    return name


async def generate_unique_room_name() -> str:
    """Attempt to generate a unique room name by querying existing rooms from LiveKit.

    Falls back to purely local generation if LiveKitAPI not available.
    """
    if LiveKitAPI is None or ListRoomsRequest is None:
        return generate_room_name()
    try:
        api = LiveKitAPI()
        resp = await api.room.list_rooms(ListRoomsRequest())
        existing = {r.name for r in resp.rooms}
        await api.aclose()
        return generate_room_name(existing)
    except Exception:
        # Silent fallback; logging could be added later
        return generate_room_name()


def build_livekit_token(room: str, *, metadata: dict) -> str:
    """Build a LiveKit access token using the official SDK objects to match reference implementation.

    Metadata is JSON encoded and attached; grants limited to provided room with room_join permission.
    """
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise RuntimeError("LiveKit credentials not configured")
    if AccessToken is None or VideoGrants is None:
        raise RuntimeError("livekit-api package not installed. Add it to requirements and install.")

    token_obj = (
        AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(room)        # identity (room-specific in this simple case)
        .with_name(room)            # display name
        .with_metadata(json.dumps(metadata))
        .with_grants(VideoGrants(room_join=True, room=room))
    )
    return token_obj.to_jwt()