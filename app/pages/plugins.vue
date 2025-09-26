<script setup lang="ts">
import { computed, reactive, ref } from "vue";

type VoiceCommand = { text: string };
type PluginMeta = {
  id: string;
  name: string;
  category: string;
  author: string;
  desc: string;
  icon: string;
  version: string;
  downloads: number;
  rating: number;
  installed: boolean;
  color: string;
  voice: VoiceCommand[];
};

// Seed plugin catalogue (extendable)
const plugins = reactive<PluginMeta[]>([
  {
    id: "whatsapp",
    name: "WhatsApp Integration",
    category: "Communication",
    author: "Kali‑E Team",
    desc: "Send and receive WhatsApp messages through voice commands",
    icon: "tabler-brand-whatsapp",
    version: "2.1.0",
    downloads: 12500,
    rating: 4.8,
    installed: true,
    color: "bg-gradient-to-br from-emerald-800/40 to-emerald-600/20",
    voice: [
      { text: "Send WhatsApp message" },
      { text: "Check WhatsApp messages" },
      { text: "Reply last chat" },
      { text: "Send status update" },
    ],
  },
  {
    id: "calendar",
    name: "Calendar Assistant",
    category: "Productivity",
    author: "Productivity Labs",
    desc: "Manage your calendar events and schedule meetings with voice",
    icon: "tabler-calendar-stats",
    version: "1.8.2",
    downloads: 8900,
    rating: 4.6,
    installed: true,
    color: "bg-gradient-to-br from-indigo-800/40 to-indigo-600/20",
    voice: [
      { text: "Schedule meeting" },
      { text: "Check calendar" },
      { text: "Move my 3pm" },
      { text: "Free time tomorrow?" },
    ],
  },
  {
    id: "email",
    name: "Email Manager",
    category: "Communication",
    author: "Mail Solutions",
    desc: "Compose, send, and manage emails using natural voice commands",
    icon: "tabler-mail-cog",
    version: "3.0.1",
    downloads: 6700,
    rating: 4.4,
    installed: false,
    color: "bg-gradient-to-br from-purple-800/40 to-fuchsia-600/20",
    voice: [
      { text: "Send email" },
      { text: "Check inbox" },
      { text: "Summarize unread" },
      { text: "Draft follow up" },
    ],
  },
  {
    id: "notes",
    name: "Notes Intelligence",
    category: "Productivity",
    author: "NLP Labs",
    desc: "Semantic clustering + summarization for long-form meeting notes",
    icon: "tabler-notes",
    version: "0.9.7",
    downloads: 5400,
    rating: 4.7,
    installed: true,
    color: "bg-gradient-to-br from-fuchsia-700/40 to-pink-500/10",
    voice: [
      { text: "Summarize notes" },
      { text: "Find action items" },
      { text: "Cluster project ideas" },
    ],
  },
  {
    id: "voicepack",
    name: "Voice Pack Pro",
    category: "Utility",
    author: "Audio Forge",
    desc: "Premium voice synthesis & adaptive tone modulation for replies",
    icon: "tabler-microphone-2",
    version: "1.2.4",
    downloads: 3100,
    rating: 4.5,
    installed: false,
    color: "bg-gradient-to-br from-rose-700/30 to-orange-500/10",
    voice: [
      { text: "Change voice" },
      { text: "Use calming tone" },
      { text: "Narrate summary" },
    ],
  },
  {
    id: "focus",
    name: "Deep Focus Guard",
    category: "Utility",
    author: "Flow Systems",
    desc: "Blocks low value interruptions & batches notifications intelligently",
    icon: "tabler-shield-lock",
    version: "0.5.3",
    downloads: 2100,
    rating: 4.3,
    installed: false,
    color: "bg-gradient-to-br from-teal-700/30 to-teal-500/10",
    voice: [
      { text: "Enter focus mode" },
      { text: "Pause focus mode" },
      { text: "What did I miss?" },
    ],
  },
]);

const activeTab = ref<"marketplace" | "installed">("marketplace");
const search = ref("");
const category = ref("All");

const categories = computed(() => ["All", ...new Set(plugins.map(p => p.category))]);

