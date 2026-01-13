<script setup lang="ts">
import { computed, ref } from "vue";

const notifications = ref(3);
const askWidgetOpen = ref(false);
const askRecording = ref(false);
const recordingLabel = computed(() => askRecording.value ? "Listening..." : "Ready to listen");

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
    <button
      class="fixed bottom-8 left-1/2 z-30 inline-flex -translate-x-1/2 transform items-center gap-2 rounded-full border border-purple-400/50 bg-gradient-to-r from-purple-600 via-fuchsia-500 to-indigo-500 px-4 py-2 text-xs md:text-sm font-semibold text-white shadow-lg transition hover:shadow-xl"
      aria-label="Open ask widget"
      @click="toggleAskWidget"
    >
      <Icon name="tabler-message-circle" class="text-base" />
      <span>Ask me anything</span>
    </button>
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
