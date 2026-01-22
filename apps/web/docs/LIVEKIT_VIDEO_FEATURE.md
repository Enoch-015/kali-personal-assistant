# LiveKit Video Feature Documentation

This document describes the video/audio communication feature built using LiveKit for the Kali Personal Assistant.

## Overview

The video feature enables real-time video/audio communication between users and the AI assistant using [LiveKit](https://livekit.io/), an open-source WebRTC platform.

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   Browser/App   │◄───────►│  LiveKit Server │◄───────►│   AI Agent      │
│   (Client SDK)  │  WebRTC │  (Docker)       │  WebRTC │   (Future)      │
└─────────────────┘         └─────────────────┘         └─────────────────┘
        │                           │
        │                           │
        ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│  Nuxt Server    │◄───────►│  Token Gen/API  │
│  (API Routes)   │   HTTP  │  (livekit-sdk)  │
└─────────────────┘         └─────────────────┘
```

## Components

### 1. Server-Side (`apps/web/server/utils/livekit.ts`)

Handles:

- **Token generation** - Creates JWT tokens with room permissions
- **Room management** - Create, list, delete rooms via LiveKit API
- **Participant management** - List/remove participants

Key functions:

```typescript
buildLivekitToken(room, identity, metadata); // Generate access token
createRoom(roomName, options); // Create a room
listRooms(); // List active rooms
generateUniqueRoomName(); // Generate unique room names
```

### 2. Client-Side Composable (`apps/web/app/composables/use-livekit.ts`)

Vue composable providing reactive state and methods:

**State:**

- `isConnected` - Connection status
- `isCameraEnabled` - Camera on/off
- `isMicEnabled` - Microphone on/off
- `isScreenShareEnabled` - Screen share on/off
- `participantCount` - Number of remote participants
- `roomName` - Current room name
- `sessionId` - Current session ID

**Methods:**

- `connect(name, metadata)` - Join a room
- `disconnect()` - Leave the room
- `toggleCamera()` - Toggle camera on/off
- `toggleMicrophone()` - Toggle mic on/off
- `toggleScreenShare()` - Toggle screen sharing
- `isScreenShareSupported()` - Check if screen share is available

### 3. UI Component (`apps/web/app/components/video-room.vue`)

A complete video room component with:

- Join/leave UI
- Local video preview
- Remote participant videos
- Media control buttons (camera, mic, screen share)
- Participant count display

### 4. API Routes

| Route                        | Method | Description               |
| ---------------------------- | ------ | ------------------------- |
| `/api/livekit/join`          | POST   | Get token and join a room |
| `/api/livekit/session/start` | POST   | Notify session started    |
| `/api/livekit/session/end`   | POST   | Notify session ended      |

## Configuration

### Environment Variables (`apps/web/.env`)

```env
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
LIVEKIT_URL=wss://your-livekit-server:7880
LIVEKIT_SERVER_URL=http://localhost:7880  # For server-side API calls
```

### Docker Compose (`apps/ai/docker-compose.yaml`)

```yaml
livekit:
  image: livekit/livekit-server
  container_name: kali-livekit
  environment:
    # IMPORTANT: Must have space after colon!
    LIVEKIT_KEYS: "devkey: secret"
  ports:
    - "7880:7880" # WebSocket signaling
    - "7881:7881" # TCP fallback
    - "7882-7932:7882-7932/udp" # WebRTC media
  command: --dev --bind 0.0.0.0
```

## Usage

### Basic Usage

```vue
<template>
  <VideoRoom
    :participant-name="userName"
    :show-controls="true"
    @connected="onConnected"
    @disconnected="onDisconnected"
    @error="onError"
  />
</template>
```

### Programmatic Usage

```typescript
const {
  isConnected,
  isCameraEnabled,
  connect,
  disconnect,
  toggleCamera,
  toggleMicrophone,
} = useLiveKit({
  onTrackSubscribed: (track, participant) => {
    // Handle new track
  },
  onDisconnected: () => {
    // Handle disconnection
  },
});

// Join a room
await connect("John Doe", { role: "user" });

// Toggle camera
await toggleCamera();

// Leave
await disconnect();
```

## Track Types

LiveKit publishes different track types independently:

| Track Source       | Description                 | Can coexist |
| ------------------ | --------------------------- | ----------- |
| `Camera`           | Webcam video                | ✅ Yes      |
| `Microphone`       | Audio input                 | ✅ Yes      |
| `ScreenShare`      | Screen capture              | ✅ Yes      |
| `ScreenShareAudio` | Screen audio (desktop only) | ✅ Yes      |

**Note:** Camera and screen share can be active simultaneously. The AI agent would receive both feeds.

## Browser Compatibility

| Feature      | Desktop Chrome | Desktop Firefox | Desktop Safari | Mobile Chrome | Mobile Safari |
| ------------ | -------------- | --------------- | -------------- | ------------- | ------------- |
| Camera       | ✅             | ✅              | ✅             | ✅            | ✅            |
| Microphone   | ✅             | ✅              | ✅             | ✅            | ✅            |
| Screen Share | ✅             | ✅              | ✅             | ❌            | ❌            |

Screen sharing requires `getDisplayMedia` API which is **not available on mobile browsers**.

## Troubleshooting

### "Could not establish pc connection"

**Cause:** WebRTC peer connection failed (NAT/firewall issues)

**Solutions:**

1. Ensure ports 7880, 7881 are forwarded and public
2. Check if UDP ports (7882-7932) are accessible
3. For Codespaces: This is a known limitation due to UDP tunneling

### "structuredClone" Error

**Cause:** livekit-client v2.11.4+ has a bug with options cloning

**Solution:** Use livekit-client v2.11.0 or don't pass options to `setCameraEnabled()`

### "Could not parse keys"

**Cause:** LIVEKIT_KEYS format incorrect

**Solution:** Use format `"key: secret"` with space after colon

### Screen share not working

**Cause:** Browser doesn't support `getDisplayMedia`

**Solution:** Only available on desktop browsers. Use `isScreenShareSupported()` to check.

## Video Quality Settings

The current configuration optimizes for Codespaces/remote environments:

```typescript
videoCaptureDefaults: {
  resolution: { width: 640, height: 480, frameRate: 24 }
}
```

For production, you may want higher quality:

```typescript
videoCaptureDefaults: {
  resolution: { width: 1280, height: 720, frameRate: 30 }
}
```

## Security Considerations

1. **Token expiration** - Tokens should have short TTL (default: 24 hours)
2. **Room permissions** - Tokens grant specific room access only
3. **Metadata** - Don't include sensitive data in participant metadata
4. **HTTPS required** - WebRTC requires secure context

## Future Improvements

- [ ] Add TURN server for better NAT traversal
- [ ] Implement AI agent as LiveKit participant
- [ ] Add recording capability
- [ ] Add real-time transcription
- [ ] Support for multiple simultaneous rooms
- [ ] Quality adaptive controls for user

## Dependencies

- `livekit-client`: ^2.11.0 (client SDK)
- `livekit-server-sdk`: ^2.15.0 (server SDK for token generation)
- LiveKit Server: v1.9.11 (Docker image)

## References

- [LiveKit Documentation](https://docs.livekit.io/)
- [LiveKit JS Client SDK](https://docs.livekit.io/reference/client-sdk-js/)
- [LiveKit Server SDK](https://docs.livekit.io/reference/server-sdk-js/)
- [Screen Sharing Guide](https://docs.livekit.io/transport/media/screenshare/)
