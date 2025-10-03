<script setup lang="ts">
import { computed, reactive, ref } from "vue";

/*************************************************
 * Events + Urgent Activity Overview Page
 * Mirrors dashboard visual language (cards, gradients, pill metrics)
 * Provides: filters (plugin, severity, type), search, acknowledge flow
 *************************************************/

type EventSeverity = "low" | "normal" | "info" | "high" | "critical";
type EventType = "message" | "email" | "reminder" | "note" | "task" | "system";
type EventItem = { id: number; plugin: string; type: EventType; title: string; time: string; severity: EventSeverity; icon: string; acknowledged?: boolean; ts: number };
type UrgentItem = { id: string | number; type: "call" | "meeting" | "task" | "alert"; title: string; desc: string; time: string; icon: string; level: "critical" | "high" | "medium"; action?: string; ack?: boolean; ts: number };

// Demo seed (could be hydrated via API later)
const now = Date.now();
const events = reactive<EventItem[]>([
  { id: 1, plugin: "WhatsApp Sync", type: "message", title: "New message from Alex: “Ship status?”", time: "2m", severity: "normal", icon: "tabler-brand-whatsapp", ts: now - 2 * 60_000 },
  { id: 2, plugin: "Calendar Fusion", type: "reminder", title: "Design Review starts in 30m", time: "8m", severity: "high", icon: "tabler-calendar", ts: now - 8 * 60_000 },
  { id: 3, plugin: "Email Assistant", type: "email", title: "Draft prepared: Weekly performance summary", time: "21m", severity: "info", icon: "tabler-mail", ts: now - 21 * 60_000 },
  { id: 4, plugin: "Notes Intelligence", type: "note", title: "Auto summary generated: Investor Call", time: "31m", severity: "info", icon: "tabler-notes", ts: now - 31 * 60_000 },
  { id: 5, plugin: "Calendar Fusion", type: "reminder", title: "1:1 with Sarah rescheduled", time: "55m", severity: "low", icon: "tabler-calendar-event", ts: now - 55 * 60_000 },
  { id: 6, plugin: "Email Assistant", type: "system", title: "Bulk triage processed (24 mails)", time: "1h", severity: "normal", icon: "tabler-inbox", ts: now - 60 * 60_000 },
  { id: 7, plugin: "WhatsApp Sync", type: "message", title: "Reply queued (low network)", time: "1h 20m", severity: "info", icon: "tabler-clock-hour-3", ts: now - 80 * 60_000 },
  { id: 8, plugin: "Deep Focus Guard", type: "system", title: "Focus mode auto‑enabled", time: "2h", severity: "high", icon: "tabler-shield-lock", ts: now - 120 * 60_000 },
]);

const urgent = reactive<UrgentItem[]>([
  { id: "u1", type: "call", title: "Incoming Call: Sarah", desc: "Ringing (15s)", time: "Now", icon: "tabler-phone-call", level: "critical", action: "Answer", ts: now - 40_000 },
  { id: "u2", type: "meeting", title: "Product Strategy Meeting", desc: "Starts in 5 min", time: "5m", icon: "tabler-calendar-event", level: "high", action: "Join", ts: now - 5 * 60_000 },
  { id: "u3", type: "task", title: "Finalize Investor Deck", desc: "Due today 6 PM", time: "Due 6h", icon: "tabler-presentation", level: "high", ts: now - 30 * 60_000 },
]);

// Filters + search
const search = ref("");
const filterPlugin = ref("All");
const filterSeverity = ref("All");
const filterType = ref("All");

const pluginNames = computed(() => ["All", ...new Set(events.map(e => e.plugin))]);
const severities = ["All", "critical", "high", "info", "normal", "low"];
const types = computed(() => ["All", ...new Set(events.map(e => e.type))]);

const filteredEvents = computed(() => {
  let list = [...events];
  if (filterPlugin.value !== "All")
    list = list.filter(e => e.plugin === filterPlugin.value);
  if (filterSeverity.value !== "All")
    list = list.filter(e => e.severity === filterSeverity.value);
  if (filterType.value !== "All")
    list = list.filter(e => e.type === filterType.value);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    list = list.filter(e => e.title.toLowerCase().includes(q) || e.plugin.toLowerCase().includes(q));
  }
  return list.sort((a, b) => b.ts - a.ts);
});

