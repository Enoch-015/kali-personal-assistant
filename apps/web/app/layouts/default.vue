<script setup lang="ts">
import { computed, ref } from "vue";

const notifications = ref(3);
const askWidgetOpen = ref(false);
const askRecording = ref(false);
const recordingLabel = computed(() => askRecording.value ? "Listening..." : "Ready to listen");

// LiveKit widget state
const livekitWidgetOpen = ref(false);

// Use the LiveKit composable
const { isConnected: livekitConnected } = useLiveKit();

// Single source of truth for navigation items
const navItems = [
  { to: "/", icon: "tabler-home", label: "Voice Assistant" },
  { to: "/plugins", icon: "tabler-plug-connected", label: "Plugins" },
  { to: "/events", icon: "tabler-activity", label: "Events Feed" },
  { to: "/analysis", icon: "tabler-chart-bar", label: "Analytics" },
  { to: "/settings", icon: "tabler-settings", label: "Settings" },
];

// Mobile sidebar state
const mobileNavOpen = ref(false);
function toggleMobileNav() {
  mobileNavOpen.value = !mobileNavOpen.value;
}
function closeMobileNav() {
  mobileNavOpen.value = false;
}
function toggleAskWidget() {
  askWidgetOpen.value = !askWidgetOpen.value;
  if (!askWidgetOpen.value)
    askRecording.value = false;
}
function toggleRecording() {
  askRecording.value = !askRecording.value;
}

function toggleLivekitWidget() {
  livekitWidgetOpen.value = !livekitWidgetOpen.value;
}

function handleLivekitConnected(_roomName: string, _sessionId: string) {
  // Room connected - can add analytics or notifications here
}

function handleLivekitDisconnected() {
  // Widget stays open but shows join screen
}

function handleLivekitError(error: string) {
  console.error("LiveKit error:", error);
}
</script>

