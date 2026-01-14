import os
import json
import logging
import asyncio
from dataclasses import dataclass
from typing import List, Any, Dict, Optional

from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    mcp,
)

from livekit.plugins import silero, deepgram, openai, azure

# --- MCP Client Imports ---
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from requests import session

from api_client import BackendAPIClient

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INSTRUCTIONS_FALLBACK = "You are a voice-based AI assistant. Use your tools to help the user."
WELCOME_MESSAGE = "Hello! I can communicate with you through voice. How would you like to interact today?"

@dataclass(slots=True)
class OrgCtx:
    org_id: str
    session_id: str
    system_prompt: str

class ModernKaliAgentService:
    def __init__(self):
        # Initialize your backend client
        self._client = BackendAPIClient(os.getenv("BASE_URL", "http://localhost:8000"))
        # We use an AsyncExitStack to manage multiple MCP connections simultaneously
        self._mcp_exit_stack = None 

    async def _connect_and_build_tools(self, urls: List[str]) -> List[str]:
            """
            MCP servers for LiveKit must be the base MCP endpoint, e.g.:
                https://your-cloudrun-url/mcp

            This function normalizes the returned URLs and returns
            the proper MCP HTTP endpoints for LiveKit agents.
            """
            mcp_urls = []

            for url in urls:
                try:
                    clean = url.rstrip("/")
                    # LiveKit always expects the MCP base route exactly once
                    endpoint = f"{clean}/sse"
                    mcp_urls.append(endpoint)
                    logger.info(f"Registered MCP server: {endpoint}")
                except Exception as e:
                    logger.error(f"Failed to process MCP URL '{url}': {e}")

            return mcp_urls

            

    async def entrypoint(self, ctx: JobContext) -> None:
        await ctx.connect()
        logger.info(f"Connected to room: {ctx.room.name}")

        # --- 1. Metadata Extraction (Robust Retry Logic) ---
        def _parse(raw: Optional[str]) -> dict:
            if not raw: return {}
            try: return json.loads(raw)
            except json.JSONDecodeError: return {}

        async def extract_meta():
            # Check Job Metadata
            meta = _parse(ctx.job.metadata)
            
            # Check Remote Participants Metadata
            if not meta.get("ephemeral_api_key"):
                for _, p in ctx.room.remote_participants.items():
                    pm = _parse(getattr(p, "metadata", None))
                    if pm.get("ephemeral_api_key"):
                        meta = pm
                        break
            
            # Check Local Participant Metadata
            if not meta.get("ephemeral_api_key"):
                lm = _parse(getattr(ctx.room.local_participant, "metadata", None))
                if lm.get("ephemeral_api_key"):
                    meta = lm
            
            return (
                meta.get("ephemeral_api_key"),
                meta.get("session_id") or meta.get("session"),
                meta.get("system_prompt"),
            )

        ephemeral_api_key, sess_id, system_prompt_override = None, None, None
        # Retry loop to wait for metadata to propagate
        for _ in range(10):
            ephemeral_api_key, sess_id, system_prompt_override = await extract_meta()
            if ephemeral_api_key and sess_id:
                break
            await asyncio.sleep(0.5)

        if not (ephemeral_api_key and sess_id):
            logger.error("Missing ephemeral_api_key or session_id. Exiting.")
            return

        # Authenticate Client
        self._client.ephemeral_key = ephemeral_api_key

        # --- 2. Fetch Org Config (System Prompt) ---
        try:
            cfg = await self._client.get_org_config(auth_token=ephemeral_api_key)
        except Exception as e:
            logger.error(f"Failed to fetch org config: {e}")
            return

        if not cfg:
            logger.error("Could not load org config")
            return

        org_ctx = OrgCtx(
            org_id=cfg["organization_id"],
            session_id=sess_id,
            system_prompt=system_prompt_override or cfg.get("system_prompt", INSTRUCTIONS_FALLBACK),
        )
        logger.info(f"Loaded configuration for Org: {org_ctx.org_id}, Session: {org_ctx.session_id}")

        # --- 3. Fetch MCP URLs & Build Tools ---
        livekit_tools = []
        try:
            # Fetch URLs from your backend
            mcp_resp = await self._client.get_livekit_mcp_urls(
                organization_id=org_ctx.org_id, 
                auth_token=ephemeral_api_key
            )
            # Expecting response format: {"urls": ["https://...", "https://..."]}
            mcp_urls = mcp_resp.get("urls", [])
            
            if mcp_urls:
                logger.info(f"Fetching tools from MCP URLs: {mcp_urls}")
                livekit_tools = await self._connect_and_build_tools(mcp_urls)
            else:
                logger.info("No MCP URLs found for this organization.")
                
        except Exception as e:
            logger.error(f"Error setting up MCP tools: {e}")

        # --- 4. Initialize Plugins ---
        stt = deepgram.STT(model="nova-2-general", language="en")
        vad = silero.VAD.load()

        tts = None
        azure_key = os.getenv("AZURE_SPEECH_KEY")
        azure_region = os.getenv("AZURE_SPEECH_REGION")
        if azure_key and azure_region:
            tts = azure.TTS(
                speech_key=azure_key,
                speech_region=azure_region,
                voice="en-NG-AbeoNeural"
            )
        else:
            logger.warning("Azure credentials not found, TTS might be disabled or default.")

        llm = openai.LLM(model="gpt-4o-mini")

        # --- 5. Define Agent ---
        # We pass the dynamically built tools here
        agent = Agent(
            instructions=org_ctx.system_prompt,
        )

        # --- 6. Create & Start Session ---
        mcp_servers = []
        for tool_url in livekit_tools or []:
            mcp_servers.append(mcp.MCPServerHTTP(url=tool_url))


        session = AgentSession(
            stt=stt,
            llm=llm,
            tts=tts,
            vad=vad,
            mcp_servers = [mcp.MCPServerHTTP(url=u ) for u in livekit_tools]
        )

        # Send welcome message via text topic when user joins
        def on_participant_connected(participant):
            async def send_welcome():
                await ctx.room.local_participant.send_text(WELCOME_MESSAGE, topic="lk.chat")
            asyncio.create_task(send_welcome())
        
        ctx.room.on("participant_connected", on_participant_connected)

        # Start the voice session
        await session.start(room=ctx.room, agent=agent)
        
        # Optional: Have the voice agent speak the welcome message
        session.generate_reply(instructions=f"Say exactly: {WELCOME_MESSAGE}")

        
        logger.info("Agent session started")

        # --- 7. Cleanup Handler ---
        async def shutdown_handler(_):
            logger.info("Shutting down...")
            # 1. Close MCP Connections
            if self._mcp_exit_stack:
                await self._mcp_exit_stack.aclose()
            
            # 2. End Backend Session
            try:
                await self._client.end_session(sess_id)
            except Exception as e:
                logger.debug("Error ending session: %s", e)

            # 3. Upload Transcript
            try:
                if hasattr(session, "history"):
                    hist = session.history.to_dict() # Verify .to_dict() exists in your version
                    await self._client.upload_transcript(hist, prefix=sess_id)
            except Exception as e:
                logger.debug("Error uploading transcript: %s", e)

        ctx.add_shutdown_callback(shutdown_handler)

    def prewarm(self, proc: JobProcess):
        proc.userdata["vad"] = silero.VAD.load()

if __name__ == "__main__":
    manager = ModernKaliAgentService()
    cli.run_app(WorkerOptions(entrypoint_fnc=manager.entrypoint, prewarm_fnc=manager.prewarm))