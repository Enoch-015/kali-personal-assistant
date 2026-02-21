import type { RemoteParticipant, RemoteTrack, RemoteTrackPublication } from "livekit-client";

import { Room, RoomEvent, Track } from "livekit-client";

export type LiveKitOptions = {
  onTrackSubscribed?: (track: RemoteTrack, participant: RemoteParticipant) => void;
  onTrackUnsubscribed?: (track: RemoteTrack, participant: RemoteParticipant) => void;
  onParticipantConnected?: (participant: RemoteParticipant) => void;
  onParticipantDisconnected?: (participant: RemoteParticipant) => void;
  onDisconnected?: () => void;
  onDataReceived?: (data: Uint8Array, participant?: RemoteParticipant) => void;
};

export type ConnectResult = {
  success: boolean;
  roomName?: string;
  sessionId?: string;
  ephemeralKeyId?: string;
  error?: string;
};

export function useLiveKit(options: LiveKitOptions = {}) {
  const room = ref<Room | null>(null);
  const isConnected = ref(false);
  const isCameraEnabled = ref(false);
  const isMicEnabled = ref(false);
  const isScreenShareEnabled = ref(false);
  const connectionError = ref("");
  const participantCount = ref(0);
  const roomName = ref("");
  const sessionId = ref("");

  /**
   * Connect to a LiveKit room
   */
  async function connect(
    participantName: string,
    metadata: Record<string, unknown> = {},
  ): Promise<ConnectResult> {
    connectionError.value = "";

    try {
      // Call API to get token and room
      const response = await $fetch("/api/livekit/join", {
        method: "POST",
        body: {
          participantName,
          metadata: {
            role: "participant",
            userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "unknown",
            ...metadata,
          },
        },
      });

      const data = response as {
        roomName: string;
        token: string;
        url: string;
        sessionId: string;
        ephemeralKeyId?: string;
      };

      // Create and configure room optimized for Codespaces/remote environments
      const newRoom = new Room({
        // Adaptive streaming helps with variable network conditions
        adaptiveStream: true,
        // Dynacast reduces bandwidth by only sending video when subscribed
        dynacast: true,
        // Video codec preferences for better performance
        videoCaptureDefaults: {
          resolution: { width: 640, height: 480, frameRate: 24 }, // Lower resolution for smoother streaming
        },
        // Force TCP transport when UDP is blocked
        rtcConfig: {
          iceTransportPolicy: "all",
        },
      });

      // Set up event listeners
      newRoom.on(
        RoomEvent.TrackSubscribed,
        (track: RemoteTrack, _publication: RemoteTrackPublication, participant: RemoteParticipant) => {
          if (options.onTrackSubscribed) {
            options.onTrackSubscribed(track, participant);
          }
        },
      );

      newRoom.on(
        RoomEvent.TrackUnsubscribed,
        (track: RemoteTrack, _publication: RemoteTrackPublication, participant: RemoteParticipant) => {
          track.detach();
          if (options.onTrackUnsubscribed) {
            options.onTrackUnsubscribed(track, participant);
          }
        },
      );

      newRoom.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
        participantCount.value = newRoom.remoteParticipants.size;
        if (options.onParticipantConnected) {
          options.onParticipantConnected(participant);
        }
      });

      newRoom.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
        participantCount.value = newRoom.remoteParticipants.size;
        if (options.onParticipantDisconnected) {
          options.onParticipantDisconnected(participant);
        }
      });

      newRoom.on(RoomEvent.Disconnected, () => {
        isConnected.value = false;
        isCameraEnabled.value = false;
        isMicEnabled.value = false;
        isScreenShareEnabled.value = false;
        roomName.value = "";
        if (options.onDisconnected) {
          options.onDisconnected();
        }
      });

      newRoom.on(RoomEvent.DataReceived, (payload: Uint8Array, participant?: RemoteParticipant) => {
        if (options.onDataReceived) {
          options.onDataReceived(payload, participant);
        }
      });

      // Track local track state changes
      newRoom.on(RoomEvent.LocalTrackPublished, (publication) => {
        if (publication.source === Track.Source.Camera) {
          isCameraEnabled.value = true;
        }
        else if (publication.source === Track.Source.Microphone) {
          isMicEnabled.value = true;
        }
        else if (publication.source === Track.Source.ScreenShare) {
          isScreenShareEnabled.value = true;
        }
      });

      newRoom.on(RoomEvent.LocalTrackUnpublished, (publication) => {
        if (publication.source === Track.Source.Camera) {
          isCameraEnabled.value = false;
        }
        else if (publication.source === Track.Source.Microphone) {
          isMicEnabled.value = false;
        }
        else if (publication.source === Track.Source.ScreenShare) {
          isScreenShareEnabled.value = false;
        }
      });

      // Connect to room
      await newRoom.connect(data.url, data.token);
      room.value = newRoom;
      isConnected.value = true;
      roomName.value = data.roomName;
      sessionId.value = data.sessionId;
      participantCount.value = newRoom.remoteParticipants.size;

      // Notify session start
      try {
        await $fetch("/api/livekit/session/start", {
          method: "POST",
          body: { sessionId: data.sessionId },
        });
      }
      catch (error) {
        console.warn("Failed to notify session start:", error);
      }

      return {
        success: true,
        roomName: data.roomName,
        sessionId: data.sessionId,
        ephemeralKeyId: data.ephemeralKeyId,
      };
    }
    catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "Failed to connect to room";
      console.error("Failed to connect to LiveKit:", error);
      connectionError.value = errorMessage;
      return { success: false, error: errorMessage };
    }
  }

  /**
   * Disconnect from the current room
   */
  async function disconnect() {
    // End session tracking
    if (sessionId.value) {
      try {
        await $fetch("/api/livekit/session/end", {
          method: "POST",
          body: { sessionId: sessionId.value },
        });
      }
      catch (error) {
        console.warn("Failed to end session:", error);
      }
    }

    if (room.value) {
      room.value.disconnect();
      room.value = null;
    }
    isConnected.value = false;
    isCameraEnabled.value = false;
    isMicEnabled.value = false;
    isScreenShareEnabled.value = false;
    participantCount.value = 0;
    roomName.value = "";
    sessionId.value = "";
  }

  /**
   * Toggle camera on/off
   */
  async function toggleCamera(): Promise<boolean> {
    if (!room.value) {
      console.warn("Cannot toggle camera: not connected to room");
      return false;
    }

    try {
      const currentState = room.value.localParticipant.isCameraEnabled;
      // Don't pass any options - let LiveKit use defaults to avoid structuredClone issues
      await room.value.localParticipant.setCameraEnabled(!currentState);
      // State will be updated by LocalTrackPublished/Unpublished events
      return !currentState;
    }
    catch (error) {
      console.error("Failed to toggle camera:", error);
      return isCameraEnabled.value;
    }
  }

  /**
   * Toggle microphone on/off
   */
  async function toggleMicrophone(): Promise<boolean> {
    if (!room.value) {
      console.warn("Cannot toggle microphone: not connected to room");
      return false;
    }

    try {
      const currentState = room.value.localParticipant.isMicrophoneEnabled;
      // Don't pass any options - let LiveKit use defaults to avoid structuredClone issues
      await room.value.localParticipant.setMicrophoneEnabled(!currentState);
      // State will be updated by LocalTrackPublished/Unpublished events
      return !currentState;
    }
    catch (error) {
      console.error("Failed to toggle microphone:", error);
      return isMicEnabled.value;
    }
  }

  /**
   * Check if screen sharing is supported in this browser context
   */
  function isScreenShareSupported(): boolean {
    return !!(navigator.mediaDevices && "getDisplayMedia" in navigator.mediaDevices);
  }

  /**
   * Toggle screen share on/off
   */
  async function toggleScreenShare(): Promise<boolean> {
    if (!room.value) {
      console.warn("Cannot toggle screen share: not connected to room");
      return false;
    }

    if (!isScreenShareSupported()) {
      console.warn("Screen sharing is not supported in this browser context");
      return false;
    }

    try {
      const currentState = room.value.localParticipant.isScreenShareEnabled;
      await room.value.localParticipant.setScreenShareEnabled(!currentState);
      // State will be updated by LocalTrackPublished/Unpublished events
      return !currentState;
    }
    catch (error) {
      console.error("Failed to toggle screen share:", error);
      return isScreenShareEnabled.value;
    }
  }

  /**
   * Get local video track element
   */
  function getLocalVideoElement(): HTMLVideoElement | null {
    if (!room.value)
      return null;

    const publication = room.value.localParticipant.getTrackPublication(Track.Source.Camera);
    if (publication?.track) {
      return publication.track.attach() as HTMLVideoElement;
    }
    return null;
  }

  /**
   * Get local screen share track element
   */
  function getLocalScreenShareElement(): HTMLVideoElement | null {
    if (!room.value)
      return null;

    const publication = room.value.localParticipant.getTrackPublication(Track.Source.ScreenShare);
    if (publication?.track) {
      return publication.track.attach() as HTMLVideoElement;
    }
    return null;
  }

  /**
   * Get all remote participants
   */
  function getRemoteParticipants(): RemoteParticipant[] {
    if (!room.value)
      return [];
    return Array.from(room.value.remoteParticipants.values());
  }

  /**
   * Send data message to room
   */
  async function sendData(
    data: Uint8Array | string,
    options?: { reliable?: boolean; destinationIdentities?: string[] },
  ) {
    if (!room.value)
      return;

    const encoder = new TextEncoder();
    const dataToSend = typeof data === "string" ? encoder.encode(data) : data;

    await room.value.localParticipant.publishData(dataToSend, options);
  }

  /**
   * Update session with transcript URL
   */
  async function updateTranscript(transcriptUrl: string) {
    if (!sessionId.value)
      return;

    try {
      await $fetch(`/api/livekit/session/${sessionId.value}`, {
        method: "PATCH",
        body: { transcriptUrl },
      });
    }
    catch (error) {
      console.error("Failed to update transcript:", error);
    }
  }

  // Cleanup on unmount
  onUnmounted(() => {
    disconnect();
  });

  return {
    // State
    room,
    isConnected,
    isCameraEnabled,
    isMicEnabled,
    isScreenShareEnabled,
    connectionError,
    participantCount,
    roomName,
    sessionId,

    // Methods
    connect,
    disconnect,
    toggleCamera,
    toggleMicrophone,
    toggleScreenShare,
    isScreenShareSupported,
    getLocalVideoElement,
    getLocalScreenShareElement,
    getRemoteParticipants,
    sendData,
    updateTranscript,
  };
}