<template>
  <div class="flex min-h-screen flex-col bg-base-100 text-base-content">
    <!-- Global Navbar / transforms to compact bar + hamburger on very small screens -->
    <header class="sticky top-0 z-40 border-b border-base-200/30 bg-base-100/80 backdrop-blur supports-[backdrop-filter]:bg-base-100/60">
      <div class="mx-auto flex w-full max-w-7xl items-center gap-2 px-3 py-2 sm:px-4">
        <!-- Hamburger (shows below md) -->
        <button
          class="btn btn-ghost btn-sm md:hidden"
          aria-label="Menu"
          @click="toggleMobileNav"
        >
          <Icon :name="mobileNavOpen ? 'tabler-x' : 'tabler-menu-2'" />
        </button>
        <!-- Brand -->
        <NuxtLink to="/" class="flex items-center gap-2 shrink-0">
          <NuxtImg
            src="v1762635825/Gemini_Generated_Image_ehw9dgehw9dgehw9-removebg-preview11_igmqeu.png"
            alt="Kali-E Logo"
            width="40"
            height="40"
            class="w-9 h-9 sm:w-10 sm:h-10 object-contain select-none"
            loading="eager"
            decoding="async"
          />
          <span class="font-semibold tracking-tight text-sm sm:text-base hidden xs:inline">Kali‑E</span>
        </NuxtLink>

        <!-- Primary nav (desktop) -->
        <nav class="responsive-nav hidden md:flex items-center gap-1 overflow-x-auto no-scrollbar text-xs sm:text-[13px]" aria-label="Primary">
          <NuxtLink
            v-for="i in navItems"
            :key="i.label"
            :to="i.to"
            class="nav-btn"
            :aria-label="i.label"
            @click="closeMobileNav"
          >
            <Icon :name="i.icon" />
            <span class="nav-label">{{ i.label }}</span>
          </NuxtLink>
        </nav>

        <!-- Right side actions -->
        <div class="ml-auto flex items-center gap-2 shrink-0">
          <button class="btn btn-xs sm:btn-sm whitespace-nowrap hidden xs:inline-flex">
            <span class="hidden sm:inline">Try Premium</span>
            <span class="sm:hidden">Pro</span>
          </button>
          <button class="btn btn-circle btn-ghost btn-sm relative" aria-label="Notifications">
            <Icon name="tabler-bell" />
            <span class="badge badge-primary absolute -right-1 -top-1">{{ notifications }}</span>
          </button>
        </div>
      </div>
    </header>

    <!-- Mobile Sidebar (below md) -->
    <transition name="fade">
      <div
        v-if="mobileNavOpen"
        class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm md:hidden"
        role="button"
        aria-label="Close navigation overlay"
        @click="closeMobileNav"
      />
    </transition>
    <transition name="slide">
      <aside
        v-if="mobileNavOpen"
        class="fixed inset-y-0 left-0 z-50 w-60 max-w-[75%] bg-base-100 border-r border-base-200/40 md:hidden flex flex-col p-4 gap-4 shadow-lg"
        aria-label="Mobile navigation"
      >
        <div class="flex items-center justify-between">
          <NuxtLink
            to="/"
            class="flex items-center gap-2"
            @click="closeMobileNav"
          >
            <NuxtImg
              src="v1762635825/Gemini_Generated_Image_ehw9dgehw9dgehw9-removebg-preview11_igmqeu.png"
              alt="Kali-E Logo"
              width="40"
              height="40"
              class="w-9 h-9 sm:w-10 sm:h-10 object-contain select-none"
              loading="eager"
              decoding="async"
            />
            <span class="font-semibold tracking-tight">Kali‑E</span>
          </NuxtLink>
          <button
            class="btn btn-ghost btn-sm"
            aria-label="Close menu"
            @click="closeMobileNav"
          >
            <Icon name="tabler-x" />
          </button>
        </div>
        <nav class="flex flex-col gap-1 mt-2" aria-label="Mobile Primary">
          <NuxtLink
            v-for="i in navItems"
            :key="`${i.label}-mobile`"
            :to="i.to"
            class="mobile-nav-item"
            :aria-label="i.label"
            @click="closeMobileNav"
          >
            <Icon :name="i.icon" class="text-lg" />
            <span>{{ i.label }}</span>
          </NuxtLink>
        </nav>
        <div class="mt-auto flex flex-col gap-2 pt-4 border-t border-base-200/40">
          <button class="btn btn-sm btn-outline" @click="closeMobileNav">
            Try Premium
          </button>
          <button class="btn btn-sm btn-ghost" @click="closeMobileNav">
            Settings
          </button>
        </div>
      </aside>
    </transition>

    <main class="flex-1 min-w-0">
      <slot />
    </main>
    <ToastContainer />
    <transition name="fade">
      <div
        v-if="askWidgetOpen"
        class="fixed bottom-24 left-1/2 z-40 w-72 max-w-[calc(100vw-2rem)] -translate-x-1/2 transform rounded-2xl border border-white/10 bg-base-100/95 p-4 shadow-xl backdrop-blur"
      >
        <div class="mb-3 flex items-start justify-between gap-3">
          <div>
            <p class="text-sm font-semibold">
              Ask Me Anything
            </p>
            <p class="text-xs opacity-60">
              Kali-E is standing by.
            </p>
          </div>
          <button
            class="btn btn-ghost btn-xs"
            aria-label="Close ask widget"
            @click="toggleAskWidget"
          >
            <Icon name="tabler-x" />
          </button>
        </div>
        <div class="space-y-4">
          <div class="rounded-xl border border-white/10 bg-base-100/60 p-3 text-xs leading-relaxed">
            <p class="text-sm font-medium">
              {{ recordingLabel }}
            </p>
            <p class="mt-1 opacity-70">
              {{ askRecording ? "Speak clearly and Kali-E will transcribe in real time." : "Tap the mic to start a voice question." }}
            </p>
          </div>
          <div class="flex items-end justify-center gap-1">
            <span
              v-for="bar in 4"
              :key="bar"
              class="inline-block h-3 w-1 rounded-full bg-purple-400 transition-all duration-300"
              :class="askRecording ? `animate-wave-${bar}` : 'opacity-40'"
            />
          </div>
          <button
            class="btn btn-sm w-full gap-2"
            :class="askRecording ? 'btn-error' : 'btn-primary'"
            @click="toggleRecording"
          >
            <Icon :name="askRecording ? 'tabler-player-stop' : 'tabler-microphone'" class="text-base" />
            <span>{{ askRecording ? 'Stop Listening' : 'Start Listening' }}</span>
          </button>
          <p class="text-[11px] text-center uppercase tracking-wide opacity-60">
            Hold device close for best accuracy
          </p>
        </div>
      </div>
    </transition>

    <!-- LiveKit Video Widget -->
    <transition name="fade">
      <div
        v-if="livekitWidgetOpen"
        class="fixed bottom-24 right-4 z-40 w-80 max-w-[calc(100vw-2rem)] rounded-2xl border border-white/10 bg-base-100/95 shadow-xl backdrop-blur overflow-hidden"
      >
        <div class="flex items-center justify-between p-3 border-b border-base-200/40">
          <div class="flex items-center gap-2">
            <Icon name="tabler-video" class="text-lg text-purple-400" />
            <span class="text-sm font-semibold">Video Session</span>
            <span
              v-if="livekitConnected"
              class="inline-flex items-center gap-1 text-xs text-success"
            >
              <span class="w-2 h-2 bg-success rounded-full animate-pulse" />
              Connected
            </span>
          </div>
          <button
            class="btn btn-ghost btn-xs"
            aria-label="Close video widget"
            @click="toggleLivekitWidget"
          >
            <Icon name="tabler-x" />
          </button>
        </div>
        <VideoRoom
          :show-controls="true"
          @connected="handleLivekitConnected"
          @disconnected="handleLivekitDisconnected"
          @error="handleLivekitError"
        />
      </div>
    </transition>

    <!-- FAB Flower Speed Dial -->
    <div class="fab fab-flower fixed bottom-6 right-6 z-30">
      <!-- Main FAB trigger -->
      <div
        tabindex="0"
        role="button"
        class="btn btn-circle btn-lg bg-gradient-to-r from-purple-600 via-fuchsia-500 to-indigo-500 border-purple-400/50 text-white shadow-lg hover:shadow-xl"
      >
        <!-- Plus icon -->
        <svg
          aria-label="Open menu"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 16 16"
          fill="currentColor"
          class="size-6"
        >
          <path d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z" />
        </svg>
      </div>

      <!-- Video Session button -->
      <div class="tooltip tooltip-left" data-tip="Video Session">
        <button
          class="btn btn-circle btn-lg"
          :class="{ 'btn-success': livekitConnected }"
          aria-label="Toggle video session"
          @click="toggleLivekitWidget"
        >
          <!-- Video icon -->
          <svg
            aria-label="Video"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
            class="size-6"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z"
            />
          </svg>
        </button>
      </div>

      <!-- Ask Me Anything (Voice) button -->
      <div class="tooltip tooltip-left" data-tip="Ask Anything">
        <button
          class="btn btn-circle btn-lg"
          :class="askRecording ? 'btn-error' : ''"
          aria-label="Open ask widget"
          @click="toggleAskWidget"
        >
          <!-- Microphone icon -->
          <svg
            aria-label="Ask"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
            class="size-6"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z"
            />
          </svg>
        </button>
      </div>

      <!-- Notifications button -->
      <div class="tooltip" data-tip="Notifications">
        <button
          class="btn btn-circle btn-lg relative"
          aria-label="Notifications"
        >
          <!-- Bell icon -->
          <svg
            aria-label="Notifications"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
            class="size-6"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0"
            />
          </svg>
          <span v-if="notifications > 0" class="badge badge-primary badge-xs absolute -right-1 -top-1">{{ notifications }}</span>
        </button>
      </div>

      <!-- Settings button -->
      <div class="tooltip" data-tip="Settings">
        <NuxtLink
          to="/settings"
          class="btn btn-circle btn-lg"
          aria-label="Settings"
        >
          <!-- Settings/Cog icon -->
          <svg
            aria-label="Settings"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
            class="size-6"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
            />
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
            />
          </svg>
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Hide scrollbar for nav on Webkit & Firefox */
.no-scrollbar {
  scrollbar-width: none;
}
.no-scrollbar::-webkit-scrollbar {
  display: none;
}