// Summary metrics
const statTotal = computed(() => events.length);
const statHigh = computed(() => events.filter(e => e.severity === "high" || e.severity === "critical").length);
const statUnhandledUrgent = computed(() => urgent.filter(u => !u.ack).length);
const statPlugins = computed(() => new Set(events.map(e => e.plugin)).size);

// Distribution analytics (for insights panel)
const severityCounts = computed(() => {
  const init: Record<string, number> = { critical: 0, high: 0, info: 0, normal: 0, low: 0 };
  events.forEach((e) => {
    init[e.severity] = (init[e.severity] || 0) + 1;
  });
  return init;
});
const pluginCounts = computed(() => {
  const map: Record<string, number> = {};
  events.forEach((e) => {
    map[e.plugin] = (map[e.plugin] || 0) + 1;
  });
  return Object.entries(map).sort((a, b) => b[1] - a[1]);
});

// Group timeline into relative buckets (Now/Last Hour/Earlier Today)
type EventGroup = { label: string; items: EventItem[] };
const groupedEvents = computed<EventGroup[]>(() => {
  const nowTs = Date.now();
  const lastHourBoundary = nowTs - 60 * 60 * 1000;
  const recentBoundary = nowTs - 10 * 60 * 1000; // 'Just Now' window
  const groups: Record<"Just Now" | "Last Hour" | "Earlier Today", EventItem[]> = { "Just Now": [], "Last Hour": [], "Earlier Today": [] };
  filteredEvents.value.forEach((e) => {
    if (e.ts >= recentBoundary) {
      groups["Just Now"].push(e);
      return;
    }
    if (e.ts >= lastHourBoundary) {
      groups["Last Hour"].push(e);
      return;
    }
    groups["Earlier Today"].push(e);
  });
  return Object.entries(groups)
    .filter(([, items]) => items.length)
    .map(([label, items]) => ({ label, items }));
});

// Flatten groups into sequence entries for timeline component
type TimelineEntry = { kind: "group"; label: string } | { kind: "event"; event: EventItem; side: "start" | "end" };
const timelineEntries = computed<TimelineEntry[]>(() => {
  let toggle = false; // alternate sides for events only
  const out: TimelineEntry[] = [];
  groupedEvents.value.forEach((g) => {
    out.push({ kind: "group", label: g.label });
    g.items.forEach((ev) => {
      out.push({ kind: "event", event: ev, side: toggle ? "end" : "start" });
      toggle = !toggle;
    });
  });
  return out;
});

function acknowledgeUrgent(id: string | number) {
  const item = urgent.find(u => String(u.id) === String(id));
  if (item) {
    item.ack = true;
  }
}
function acknowledgeAllUrgent() {
  urgent.forEach((u) => {
    u.ack = true;
  });
}
function acknowledgeEvent(e: EventItem) {
  e.acknowledged = true;
}

function severityBadgeClass(s: EventSeverity) {
  switch (s) {
    case "critical": return "bg-rose-500/20 text-rose-300";
    case "high": return "bg-amber-500/20 text-amber-300";
    case "info": return "bg-sky-500/20 text-sky-300";
    case "normal": return "bg-base-300/30 text-base-content/70";
    case "low": return "bg-emerald-500/15 text-emerald-300";
    default: return "bg-base-300/30 text-base-content/70"; // fallback
  }
}
</script>

