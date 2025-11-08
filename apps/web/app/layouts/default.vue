<script setup lang="ts">
import { ref } from "vue";

const notifications = ref(3);

// Single source of truth for navigation items
const navItems = [
  { to: "/", icon: "tabler-home", label: "Voice Assistant" },
  { to: "/plugins", icon: "tabler-plug-connected", label: "Plugins" },
  { to: "/events", icon: "tabler-activity", label: "Events Feed" },
  { to: "#", icon: "tabler-chart-bar", label: "Analytics" },
  { to: "#", icon: "tabler-settings", label: "Settings" },
];

// Mobile sidebar state
const mobileNavOpen = ref(false);
function toggleMobileNav() {
  mobileNavOpen.value = !mobileNavOpen.value;
}
function closeMobileNav() {
  mobileNavOpen.value = false;
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
              src="/img/Gemini_Generated_Image_ehw9dgehw9dgehw9-removebg-preview11.png"
              alt="Kali-E Logo"
              width="34"
              height="34"
              class="w-8 h-8 object-contain"
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
</style>