const filtered = computed(() => {
  let list = [...plugins];
  if (activeTab.value === "installed")
    list = list.filter(p => p.installed);
  if (category.value !== "All")
    list = list.filter(p => p.category === category.value);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    list = list.filter(p => p.name.toLowerCase().includes(q) || p.desc.toLowerCase().includes(q));
  }
  return list;
});

function toggleInstall(p: PluginMeta) {
  p.installed = !p.installed;
}

function formatDownloads(n: number) {
  if (n >= 1000)
    return `${(n / 1000).toFixed(1).replace(/\.0$/, "")}k`;
  return String(n);
}
</script>

<template>
  <div class="plugins-page mx-auto w-full max-w-[1650px] px-3 py-6 sm:px-6">
    <header class="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">
          Plugins Marketplace
        </h1>
        <p class="mt-1 text-sm opacity-70">
          Extend Kali‑E with powerful integrations
        </p>
      </div>
      <div class="flex items-center gap-2 self-start rounded-xl border border-base-200/40 bg-base-200/10 p-1 text-sm">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'marketplace' }"
          @click="activeTab = 'marketplace'"
        >
          Marketplace
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'installed' }"
          @click="activeTab = 'installed'"
        >
          Installed ({{ plugins.filter(p => p.installed).length }})
        </button>
      </div>
    </header>

    <div class="mb-5 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div class="flex flex-1 items-center gap-3">
        <div class="relative flex-1 max-w-md">
          <Icon name="tabler-search" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-base opacity-60" />
          <input
            v-model="search"
            type="text"
            placeholder="Search plugins..."
            class="input input-sm w-full rounded-xl bg-base-200/30 pl-10"
          >
        </div>
        <div class="hidden md:flex items-center gap-1 text-xs opacity-60">
          <span>{{ filtered.length }} result(s)</span>
        </div>
      </div>
      <div class="flex w-full gap-2 overflow-auto md:w-auto category-scroll pb-1">
        <button
          v-for="c in categories"
          :key="c"
          class="category-chip"
          :class="{ active: category === c }"
          @click="category = c"
        >
          {{ c }} ({{ c === 'All' ? plugins.length : plugins.filter(p => p.category === c).length }})
        </button>
      </div>
    </div>

    <TransitionGroup
      name="fade"
      tag="div"
      class="grid gap-6 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4"
    >
      <div
        v-for="p in filtered"
        :key="p.id"
        class="plugin-card group relative flex flex-col overflow-hidden rounded-2xl border border-base-200/40 bg-base-100/5 p-5 shadow-sm transition hover:border-purple-500/40"
        :class="p.color"
      >
        <div class="mb-4 flex items-start justify-between gap-4">
          <div class="flex items-center gap-3">
            <div class="rounded-xl bg-base-100/40 p-3 ring-1 ring-white/10">
              <Icon :name="p.icon" class="text-lg text-purple-200" />
            </div>
            <div>
              <p class="font-medium leading-tight">
                {{ p.name }}
              </p>
              <p class="text-[11px] uppercase tracking-wide opacity-60">
                by {{ p.author }}
              </p>
            </div>
          </div>
          <span v-if="p.installed" class="installed-badge">Installed</span>
        </div>
        <p class="mb-4 line-clamp-3 text-sm opacity-70">
          {{ p.desc }}
        </p>

        <div class="mb-4 flex flex-wrap items-center gap-4 text-xs font-medium opacity-80">
          <span class="flex items-center gap-1"><Icon name="tabler-star" class="text-amber-400" /> {{ p.rating.toFixed(1) }}</span>
          <span class="flex items-center gap-1"><Icon name="tabler-download" class="opacity-70" /> {{ formatDownloads(p.downloads) }}</span>
          <span class="rounded-md bg-base-300/40 px-2 py-0.5 text-[10px] font-medium">v{{ p.version }}</span>
        </div>

        <div class="voice-section mb-5">
          <p class="mb-2 text-xs font-semibold uppercase tracking-wide opacity-70 flex items-center gap-1">
            <Icon name="tabler-microphone" class="opacity-70" /> Voice Commands:
          </p>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="v in p.voice.slice(0, 3)"
              :key="v.text"
              class="command-pill"
            >"{{ v.text }}"</span>
            <span
              v-if="p.voice.length > 3"
              class="command-pill more"
            >+{{ p.voice.length - 3 }} more</span>
          </div>
        </div>

        <div class="mt-auto">
          <button
            v-if="p.installed"
            class="btn btn-sm btn-outline w-full gap-2"
          >
            <Icon name="tabler-settings" /> Configure
          </button>
          <button
            v-else
            class="btn btn-sm btn-primary w-full gap-2"
            @click="toggleInstall(p)"
          >
            <Icon name="tabler-download" /> Install
          </button>
        </div>
      </div>
    </TransitionGroup>

    <p v-if="!filtered.length" class="mt-16 text-center text-sm opacity-50">
      No plugins match your filters.
    </p>
  </div>