<template>
  <div class="events-root mx-auto w-full max-w-[1650px] px-3 py-6 sm:px-6">
    <!-- Heading -->
    <header class="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">
          Activity & Events
        </h1>
        <p class="mt-1 text-sm opacity-70">
          Unified feed of system activity, plugin events & urgent signals.
        </p>
      </div>
      <div class="flex gap-2 text-xs opacity-60">
        <span>{{ filteredEvents.length }} shown</span>
        <span>• {{ statHigh }} high</span>
        <span>• {{ statUnhandledUrgent }} urgent open</span>
      </div>
    </header>

    <!-- Top stats (reuse KPI cadence) -->
    <div class="grid gap-4 md:grid-cols-4 sm:grid-cols-2 mb-8">
      <div class="stat-tile">
        <p class="stat-label">
          Total Events
        </p>
        <p class="stat-value">
          {{ statTotal }}
        </p>
        <p class="stat-sub">
          Across {{ statPlugins }} plugins
        </p>
      </div>
      <div class="stat-tile">
        <p class="stat-label">
          High / Critical
        </p>
        <p class="stat-value text-amber-300">
          {{ statHigh }}
        </p>
        <p class="stat-sub">
          Needs attention
        </p>
      </div>
      <div class="stat-tile">
        <p class="stat-label">
          Open Urgent
        </p>
        <p class="stat-value text-rose-300">
          {{ statUnhandledUrgent }}
        </p>
        <p class="stat-sub">
          Active signals
        </p>
      </div>
      <div class="stat-tile">
        <p class="stat-label">
          Plugins Active
        </p>
        <p class="stat-value text-purple-200">
          {{ statPlugins }}
        </p>
        <p class="stat-sub">
          Source channels
        </p>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div class="flex flex-col gap-3 md:flex-row md:items-center md:gap-4 flex-1">
        <div class="relative flex-1 max-w-md">
          <Icon name="tabler-search" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-base opacity-60" />
          <input
            v-model="search"
            type="text"
            placeholder="Search events..."
            class="input input-sm w-full rounded-xl bg-base-200/30 pl-10"
          >
        </div>
        <div class="flex gap-2 flex-wrap">
          <select v-model="filterPlugin" class="select select-xs bg-base-200/30 min-w-40">
            <option v-for="p in pluginNames" :key="p">
              {{ p }}
            </option>
          </select>
          <select v-model="filterType" class="select select-xs bg-base-200/30 min-w-32">
            <option v-for="t in types" :key="t">
              {{ t }}
            </option>
          </select>
          <select v-model="filterSeverity" class="select select-xs bg-base-200/30 min-w-32">
            <option v-for="s in severities" :key="s">
              {{ s }}
            </option>
          </select>
        </div>
      </div>
      <div class="flex gap-2 self-start">
        <button class="btn btn-xs btn-outline" @click="search = ''; filterPlugin = 'All'; filterSeverity = 'All'; filterType = 'All'">
          Reset
        </button>
        <button
          class="btn btn-xs btn-primary"
          :disabled="!statUnhandledUrgent"
          @click="acknowledgeAllUrgent"
        >
          Ack All Urgent
        </button>
      </div>
    </div>

    <div class="grid gap-6 xl:grid-cols-12 auto-rows-[minmax(120px,auto)] layout-panels">
      <!-- Urgent panel (left) -->
      <section class="card col-span-12 xl:col-span-3 border shadow-sm bg-base-200/10 backdrop-blur sticky-panel">
        <div class="card-body gap-4">
          <div class="flex items-center justify-between">
            <h2 class="font-semibold flex items-center gap-2">
              <Icon name="tabler-alert-triangle" class="text-amber-400" /> Urgent Signals
            </h2>
            <button
              class="btn btn-xs btn-outline"
              :disabled="!statUnhandledUrgent"
              @click="acknowledgeAllUrgent"
            >
              Ack All
            </button>
          </div>
          <ul class="space-y-3 max-h-[360px] overflow-auto pr-1 custom-scroll">
            <li
              v-for="u in urgent"
              :key="u.id"
              class="relative flex items-start gap-3 rounded-xl border border-base-200/40 bg-base-100/20 p-3 text-sm transition"
              :class="[u.ack ? 'opacity-40' : '', u.level === 'critical' ? 'ring-1 ring-rose-500/40 animate-pulse' : '', u.level === 'high' ? 'ring-1 ring-amber-500/30' : '']"
            >
              <div class="rounded-lg p-2 flex items-center justify-center" :class="u.level === 'critical' ? 'bg-rose-500/20 text-rose-300' : u.level === 'high' ? 'bg-amber-500/15 text-amber-300' : 'bg-base-300/40 text-purple-300'">
                <Icon :name="u.icon" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-start justify-between gap-2">
                  <p class="font-medium leading-snug truncate">
                    {{ u.title }}
                  </p>
                  <span class="text-[10px] uppercase tracking-wide opacity-50">{{ u.time }}</span>
                </div>
                <p class="mt-0.5 text-xs opacity-60 line-clamp-2">
                  {{ u.desc }}
                </p>
                <div class="mt-2 flex items-center gap-2">
                  <button
                    v-if="u.action && !u.ack"
                    class="btn btn-ghost btn-xs"
                    @click="acknowledgeUrgent(u.id)"
                  >
                    {{ u.action }}
                  </button>
                  <button
                    v-if="!u.ack"
                    class="btn btn-outline btn-xs"
                    @click="acknowledgeUrgent(u.id)"
                  >
                    Ack
                  </button>
                  <span v-else class="badge badge-ghost badge-xs">Done</span>
                </div>
              </div>
              <div v-if="u.level === 'critical' && !u.ack" class="pointer-events-none absolute inset-0 rounded-xl ring-1 ring-rose-400/40 [animation:pulse_2s_ease-in-out_infinite]" />
            </li>
          </ul>
          <p v-if="!urgent.length" class="text-xs opacity-50">
            No urgent items.
          </p>
        </div>
      </section>

      <!-- Events timeline (center) using DaisyUI timeline component -->
      <section class="card col-span-12 xl:col-span-6 border shadow-sm bg-base-200/10 backdrop-blur timeline-panel">
        <div class="card-body gap-5">
          <div class="flex items-start justify-between">
            <h2 class="font-semibold flex items-start gap-2">
              <Icon name="tabler-activity" class="text-purple-300" /> Timeline
            </h2>
            <span class="text-xs opacity-60">Newest first</span>
          </div>
          <ul class="timeline timeline-vertical timeline-events max-h-[680px] overflow-auto pr-1 custom-scroll">
            <li
              v-for="(entry, idx) in timelineEntries"
              :key="entry.kind === 'group' ? `g-${entry.label}` : entry.event!.id"
              class="timeline-row"
            >
              <hr v-if="idx > 0">
              <!-- Group heading marker -->
              <template v-if="entry.kind === 'group'">
                <div class="timeline-middle">
                  <div class="group-pin h-6 w-6 rounded-full bg-purple-500/30 flex items-center justify-center ring-2 ring-purple-400/60 text-[10px] font-semibold text-purple-100">
                    {{ entry.label[0] }}
                  </div>
                </div>
                <div class="timeline-start timeline-box group-label-box">
                  <span class="group-label text-[11px] font-semibold uppercase tracking-wide text-purple-200/90">{{ entry.label }}</span>
                </div>
                <hr>
              </template>
              <!-- Event item -->
              <template v-else>
                <!-- Start side box if side === start -->
                <div v-if="entry.side === 'start'" class="timeline-start timeline-box event-box bg-base-100/10 border border-base-200/40 backdrop-blur">
                  <div class="flex flex-wrap items-center gap-2">
                    <p class="font-medium leading-snug truncate flex-1">
                      {{ entry.event!.title }}
                    </p>
                    <span class="badge badge-ghost badge-xs" :class="severityBadgeClass(entry.event!.severity)">{{ entry.event!.severity }}</span>
                    <span class="badge badge-ghost badge-xs">{{ entry.event!.type }}</span>
                  </div>
                  <p class="mt-0.5 text-[11px] opacity-60">
                    {{ entry.event!.plugin }} • {{ entry.event!.time }}
                  </p>
                  <div class="mt-2 flex items-center gap-2">
                    <button
                      v-if="!entry.event!.acknowledged"
                      class="btn btn-ghost btn-xs"
                      @click="acknowledgeEvent(entry.event!)"
                    >
                      Ack
                    </button>
                    <span v-else class="badge badge-ghost badge-xs">Done</span>
                  </div>
                </div>
                <div class="timeline-middle">
                  <div class="icon-wrapper rounded-lg bg-base-300/40 p-2 flex items-center justify-center">
                    <Icon :name="entry.event!.icon" class="text-purple-300" />
                  </div>
                </div>
                <div v-if="entry.side === 'end'" class="timeline-end timeline-box event-box bg-base-100/10 border border-base-200/40 backdrop-blur">
                  <div class="flex flex-wrap items-center gap-2">
                    <p class="font-medium leading-snug truncate flex-1">
                      {{ entry.event!.title }}
                    </p>
                    <span class="badge badge-ghost badge-xs" :class="severityBadgeClass(entry.event!.severity)">{{ entry.event!.severity }}</span>
                    <span class="badge badge-ghost badge-xs">{{ entry.event!.type }}</span>
                  </div>
                  <p class="mt-0.5 text-[11px] opacity-60">
                    {{ entry.event!.plugin }} • {{ entry.event!.time }}
                  </p>
                  <div class="mt-2 flex items-center gap-2">
                    <button
                      v-if="!entry.event!.acknowledged"
                      class="btn btn-ghost btn-xs"
                      @click="acknowledgeEvent(entry.event!)"
                    >
                      Ack
                    </button>
                    <span v-else class="badge badge-ghost badge-xs">Done</span>
                  </div>
                </div>
                <hr v-if="idx < timelineEntries.length - 1">
              </template>
            </li>
          </ul>
          <p v-if="!filteredEvents.length" class="text-xs opacity-60">
            No events match filters.
          </p>
        </div>
      </section>

      <!-- Insights (right) -->
      <section class="card col-span-12 xl:col-span-3 border shadow-sm bg-base-200/10 backdrop-blur insights-panel">
        <div class="card-body gap-5">
          <div>
            <h2 class="font-semibold mb-1">
              Insights
            </h2>
            <p class="text-xs opacity-60">
              Distribution & recent sources
            </p>
          </div>
          <div>
            <h3 class="text-[11px] uppercase tracking-wide opacity-60 mb-2">
              Severity Mix
            </h3>
            <ul class="space-y-1 text-xs">
              <li
                v-for="(count, key) in severityCounts"
                :key="key"
                class="flex items-center gap-2"
              >
                <span class="w-16 capitalize opacity-70">{{ key }}</span>
                <div class="h-2 flex-1 rounded-full bg-base-300/30 overflow-hidden">
                  <div
                    class="h-full severity-bar"
                    :class="key"
                    :style="{ width: `${count / statTotal * 100 || 0}%` }"
                  />
                </div>
                <span class="tabular-nums w-6 text-right">{{ count }}</span>
              </li>
            </ul>
          </div>
          <div>
            <h3 class="text-[11px] uppercase tracking-wide opacity-60 mb-2">
              Top Plugins
            </h3>
            <ul class="space-y-2 text-xs">
              <li
                v-for="([name, count], i) in pluginCounts.slice(0, 5)"
                :key="name"
                class="flex items-center gap-2"
              >
                <span class="inline-flex h-5 w-5 items-center justify-center rounded-md bg-base-300/40 text-[10px] font-medium">{{ i + 1 }}</span>
                <span class="flex-1 truncate">{{ name }}</span>
                <span class="badge badge-ghost badge-xs">{{ count }}</span>
              </li>
            </ul>
            <p v-if="pluginCounts.length > 5" class="mt-2 text-[10px] opacity-50">
              +{{ pluginCounts.length - 5 }} more
            </p>
          </div>
          <div class="text-[10px] opacity-50 leading-relaxed">
            Tip: Filter by severity to focus on risk. Acknowledge events you have reviewed to clear noise.
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.custom-scroll::-webkit-scrollbar {
  width: 6px;
}
.custom-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scroll::-webkit-scrollbar-thumb {
  background: linear-gradient(to bottom, rgba(139, 92, 246, 0.4), rgba(217, 70, 239, 0.3));
  border-radius: 4px;
}
.custom-scroll::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(to bottom, rgba(139, 92, 246, 0.7), rgba(217, 70, 239, 0.6));
}

