"""LiveKit voice agent with optional multimodal (vision) support.

Providers (LLM, TTS, STT) are resolved at runtime from
``config.settings.LiveKitSettings`` so that adding / swapping a provider
only requires changing environment variables or Vault secrets.

When the configured LLM model supports vision **and** ``vision_enabled``
is ``True``, the agent automatically:
* captures the user's camera feed (latest frame),
* accepts byte-stream image uploads from the frontend,
* injects images into the chat context on each user turn.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure the apps/ directory is on sys.path so `config` and `services` resolve
_APPS_DIR = str(Path(__file__).resolve().parent.parent.parent)  # apps/
_VOICE_DIR = str(Path(__file__).resolve().parent.parent)         # apps/voice/
for _p in (_APPS_DIR, _VOICE_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dotenv import load_dotenv
from livekit import rtc, api
from livekit.agents import (
    Agent,
    AgentSession,
    ChatContext,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
    get_job_context,
    mcp,
)
from livekit.agents.llm import ImageContent
from livekit.plugins import silero

from config.settings import Settings, get_settings
from services.backend_url_service import BackendRequestService

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INSTRUCTIONS_FALLBACK = "You are a voice-based AI assistant. Use your tools to help the user."
WELCOME_MESSAGE = "Hello! I can communicate with you through voice. How would you like to interact today?"
WELCOME_MESSAGE_VISION = (
    "Hello! I can communicate with you through voice and I can also see! "
    "Share your camera or upload an image and I'll analyze it for you."
)


# =====================================================================
# Provider factory helpers — map config providers → LiveKit plugin instances
# =====================================================================

def _build_stt(settings: Settings):
    """Instantiate an STT plugin from config."""
    lk = settings.livekit
    if not lk.has_stt:
        raise RuntimeError(
            "No STT provider configured. Set DEEPGRAM_API_KEY (or equivalent) "
            "in your environment or Vault."
        )
    stt_cfg = lk.stt
    if stt_cfg.provider == "deepgram":
        from livekit.plugins import deepgram
        return deepgram.STT(
            model=stt_cfg.model,
            language=stt_cfg.language,
        )
    raise RuntimeError(f"Unsupported STT provider: {stt_cfg.provider}")


def _build_tts(settings: Settings):
    """Instantiate a TTS plugin from config."""
    lk = settings.livekit
    if not lk.has_tts:
        logger.warning("No TTS provider configured — voice output will be disabled.")
        return None
    tts_cfg = lk.tts
    if tts_cfg.provider == "azure":
        from livekit.plugins import azure
        return azure.TTS(
            speech_key=tts_cfg.api_key,
            speech_region=tts_cfg.region,
            voice=tts_cfg.voice,
        )
    if tts_cfg.provider == "cartesia":
        from livekit.plugins import cartesia
        return cartesia.TTS(
            model=tts_cfg.model,
            voice=tts_cfg.voice,
        )
    raise RuntimeError(f"Unsupported TTS provider: {tts_cfg.provider}")


def _build_llm(settings: Settings):
    """Instantiate an LLM plugin from config."""
    lk = settings.livekit
    if not lk.has_llm:
        raise RuntimeError(
            "No LLM provider configured. Set OPENAI_API_KEY or GOOGLE_API_KEY "
            "(or equivalent) in your environment or Vault."
        )
    llm_cfg = lk.llm
    if llm_cfg.provider == "openai":
        from livekit.plugins import openai
        return openai.LLM(model=llm_cfg.model)
    if llm_cfg.provider == "gemini":
        from livekit.plugins import google
        return google.LLM(model=llm_cfg.model)
    raise RuntimeError(f"Unsupported LLM provider: {llm_cfg.provider}")


def _check_multimodal(settings: Settings) -> bool:
    """Return ``True`` when vision can be activated.

    Checks:
    1. ``vision_enabled`` flag is ``True`` in config.
    2. The configured LLM model actually supports vision input.

    Logs a warning if vision is requested but the model cannot handle it.
    """
    lk = settings.livekit
    if not lk.vision_enabled:
        return False
    if lk.llm is None:
        logger.warning("Vision requested but no LLM provider configured — disabling vision.")
        return False
    if not lk.llm.supports_vision:
        logger.warning(
            "Vision requested but model %r does not support multimodal input — "
            "disabling vision. Choose a vision-capable model (e.g. gpt-4o, gemini-2.0-flash).",
            lk.llm.model,
        )
        return False
    logger.info("Multimodal vision support ENABLED (model=%s).", lk.llm.model)
    return True


# =====================================================================
# Vision-capable Agent
# =====================================================================

class VisionAgent(Agent):
    """Voice agent that optionally ingests video frames & uploaded images.

    When ``vision`` is ``False`` this behaves like a plain voice agent.
    """

    def __init__(self, *, instructions: str, vision: bool = False) -> None:
        self._vision = vision
        self._latest_frame: str | None = None
        self._video_stream: rtc.VideoStream | None = None
        self._tasks: list[asyncio.Task] = []
        super().__init__(instructions=instructions)

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def on_enter(self):
        if not self._vision:
            return

        room = get_job_context().room

        # Byte-stream handler for images uploaded from the frontend
        def _image_received_handler(reader, participant_identity):
            task = asyncio.create_task(self._image_received(reader, participant_identity))
            self._tasks.append(task)
            task.add_done_callback(lambda t: self._tasks.remove(t) if t in self._tasks else None)

        room.register_byte_stream_handler("images", _image_received_handler)

        # Look for an existing video track
        for participant in room.remote_participants.values():
            video_tracks = [
                pub.track
                for pub in participant.track_publications.values()
                if pub.track and pub.track.kind == rtc.TrackKind.KIND_VIDEO
            ]
            if video_tracks:
                self._create_video_stream(video_tracks[0])
                break

        # Watch for new video tracks
        @room.on("track_subscribed")
        def on_track_subscribed(
            track: rtc.Track,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant,
        ):
            if track.kind == rtc.TrackKind.KIND_VIDEO:
                self._create_video_stream(track)

    # ── Image upload handler ─────────────────────────────────────────

    async def _image_received(self, reader, participant_identity):
        """Handle images uploaded from the frontend via byte stream."""
        image_bytes = bytes()
        async for chunk in reader:
            image_bytes += chunk

        chat_ctx = self.chat_ctx.copy()
        chat_ctx.add_message(
            role="user",
            content=[
                "Here's an image I want to share with you:",
                ImageContent(
                    image=f"data:image/png;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
                ),
            ],
        )
        await self.update_chat_ctx(chat_ctx)

    # ── Turn hook — inject latest video frame ────────────────────────

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: dict) -> None:
        if not self._vision or not self._latest_frame:
            return

        if isinstance(new_message.content, list):
            new_message.content.append(ImageContent(image=self._latest_frame))
        else:
            new_message.content = [new_message.content, ImageContent(image=self._latest_frame)]
        self._latest_frame = None

    # ── Video stream buffering ───────────────────────────────────────

    def _create_video_stream(self, track: rtc.Track):
        if self._video_stream is not None:
            self._video_stream.close()

        self._video_stream = rtc.VideoStream(track)

        async def _read_stream():
            try:
                from livekit.agents.utils.images import encode, EncodeOptions, ResizeOptions
            except ImportError:
                logger.warning("livekit image utils not available — video frame capture disabled.")
                return

            async for event in self._video_stream:
                image_bytes = encode(
                    event.frame,
                    EncodeOptions(
                        format="JPEG",
                        resize_options=ResizeOptions(width=1024, height=1024, strategy="scale_aspect_fit"),
                    ),
                )
                self._latest_frame = (
                    f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
                )

        task = asyncio.create_task(_read_stream())
        self._tasks.append(task)
        task.add_done_callback(lambda t: self._tasks.remove(t) if t in self._tasks else None)


# =====================================================================
# Agent service (entrypoint)
# =====================================================================

@dataclass(slots=True)
class UserCtx:
    user_id: str
    config_id: str
    session_id: str
    system_prompt: str


class ModernKaliAgentService:
    """Main LiveKit worker service — wired to ``config.settings``."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings("voice")
        self._client = BackendRequestService(settings=self._settings)
        self._mcp_exit_stack = None

    # ── MCP helper ────────────────────────────────────────────────────

    async def _connect_and_build_tools(self, urls: List[str]) -> List[str]:
        mcp_urls: list[str] = []
        for url in urls:
            try:
                clean = url.rstrip("/")
                endpoint = f"{clean}/sse"
                mcp_urls.append(endpoint)
                logger.info("Registered MCP server: %s", endpoint)
            except Exception as e:
                logger.error("Failed to process MCP URL %r: %s", url, e)
        return mcp_urls

    # ── Entrypoint ────────────────────────────────────────────────────

    async def entrypoint(self, ctx: JobContext) -> None:
        await ctx.connect()
        logger.info("Connected to room: %s", ctx.room.name)

        # --- metadata parsing helpers ---
        def _parse(raw: Optional[str]) -> dict:
            if not raw:
                return {}
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {}

        async def extract_meta():
            meta = _parse(ctx.job.metadata)
            if not meta.get("ephemeral_api_key"):
                # Check room metadata (set server-side by join endpoint)
                rm = _parse(getattr(ctx.room, "metadata", None))
                if rm.get("ephemeral_api_key"):
                    meta = rm
            if not meta.get("ephemeral_api_key"):
                for _, p in ctx.room.remote_participants.items():
                    pm = _parse(getattr(p, "metadata", None))
                    if pm.get("ephemeral_api_key"):
                        meta = pm
                        break
            if not meta.get("ephemeral_api_key"):
                lm = _parse(getattr(ctx.room.local_participant, "metadata", None))
                if lm.get("ephemeral_api_key"):
                    meta = lm
            return (
                meta.get("ephemeral_api_key"),
                meta.get("session_id") or meta.get("sessionId") or meta.get("session"),
                meta.get("system_prompt"),
            )

        # Wait for metadata
        ephemeral_api_key, sess_id, system_prompt_override = None, None, None
        for _ in range(10):
            ephemeral_api_key, sess_id, system_prompt_override = await extract_meta()
            if ephemeral_api_key and sess_id:
                break
            await asyncio.sleep(0.5)

        if not (ephemeral_api_key and sess_id):
            logger.error("Missing ephemeral_api_key or session_id. Exiting.")
            return

        self._client.set_ephemeral_key(ephemeral_api_key)

        # Fetch user config from /api/config
        user_cfg: Dict[str, Any] = {}
        try:
            resp = await self._client.get_org_config()
            if resp and resp.get("success"):
                user_cfg = resp.get("config", {})
            else:
                logger.warning("Config response indicated failure: %s", resp)
        except Exception as e:
            logger.warning("Failed to fetch user config (continuing with defaults): %s", e)

        user_ctx = UserCtx(
            user_id=user_cfg.get("userId", "unknown"),
            config_id=user_cfg.get("id", "default"),
            session_id=sess_id,
            system_prompt=(
                system_prompt_override
                or user_cfg.get("systemPrompt")
                or user_cfg.get("instructions")
                or INSTRUCTIONS_FALLBACK
            ),
        )
        logger.info(
            "Loaded config for User: %s, Session: %s (model=%s)",
            user_ctx.user_id, user_ctx.session_id, user_cfg.get("aiModel", "default"),
        )

        # MCP tools (optional — the /api/mcp endpoint may not exist yet)
        livekit_tools: list[str] = []
        try:
            mcp_resp = await self._client.get_livekit_mcp_urls()
            mcp_urls = mcp_resp.get("urls", [])
            if mcp_urls:
                logger.info("Fetching tools from MCP URLs: %s", mcp_urls)
                livekit_tools = await self._connect_and_build_tools(mcp_urls)
            else:
                logger.debug("No MCP URLs configured.")
        except Exception:
            logger.debug("MCP endpoint not available — continuing without MCP tools.")

        # ── Build plugins from settings ──────────────────────────────
        stt = _build_stt(self._settings)
        tts = _build_tts(self._settings)
        llm = _build_llm(self._settings)
        vad = ctx.proc.userdata["vad"]

        vision_active = _check_multimodal(self._settings)

        # Optional: turn detection — instantiated inside entrypoint per LiveKit docs.
        # See: https://docs.livekit.io/agents/build/turns/turn-detector/
        turn_detection = None
        if self._settings.livekit.turn_detection_enabled:
            try:
                from livekit.plugins.turn_detector.multilingual import MultilingualModel
                turn_detection = MultilingualModel()
            except ImportError:
                logger.debug("Multilingual turn detector not installed — skipping.")
            except Exception as e:
                logger.warning("Failed to initialize turn detector: %s", e)

        agent = VisionAgent(
            instructions=user_ctx.system_prompt,
            vision=vision_active,
        )

        # Build room input options
        room_input_opts_kwargs: dict[str, Any] = {}
        if vision_active:
            room_input_opts_kwargs["video_enabled"] = True
        if self._settings.livekit.noise_cancellation_enabled:
            try:
                from livekit.plugins import noise_cancellation
                room_input_opts_kwargs["noise_cancellation"] = noise_cancellation.BVC()
            except ImportError:
                logger.debug("Noise cancellation plugin not installed — skipping.")

        session = AgentSession(
            stt=stt,
            llm=llm,
            tts=tts,
            vad=vad,
            turn_detection=turn_detection,
            mcp_servers=[mcp.MCPServerHTTP(url=u) for u in livekit_tools],
        )

        def on_participant_connected(participant):
            async def send_welcome():
                msg = WELCOME_MESSAGE_VISION if vision_active else WELCOME_MESSAGE
                await ctx.room.local_participant.send_text(msg, topic="lk.chat")
            asyncio.create_task(send_welcome())

        ctx.room.on("participant_connected", on_participant_connected)

        await session.start(
            room=ctx.room,
            agent=agent,
            room_input_options=RoomInputOptions(**room_input_opts_kwargs),
        )

        welcome = WELCOME_MESSAGE_VISION if vision_active else WELCOME_MESSAGE
        session.generate_reply(instructions=f"Say exactly: {welcome}")
        logger.info(
            "Agent session started (vision=%s, user=%s, session=%s)",
            vision_active, user_ctx.user_id, user_ctx.session_id,
        )

        # ── Shutdown handler ─────────────────────────────────────────

        async def shutdown_handler(_):
            logger.info("Shutting down...")
            if self._mcp_exit_stack:
                await self._mcp_exit_stack.aclose()
            try:
                await self._client.update_session(user_ctx.session_id, {"status": "ended"})
            except Exception as e:
                logger.debug("Error ending session: %s", e)
            try:
                if hasattr(session, "history"):
                    hist = session.history.to_dict()
                    await self._client.post(
                        "/api/livekit/transcript",
                        data={"session_id": user_ctx.session_id, "history": hist},
                    )
            except Exception as e:
                logger.debug("Error uploading transcript: %s", e)

        ctx.add_shutdown_callback(shutdown_handler)

    # ── Prewarm ──────────────────────────────────────────────────────
    # MultilingualModel is NOT loaded here — it must be instantiated inside
    # the job entrypoint per LiveKit docs. Only load models that don't
    # require a job context (e.g. silero VAD).

    def prewarm(self, proc: JobProcess):
        proc.userdata["vad"] = silero.VAD.load()


if __name__ == "__main__":
    manager = ModernKaliAgentService()
    cli.run_app(WorkerOptions(entrypoint_fnc=manager.entrypoint, prewarm_fnc=manager.prewarm))