/* Reusable button style for nav items; rely on Daisy but tighten spacing */
.nav-btn {
  /* mimic btn btn-ghost btn-xs spacing simplified for custom element */
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-weight: 500;
  font-size: 0.7rem; /* xs */
  padding: 0.35rem 0.5rem;
  border-radius: 0.5rem;
  background: transparent;
  border: 1px solid transparent;
  transition:
    background 120ms,
    color 120ms,
    border-color 120ms;
}
.nav-btn:hover {
  background: rgba(255, 255, 255, 0.05);
}
@media (min-width: 640px) {
  /* sm */
  .nav-btn {
    font-size: 0.8rem;
    padding: 0.45rem 0.75rem;
  }
}

/* Hide text labels below md to keep only icons */
.nav-label {
  display: none;
}
@media (min-width: 768px) {
  /* md */
  .nav-label {
    display: inline;
  }
}

/* When space is extremely constrained (<380px), keep only first 3 icons */
@media (max-width: 380px) {
  .responsive-nav a:nth-child(n + 4) {
    display: none;
  }
}

/* Slightly increase gap on large screens */
@media (min-width: 1280px) {
  .responsive-nav {
    gap: 0.35rem;
  }
}

/* Provide subtle hover ring for accessibility */
.responsive-nav a:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(168, 85, 247, 0.6);
}

/* Mobile sidebar links */
.mobile-nav-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.6rem 0.75rem;
  font-weight: 500;
  border-radius: 0.55rem;
  font-size: 0.85rem;
  transition:
    background 0.15s,
    color 0.15s;
}
.mobile-nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

/* Transitions */
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.25s ease;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(-100%);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 380px) {
  /* Make sidebar a bit narrower on ultra small devices */
  aside[aria-label="Mobile navigation"] {
    width: 11.5rem;
  }
}

@keyframes ask-wave {
  0%,
  100% {
    transform: scaleY(0.5);
    opacity: 0.5;
  }
  50% {
    transform: scaleY(1.2);
    opacity: 1;
  }
}

.animate-wave-1 {
  animation: ask-wave 1s ease-in-out infinite;
}

.animate-wave-2 {
  animation: ask-wave 1s ease-in-out infinite;
  animation-delay: 0.15s;
}

.animate-wave-3 {
  animation: ask-wave 1s ease-in-out infinite;
  animation-delay: 0.3s;
}

.animate-wave-4 {
  animation: ask-wave 1s ease-in-out infinite;
  animation-delay: 0.45s;
}
</style>