.stat-tile {
  position: relative;
  overflow: hidden;
  border-radius: 1.3rem;
  padding: 1rem 1.1rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(6px);
}
.stat-tile:before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 70% 30%, rgba(8, 8, 8, 0.18));
  opacity: 0.9;
  pointer-events: none;
}
.stat-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  opacity: 0.65;
  font-weight: 500;
}
.stat-value {
  font-size: clamp(1.35rem, 1.1rem + 0.6vw, 1.9rem);
  font-weight: 600;
  line-height: 1.1;
  margin-top: 0.2rem;
}
.stat-sub {
  font-size: 11px;
  opacity: 0.5;
  margin-top: 0.35rem;
}

/* Filters responsiveness */
@media (max-width: 520px) {
  .filters select {
    flex: 1 1 45%;
  }
}
@media (max-width: 380px) {
  .filters select {
    flex: 1 1 100%;
  }
  .filters .flex-1.max-w-md {
    max-width: 100%;
  }
}

/* Density adjustments for very small screens */
@media (max-width: 370px) {
  .stat-tile {
    padding: 0.85rem 0.9rem;
  }
  .stat-value {
    font-size: 1.25rem;
  }
  .stat-label {
    font-size: 10px;
  }
}

/* Layout panel enhancements */
.layout-panels {
  align-items: start;
}
.sticky-panel {
  position: sticky;
  top: 5.5rem;
  height: fit-content;
}
@media (max-width: 1279px) {
  .sticky-panel {
    position: static;
  }
}

