<script setup lang="ts">
import type { RemoteParticipant, RemoteTrack } from "livekit-client";

const props = withDefaults(defineProps<{
  autoConnect?: boolean;
  participantName?: string;
  showControls?: boolean;
  compact?: boolean;
}>(), {
  autoConnect: false,
  participantName: "",
  showControls: true,
  compact: false,
});

const emit = defineEmits<{
  connected: [roomName: string, sessionId: string];
  disconnected: [];
  error: [error: string];
  participantJoined: [participant: RemoteParticipant];
  participantLeft: [participant: RemoteParticipant];
}>();

const localVideoContainer = ref<HTMLDivElement>();
const remoteVideosContainer = ref<HTMLDivElement>();
const nameInput = ref(props.participantName || "");
const isJoining = ref(false);

const {
  room,
  isConnected,
  isCameraEnabled,
  isMicEnabled,
  isScreenShareEnabled,
  participantCount,
  connectionError,
  roomName,
  sessionId,
  connect,
  disconnect,
  toggleCamera,
  toggleMicrophone,
  toggleScreenShare,
  getLocalVideoElement,
} = useLiveKit({
  onTrackSubscribed: (track: RemoteTrack, participant: RemoteParticipant) => {
    if (track.kind === "video") {
      const videoEl = track.attach();
      videoEl.style.width = "100%";
      videoEl.style.height = "100%";
      videoEl.style.objectFit = "cover";
      videoEl.style.borderRadius = "0.5rem";
      videoEl.classList.add("remote-video");

      // Create container for this participant
      const container = document.createElement("div");
      container.id = `participant-${participant.identity}`;
      container.className = "relative rounded-lg overflow-hidden bg-base-300 aspect-video";

      // Add participant label
      const label = document.createElement("div");
      label.className = "absolute top-2 left-2 bg-base-100/80 backdrop-blur px-2 py-1 rounded text-xs font-medium z-10";
      label.textContent = participant.name || participant.identity;

      container.appendChild(label);
      container.appendChild(videoEl);
      remoteVideosContainer.value?.appendChild(container);
    }
    else if (track.kind === "audio") {
      track.attach();
    }
  },
  onTrackUnsubscribed: (_track: RemoteTrack, participant: RemoteParticipant) => {
    const container = document.getElementById(`participant-${participant.identity}`);
    container?.remove();
  },
  onParticipantConnected: (participant: RemoteParticipant) => {
    emit("participantJoined", participant);
  },
  onParticipantDisconnected: (participant: RemoteParticipant) => {
    const container = document.getElementById(`participant-${participant.identity}`);
    container?.remove();
    emit("participantLeft", participant);
  },
  onDisconnected: () => {
    emit("disconnected");
  },
});

const canJoin = computed(() => nameInput.value.trim().length > 0);

async function handleJoin() {
  if (!canJoin.value || isJoining.value) return;

  isJoining.value = true;
  const result = await connect(nameInput.value.trim());
  isJoining.value = false;

  if (result.success && result.roomName && result.sessionId) {
    emit("connected", result.roomName, result.sessionId);
  }
  else {
    emit("error", result.error || "Failed to connect");
  }
}

async function handleDisconnect() {
  await disconnect();
  if (localVideoContainer.value) {
    localVideoContainer.value.innerHTML = "";
  }
  if (remoteVideosContainer.value) {
    remoteVideosContainer.value.innerHTML = "";
  }
}

async function handleToggleCamera() {
  const enabled = await toggleCamera();

  if (enabled && localVideoContainer.value) {
    // Wait a bit for track to be ready
    setTimeout(() => {
      const videoEl = getLocalVideoElement();
      if (videoEl && localVideoContainer.value) {
        videoEl.style.width = "100%";
        videoEl.style.height = "100%";
        videoEl.style.objectFit = "cover";
        videoEl.style.borderRadius = "0.5rem";
        localVideoContainer.value.innerHTML = "";
        localVideoContainer.value.appendChild(videoEl);
      }
    }, 100);
  }
  else if (!enabled && localVideoContainer.value) {
    localVideoContainer.value.innerHTML = "";
  }
}

// Auto-connect if props specify
onMounted(() => {
  if (props.autoConnect && props.participantName) {
    nameInput.value = props.participantName;
    handleJoin();
  }
});

watch(connectionError, (error) => {
  if (error) {
    emit("error", error);
  }
});

// Expose methods for parent components
defineExpose({
  connect,
  disconnect: handleDisconnect,
  toggleCamera: handleToggleCamera,
  toggleMicrophone,
  toggleScreenShare,
  isConnected,
  roomName,
  sessionId,
});
</script>