</template>

<style scoped>
.plugins-page {
  --chip-bg: rgba(255, 255, 255, 0.06);
}
.tab-btn {
  border-radius: 0.65rem;
  padding: 0.4rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  opacity: 0.7;
  transition: 0.25s;
  line-height: 1.1;
}
.tab-btn:hover {
  opacity: 1;
}
.tab-btn.active {
  background: rgba(168, 85, 247, 0.25);
  color: #e9d5ff;
  opacity: 1;
}
.category-scroll {
  scrollbar-width: none;
}
.category-scroll::-webkit-scrollbar {
  display: none;
}
.category-chip {
  white-space: nowrap;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  padding: 0.45rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 9999px;
  transition: 0.25s;
}
.category-chip:hover {
  border-color: rgba(168, 85, 247, 0.4);
  background: rgba(255, 255, 255, 0.07);
}
.category-chip.active {
  background: rgba(147, 51, 234, 0.35);
  border-color: rgba(168, 85, 247, 0.4);
  color: #e9d5ff;
}
.plugin-card {
  backdrop-filter: blur(6px);
  min-height: 320px;
}
.installed-badge {
  border-radius: 9999px;
  background: rgba(16, 185, 129, 0.15);
  padding: 0.45rem 0.75rem;
  font-size: 10px;
  font-weight: 500;
  color: rgb(110 231 183);
}
.command-pill {
  border-radius: 0.45rem;
  background: rgba(255, 255, 255, 0.08);
  padding: 0.25rem 0.5rem;
  font-size: 10px;
  line-height: 1.1;
  font-weight: 500;
}
.command-pill.more {
  background: rgba(255, 255, 255, 0.05);
}
.voice-section {
  --shadow: 0 0 0 1px rgba(255, 255, 255, 0.03);
}
.fade-move,
.fade-enter-active,
.fade-leave-active {
  transition: all 0.35s cubic-bezier(0.4, 0.2, 0.2, 1);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: scale(0.96);
}

/* Tiny devices adjustments */
@media (max-width: 480px) {
  .plugins-page {
    padding-left: 0.75rem;
    padding-right: 0.75rem;
  }
  .plugin-card {
    padding: 1rem 1rem 1.1rem;
  }
  .plugin-card p.line-clamp-3 {
    line-clamp: 4;
    -webkit-line-clamp: 4;
  }
  .voice-section {
    margin-bottom: 1rem;
  }
  .command-pill {
    font-size: 9px;
  }
}
@media (max-width: 380px) {
  .tab-btn {
    padding: 0.55rem 0.7rem;
    font-size: 11px;
  }
  .category-chip {
    padding: 0.45rem 0.7rem;
    font-size: 11px;
  }
  .plugin-card {
    min-height: 300px;
  }
}
@media (max-width: 340px) {
  /* ultra small (old iPhone SE) */
  .tab-btn {
    font-size: 10px;
    padding: 0.45rem 0.55rem;
  }
  .category-chip {
    font-size: 10px;
    padding: 0.4rem 0.55rem;
  }
  .plugin-card {
    padding: 0.85rem 0.85rem 1rem;
  }
  .plugin-card .command-pill {
    font-size: 9px;
  }
}
@media (min-width: 1800px) {
  .plugins-page .grid {
    grid-template-columns: repeat(5, 1fr);
  }
}
@media (min-width: 2100px) {
  .plugins-page .grid {
    grid-template-columns: repeat(6, 1fr);
  }
}
</style>