/* Timeline overrides */
.timeline-events .event-box {
  border-radius: 1rem;
  padding: 0.9rem 0.95rem;
}
.timeline-events .timeline-row .group-label {
  letter-spacing: 0.08em;
}
.timeline-events .timeline-row .group-pin {
  box-shadow:
    0 0 0 2px rgba(255, 255, 255, 0.07),
    0 0 12px -2px rgba(168, 85, 247, 0.5);
}
.timeline-events .icon-wrapper {
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.03);
}
.timeline-events {
  scrollbar-width: thin;
}
/* Timeline layout normalization (even left/right distribution) */
/* Restore default inner padding so timeline stays within card bounds */
.timeline-panel .card-body {
  padding-left: 1.25rem;
  padding-right: 1.25rem;
}
@media (min-width: 640px) {
  .timeline-panel .card-body {
    padding-left: 1.4rem;
    padding-right: 1.4rem;
  }
}
@media (min-width: 1024px) {
  .timeline-panel .card-body {
    padding-left: 1.75rem;
    padding-right: 1.75rem;
  }
}
/* Remove previous negative offset; keep vertical line centered */
.timeline-events {
  margin-left: 0;
  padding-left: 0;
}
/* Let DaisyUI handle hr positioning; no manual left shift */
.timeline-events .timeline-row > hr {
  margin-left: 0;
}
/* Natural width boxes with a max for readability */
.timeline-events .event-box {
  width: auto;
  max-width: 480px;
}
@media (min-width: 1400px) {
  .timeline-events .event-box {
    max-width: 520px;
  }
}
@media (max-width: 640px) {
  .timeline-events .event-box {
    max-width: 100%;
  }
}
@media (max-width: 520px) {
  .timeline-events .event-box {
    padding: 0.75rem 0.8rem;
  }
}
/* Subtle background for group label row */
.timeline-events .group-label-box {
  background: linear-gradient(to right, rgba(168, 85, 247, 0.15), rgba(168, 85, 247, 0.05));
}