<template>
  <div class="video-room" :class="{ compact }">
    <!-- Join Screen -->
    <div v-if="!isConnected" class="join-screen">
      <div class="w-full max-w-md mx-auto space-y-4">
        <div class="text-center">
          <Icon name="tabler-video" class="text-5xl mb-3 opacity-60" />
          <h2 class="text-xl font-bold mb-1">
            Join Video Room
          </h2>
          <p class="text-sm opacity-70">
            Enter your name to start a video session
          </p>
        </div>

        <div class="form-control">
          <label class="label">
            <span class="label-text text-sm">Your Name</span>
          </label>
          <input
            v-model="nameInput"
            type="text"
            placeholder="Enter your name"
            class="input input-bordered w-full"
            :disabled="isJoining"
            @keyup.enter="handleJoin"
          >
        </div>

        <div v-if="connectionError" class="alert alert-error text-sm py-2">
          <Icon name="tabler-alert-circle" />
          <span>{{ connectionError }}</span>
        </div>

        <button
          class="btn btn-primary w-full"
          :disabled="!canJoin || isJoining"
          @click="handleJoin"
        >
          <Icon v-if="!isJoining" name="tabler-video" />
          <span v-else class="loading loading-spinner loading-sm" />
          <span>{{ isJoining ? "Joining..." : "Join Room" }}</span>
        </button>
      </div>
    </div>

    <!-- Video Room Active -->
    <div v-else class="room-active space-y-3">
      <!-- Header -->
      <div class="flex items-center justify-between p-3 bg-base-200 rounded-lg">
        <div class="flex items-center gap-3">
          <div class="w-2.5 h-2.5 bg-success rounded-full animate-pulse" />
          <div>
            <p class="font-semibold text-sm">
              {{ roomName }}
            </p>
            <p class="text-xs opacity-70">
              {{ participantCount + 1 }} participant{{ participantCount !== 0 ? "s" : "" }}
            </p>
          </div>
        </div>
        <button class="btn btn-error btn-sm gap-1" @click="handleDisconnect">
          <Icon name="tabler-phone-off" class="text-base" />
          <span class="hidden sm:inline">Leave</span>
        </button>
      </div>

      <!-- Video Grid -->
      <div
        class="grid gap-3"
        :class="participantCount > 0 ? 'md:grid-cols-2' : 'grid-cols-1'"
      >
        <!-- Local Video -->
        <div class="space-y-2">
          <div class="flex items-center justify-between px-1">
            <span class="text-xs font-medium">You</span>
            <span class="badge badge-success badge-xs">Local</span>
          </div>
          <div class="relative aspect-video bg-base-300 rounded-lg overflow-hidden">
            <div
              ref="localVideoContainer"
              class="w-full h-full"
            >
              <div v-if="!isCameraEnabled" class="w-full h-full flex items-center justify-center">
                <Icon name="tabler-video-off" class="text-5xl opacity-30" />
              </div>
            </div>
            <!-- Audio indicator -->
            <div
              v-if="isMicEnabled"
              class="absolute bottom-2 right-2 flex items-center gap-1 bg-base-100/80 backdrop-blur px-2 py-1 rounded text-xs"
            >
              <Icon name="tabler-microphone" class="text-success text-sm" />
            </div>
          </div>
        </div>

        <!-- Remote Videos -->
        <div v-if="participantCount > 0" class="space-y-2">
          <div class="flex items-center justify-between px-1">
            <span class="text-xs font-medium">Participants</span>
            <span class="badge badge-xs">{{ participantCount }}</span>
          </div>
          <div
            ref="remoteVideosContainer"
            class="grid gap-2 max-h-[500px] overflow-y-auto"
          />
        </div>
      </div>

      <!-- Controls -->
      <div v-if="showControls" class="controls flex flex-wrap gap-2 p-3 bg-base-200 rounded-lg">
        <button
          class="btn btn-sm flex-1 min-w-[100px] gap-1"
          :class="isCameraEnabled ? 'btn-error' : 'btn-ghost'"
          @click="handleToggleCamera"
        >
          <Icon :name="isCameraEnabled ? 'tabler-video' : 'tabler-video-off'" class="text-base" />
          <span class="hidden xs:inline">{{ isCameraEnabled ? "Camera On" : "Camera Off" }}</span>
        </button>

        <button
          class="btn btn-sm flex-1 min-w-[100px] gap-1"
          :class="isMicEnabled ? 'btn-error' : 'btn-ghost'"
          @click="toggleMicrophone"
        >
          <Icon :name="isMicEnabled ? 'tabler-microphone' : 'tabler-microphone-off'" class="text-base" />
          <span class="hidden xs:inline">{{ isMicEnabled ? "Mic On" : "Mic Off" }}</span>
        </button>

        <button
          class="btn btn-sm flex-1 min-w-[100px] gap-1"
          :class="isScreenShareEnabled ? 'btn-error' : 'btn-ghost'"
          @click="toggleScreenShare"
        >
          <Icon :name="isScreenShareEnabled ? 'tabler-screen-share' : 'tabler-screen-share-off'" class="text-base" />
          <span class="hidden xs:inline">{{ isScreenShareEnabled ? "Stop" : "Share" }}</span>
        </button>
      </div>

      <!-- Status Indicators -->
      <div class="flex flex-wrap gap-2 text-xs opacity-70 px-1">
        <div v-if="isCameraEnabled" class="flex items-center gap-1">
          <Icon name="tabler-video" class="text-success text-sm" />
          <span>Camera active</span>
        </div>
        <div v-if="isMicEnabled" class="flex items-center gap-1">
          <Icon name="tabler-microphone" class="text-success text-sm" />
          <span>Microphone active</span>
        </div>
        <div v-if="isScreenShareEnabled" class="flex items-center gap-1">
          <Icon name="tabler-screen-share" class="text-info text-sm" />
          <span>Screen sharing</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.video-room {
  width: 100%;
  min-height: 300px;
}

.video-room.compact {
  min-height: auto;
}

.join-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 1.5rem;
}

.compact .join-screen {
  min-height: 250px;
  padding: 1rem;
}

:deep(.remote-video) {
  object-fit: cover;
}

/* Smooth transitions */
.controls button {
  transition: all 0.2s ease;
}

.controls button:hover {
  transform: translateY(-1px);
}
</style>