.insights-panel {
  position: sticky;
  top: 5.5rem;
  height: fit-content;
}
@media (max-width: 1279px) {
  .insights-panel {
    position: static;
  }
}

/* Severity bar colors */
.severity-bar.critical {
  background: radial-gradient(circle at 30% 40%, rgba(244, 63, 94, 0.8), rgba(244, 63, 94, 0.3));
}
.severity-bar.high {
  background: radial-gradient(circle at 30% 40%, rgba(245, 158, 11, 0.8), rgba(245, 158, 11, 0.25));
}
.severity-bar.info {
  background: radial-gradient(circle at 30% 40%, rgba(56, 189, 248, 0.7), rgba(56, 189, 248, 0.25));
}
.severity-bar.normal {
  background: linear-gradient(to right, rgba(255, 255, 255, 0.35), rgba(255, 255, 255, 0.05));
}
.severity-bar.low {
  background: radial-gradient(circle at 30% 40%, rgba(16, 185, 129, 0.7), rgba(16, 185, 129, 0.25));
}

@media (max-width: 1024px) {
  .layout-panels {
    grid-template-columns: 1fr;
  }
  .timeline-panel {
    order: 2;
  }
  .insights-panel {
    order: 3;
  }
  .sticky-panel {
    order: 1;
  }
}

@media (min-width: 2100px) {
  .timeline-panel .timeline-scroll {
    max-height: 860px;
  }
}
</style>
