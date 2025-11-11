<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

// --- State for Header (Missing from original script) ---
const greeting = ref("Good Morning");
const listening = ref(false);

function toggleListening() {
  listening.value = !listening.value;
  // Add logic here to start/stop voice recognition
}

// --- KPIs ---
type Kpi = {
  id: string;
  title: string;
  value: number;
  prev: number;
  delta: number;
  type?: "number" | "percent" | "ms" | "hours";
  variant?: "gradient" | "plain";
  sparkline?: number[];
  accent?: string;
  goodDirection?: "up" | "down";
  baseline?: string;
  deltaUnit?: string;
};

const kpis = reactive<Kpi[]>([
  { id: "interactions", title: "AI Interactions", value: 328, prev: 290, delta: 13.1, type: "number", variant: "plain", sparkline: [180, 210, 250, 230, 260, 305, 328], accent: "text-purple-100", goodDirection: "up", baseline: "vs yesterday 290", deltaUnit: "%" },
  { id: "automation", title: "Automation Time Saved", value: 2.8, prev: 2.3, delta: 22.0, type: "hours", variant: "plain", sparkline: [1.4, 1.6, 1.9, 2.1, 2.3, 2.5, 2.8], accent: "text-purple-300", goodDirection: "up", baseline: "vs last week avg 2.3h", deltaUnit: "%" },
  { id: "latency", title: "Avg Response Latency", value: 420, prev: 445, delta: -5.6, type: "ms", variant: "plain", sparkline: [510, 505, 480, 470, 451, 438, 420], accent: "text-pink-300", goodDirection: "down", baseline: "vs last week 445ms", deltaUnit: "%" },
]);

function isFavorable(kpi: Kpi) {
  const desired = kpi.goodDirection ?? "up";
  return desired === "up" ? kpi.delta >= 0 : kpi.delta <= 0;
}

function deltaPillClasses(kpi: Kpi) {
  const base = "border border-white/10";
  if (kpi.delta === 0)
    return `${base} bg-slate-500/15 text-slate-200`;
  return isFavorable(kpi)
    ? `${base} bg-emerald-500/15 text-emerald-200`
    : `${base} bg-rose-500/15 text-rose-200`;
}

function deltaIcon(kpi: Kpi) {
  if (kpi.delta === 0)
    return "tabler-arrows-diff";
  return isFavorable(kpi) ? "tabler-trending-up" : "tabler-trending-down";
}

function deltaText(kpi: Kpi) {
  if (kpi.delta === 0)
    return `0${kpi.deltaUnit ?? "%"}`;
  const sign = kpi.delta > 0 ? "+" : "-";
  const magnitude = Math.abs(kpi.delta);
  const precision = magnitude >= 10 ? 0 : 1;
  const formatted = magnitude.toFixed(precision).replace(/\.0$/, "");
  return `${sign}${formatted}${kpi.deltaUnit ?? "%"}`;
}

function formatValue(kpi: Kpi) {
  switch (kpi.type) {
    case "percent":
      return `${kpi.value.toFixed(0)}%`;
    case "ms":
      return `${kpi.value.toLocaleString()} ms`;
    case "hours":
      return `${kpi.value.toFixed(1)}h`;
    default:
      return kpi.value.toLocaleString();
  }
}

function baselineLabel(kpi: Kpi) {
  if (kpi.baseline)
    return kpi.baseline;
  if (kpi.type === "percent")
    return `vs previous ${kpi.prev}%`;
  if (kpi.type === "ms")
    return `vs previous ${kpi.prev} ms`;
  if (kpi.type === "hours")
    return `vs previous ${kpi.prev}h`;
  return `vs previous ${kpi.prev}`;
}

function sparkPath(points: number[]) {
  if (!points.length)
    return "";
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  return points
    .map((point, index) => {
      const x = points.length === 1 ? 0 : (index / (points.length - 1)) * 100;
      const y = 40 - ((point - min) / span) * 40;
      const command = index === 0 ? "M" : "L";
      return `${command}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

// --- Quick Actions ---
// Note: Quick Actions data is defined but not used in the provided template.
type QuickAction = {
  id: string;
  title: string;
  description: string;
  icon: string;
  primary?: boolean;
};

const quickActions = reactive<QuickAction[]>([
  {
    id: "send-digest",
    title: "Send morning digest",
    description: "Push the compiled brief to the leadership Slack channel.",
    icon: "tabler-send",
    primary: true,
  },
  {
    id: "prep-brief",
    title: "Prep investor notes",
    description: "Draft bullet recap from last night's emails and CRM.",
    icon: "tabler-notes",
  },
  {
    id: "reschedule",
    title: "Reschedule afternoon stand-up",
    description: "Offer alternate slots to the team and confirm automatically.",
    icon: "tabler-calendar-cog",
  },
  {
    id: "voice-reminder",
    title: "Set voice reminder",
    description: "Ping you if no reply from Alex within 1 hour.",
    icon: "tabler-bell-ringing",
  },
]);

const lastTriggeredAction = ref<string | null>(null);
function triggerAction(action: QuickAction) {
  lastTriggeredAction.value = action.title;
}

type UrgentItem = {
  id: string | number;
  type: "call" | "meeting" | "task" | "alert";
  title: string;
  desc: string;
  time: string;
  icon: string;
  level: "critical" | "high" | "medium";
  action?: string;
};

const urgentBase = reactive<UrgentItem[]>([
  { id: 1, type: "call", title: "Incoming call: Sarah", desc: "Personal call - ringing (15s)", time: "Now", icon: "tabler-phone-call", level: "critical", action: "Answer" },
  { id: 2, type: "meeting", title: "Product strategy meeting", desc: "Starts in 5 min - Boardroom or Zoom", time: "5m", icon: "tabler-calendar-event", level: "high", action: "Join" },
  { id: 3, type: "task", title: "Finalize investor deck", desc: "High priority - due today at 6 PM", time: "Due 6h", icon: "tabler-presentation", level: "high" },
]);

const acknowledged = ref<string[]>([]);
function isAck(id: string | number) {
  return acknowledged.value.includes(String(id));
}

const urgentItems = computed<UrgentItem[]>(() => [...urgentBase]);

function acknowledge(id: string | number) {
  const key = String(id);
  if (!acknowledged.value.includes(key))
    acknowledged.value.push(key);
}

function acknowledgeAll() {
  if (!urgentItems.value.length) {
    acknowledged.value = [];
    return;
  }
  acknowledged.value = urgentItems.value.map(item => String(item.id));
}

// --- Activity Events ---
type ActivityEvent = {
  id: string;
  plugin: string;
  title: string;
  time: string;
  type: string;
  severity: "info" | "high" | "medium";
  icon: string;
};

// This section was corrupted. I've repaired it.
const eventLog = reactive<ActivityEvent[]>([
  {
    id: "evt-3", // This ID was missing
    plugin: "CRM Insights",
    title: "Lead score spiked for Nova Labs",
    time: "12m ago",
    type: "Alert",
    severity: "high",
    icon: "tabler-alert-circle",
  },
  {
    id: "evt-4",
    plugin: "Voice Notes",
    title: "Transcript cleaned for Monday stand-up",
    time: "20m ago",
    type: "Transcription",
    severity: "info",
    icon: "tabler-notes",
  },
  // You can add evt-1 and evt-2 here if you have them
]);

const eventFilterPlugin = ref("All");

const pluginNames = computed(() => ["All", ...new Set(eventLog.map(event => event.plugin))]);

const filteredEvents = computed(() => {
  const target = eventFilterPlugin.value;
  if (target === "All")
    return eventLog;
  return eventLog.filter(event => event.plugin === target);
});

type FeedMode = "events" | "urgent";
const activeFeed = ref<FeedMode>("events");
const feedTabs: Array<{ value: FeedMode; label: string; icon: string }> = [
  { value: "events", label: "Live Events", icon: "tabler-activity" },
  { value: "urgent", label: "Urgent Info", icon: "tabler-alert-triangle" },
];

// --- onMounted Hook ---
onMounted(() => {
  const hour = new Date().getHours();
  greeting.value = hour < 12 ? "Good Morning" : hour < 18 ? "Good Afternoon" : "Good Evening";
});
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <main class="dashboard-root mx-auto w-full max-w-[1650px] flex-1 px-3 py-4 sm:px-6">
      <div class="dashboard-top-row mb-6 grid gap-4 lg:grid-cols-12">
        <div class="card border bg-gradient-to-br from-purple-800/30 via-purple-900/20 to-fuchsia-900/20 shadow-sm backdrop-blur lg:col-span-4">
          <div class="card-body gap-4">
            <div class="flex items-start justify-between">
              <div>
                <h1 class="text-xl font-semibold tracking-tight">
                  {{ greeting }}, <span class="text-transparent bg-gradient-to-r from-purple-300 to-fuchsia-300 bg-clip-text">Enoch</span>
                </h1>
                <p class="mt-1 text-sm opacity-70">
                  Your AI cockpit is synced & ready.
                </p>
              </div>
              <button class="btn btn-sm gap-2 border-purple-500/40 bg-purple-600/20 text-purple-200 hover:bg-purple-600/30" @click="toggleListening">
                <Icon
                  v-if="listening"
                  :name="listening ? 'tabler-wave-sine' : 'tabler-microphone'"
                  class="animate-pulse"
                />
                <Icon v-else name="tabler-microphone" />
                <span>{{ listening ? 'Listening...' : 'Speak' }}</span>
              </button>
            </div>
            <div class="grid gap-3 sm:grid-cols-2">
              <div class="rounded-xl border border-purple-500/30 bg-purple-900/10 p-3 text-xs">
                <p class="uppercase tracking-wide opacity-60">
                  Context Memory
                </p>
                <p class="mt-1 font-semibold">
                  Active
                </p>
              </div>
              <div class="rounded-xl border border-fuchsia-500/30 bg-fuchsia-900/10 p-3 text-xs">
                <p class="uppercase tracking-wide opacity-60">
                  Latency
                </p>
                <p class="mt-1 font-semibold">
                  ~420ms
                </p>
              </div>
            </div>
            <div class="text-xs opacity-60">
              Tip: Say "Summarize my morning inputs" to get a cross-channel brief.
            </div>
          </div>
        </div>

        <div class="lg:col-span-8 kpi-grid">
          <div
            v-for="k in kpis"
            :key="k.id"
            class="relative flex flex-col overflow-hidden rounded-[26px] p-4 md:p-5 lg:p-6 2xl:p-7 shadow-sm ring-1 ring-white/5 transition backdrop-blur"
            :class="[
              k.variant === 'gradient'
                ? 'bg-gradient-to-br from-purple-600 via-fuchsia-600 to-indigo-600 text-white kpi-gradient'
                : 'bg-base-200/20 hover:bg-base-200/30',
            ]"
          >
            <div v-if="k.variant === 'gradient'" class="pointer-events-none absolute inset-0 opacity-40">
              <div class="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-fuchsia-400/20 blur-2xl" />
              <div class="absolute left-1/3 top-1/2 h-32 w-32 -translate-x-1/2 -translate-y-1/2 rounded-full bg-purple-300/10 blur-2xl" />
            </div>
            <div class="relative z-10 flex h-full flex-col gap-2">
              <div class="flex items-start gap-2">
                <h3 class="text-[13px] font-medium tracking-wide uppercase opacity-80 leading-tight line-clamp-2 pr-1">
                  {{ k.title }}
                </h3>
                <span
                  class="kpi-delta ml-auto inline-flex items-center gap-0.5 rounded-full px-2 py-1 text-[10px] font-medium leading-none backdrop-blur shrink-0"
                  :class="deltaPillClasses(k)"
                >
                  <Icon :name="deltaIcon(k)" class="inline size-3" />
                  {{ deltaText(k) }}
                </span>
              </div>
              <div class="flex flex-1 items-end justify-between gap-2">
                <div>
                  <div class="kpi-value font-semibold tracking-tight" :class="k.variant === 'gradient' ? 'text-white' : k.accent">
                    {{ formatValue(k) }}
                  </div>
                  <div class="mt-1 text-[11px] opacity-60">
                    {{ baselineLabel(k) }}
                  </div>
                </div>
                <div v-if="k.sparkline" class="sparkline relative h-14 w-20 sm:h-16 sm:w-24">
                  <svg viewBox="0 0 100 40" class="absolute inset-0 h-full w-full overflow-visible">
                    <defs>
                      <linearGradient
                        :id="`grad-${k.id}`"
                        x1="0%"
                        y1="0%"
                        x2="0%"
                        y2="100%"
                      >
                        <stop
                          offset="0%"
                          stop-color="#a855f7"
                          stop-opacity="0.8"
                        />
                        <stop
                          offset="100%"
                          stop-color="#a855f7"
                          stop-opacity="0"
                        />
                      </linearGradient>
                    </defs>
                    <path
                      :d="sparkPath(k.sparkline)"
                      fill="none"
                      stroke="#c084fc"
                      stroke-width="2"
                      stroke-linejoin="round"
                      stroke-linecap="round"
                    />
                    <path :d="`${sparkPath(k.sparkline)} L100 40 L0 40 Z`" :fill="`url(#grad-${k.id})`" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div class="inline-flex items-center rounded-full border border-white/10 bg-base-100/10 p-1">
          <button
            v-for="tab in feedTabs"
            :key="tab.value"
            type="button"
            class="flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide transition"
            :class="activeFeed === tab.value
              ? 'bg-purple-500/30 text-purple-100'
              : 'text-slate-300 hover:bg-base-100/30'"
            @click="activeFeed = tab.value"
          >
            <Icon :name="tab.icon" class="text-sm" />
            <span>{{ tab.label }}</span>
          </button>
        </div>
        <p class="text-[11px] uppercase tracking-wide opacity-60 md:text-xs">
          {{ activeFeed === 'events' ? 'Realtime stream of assistant activity.' : 'High-priority items needing attention.' }}
        </p>
      </div>

      <div class="dashboard-grid grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        <section class="card dashboard-card h-full border shadow-sm bg-base-200/10 backdrop-blur xl:col-span-2">
          <div class="card-body gap-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div class="flex items-center gap-2">
                <Icon
                  :name="activeFeed === 'events' ? 'tabler-activity' : 'tabler-alert-triangle'"
                  :class="activeFeed === 'events' ? 'text-purple-300' : 'text-amber-400'"
                />
                <h2 class="font-semibold">
                  {{ activeFeed === 'events' ? 'Live Events' : 'Urgent Info' }}
                </h2>
              </div>
              <div class="flex items-center gap-2">
                <template v-if="activeFeed === 'events'">
                  <select v-model="eventFilterPlugin" class="select select-xs w-32 bg-base-300/40">
                    <option v-for="p in pluginNames" :key="p">
                      {{ p }}
                    </option>
                  </select>
                </template>
                <template v-else>
                  <button
                    class="btn btn-xs btn-outline"
                    :disabled="acknowledged.length === urgentItems.length"
                    @click="acknowledgeAll"
                  >
                    Acknowledge All
                  </button>
                </template>
              </div>
            </div>

            <ul
              v-if="activeFeed === 'events'"
              class="custom-scroll space-y-3 max-h-[340px] overflow-auto pr-1"
            >
              <li
                v-for="e in filteredEvents"
                :key="e.id"
                class="flex items-start gap-3 rounded-xl border border-base-200/40 bg-base-100/20 p-3 text-sm"
              >
                <div class="rounded-lg bg-base-300/40 p-2">
                  <Icon :name="e.icon" class="text-purple-300" />
                </div>
                <div class="flex-1 min-w-0">
                  <p class="font-medium truncate">
                    {{ e.title }}
                  </p>
                  <p class="mt-0.5 text-xs opacity-60">
                    {{ e.plugin }} - {{ e.time }}
                  </p>
                </div>
                <span class="badge badge-ghost badge-xs" :class="{ 'badge-error': e.severity === 'high', 'badge-info': e.severity === 'info' }">{{ e.type }}</span>
              </li>
            </ul>

            <template v-else>
              <ul class="custom-scroll space-y-3 max-h-[300px] overflow-auto pr-1">
                <li
                  v-for="u in urgentItems"
                  :key="u.id"
                  class="relative flex items-start gap-3 rounded-xl border border-base-200/40 bg-base-100/20 p-3 text-sm transition"
                  :class="[
                    isAck(u.id) ? 'opacity-40' : '',
                    u.level === 'critical' ? 'ring-1 ring-rose-500/40 animate-pulse' : '',
                    u.level === 'high' ? 'ring-1 ring-amber-500/30' : '',
                  ]"
                >
                  <div
                    class="flex items-center justify-center rounded-lg p-2"
                    :class="u.level === 'critical'
                      ? 'bg-rose-500/20 text-rose-300'
                      : u.level === 'high'
                        ? 'bg-amber-500/15 text-amber-300'
                        : 'bg-base-300/40 text-purple-300'"
                  >
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
                        v-if="u.action && !isAck(u.id)"
                        class="btn btn-ghost btn-xs"
                        @click="acknowledge(u.id)"
                      >
                        {{ u.action }}
                      </button>
                      <button
                        v-if="!isAck(u.id)"
                        class="btn btn-outline btn-xs"
                        @click="acknowledge(u.id)"
                      >
                        Acknowledge
                      </button>
                      <span v-else class="badge badge-ghost badge-xs">Done</span>
                    </div>
                  </div>
                  <div v-if="u.level === 'critical' && !isAck(u.id)" class="pointer-events-none absolute inset-0 rounded-xl ring-1 ring-rose-400/40 [animation:pulse_2s_ease-in-out_infinite]" />
                </li>
              </ul>
              <p v-if="!urgentItems.length" class="text-xs opacity-50">
                No urgent items right now. You're all clear.
              </p>
            </template>
          </div>
        </section>

        <section class="card dashboard-card h-full border shadow-sm bg-base-200/10 backdrop-blur xl:col-span-1">
          <div class="card-body gap-4">
            <div class="flex items-center justify-between">
              <h2 class="font-semibold flex items-center gap-2">
                <Icon name="tabler-bolt" class="text-amber-300" /> Quick Actions
              </h2>
              <span v-if="lastTriggeredAction" class="text-[11px] uppercase tracking-wide opacity-60">
                Last: {{ lastTriggeredAction }}
              </span>
            </div>
            <div class="space-y-2">
              <button
                v-for="action in quickActions"
                :key="action.id"
                type="button"
                class="flex w-full items-center gap-3 rounded-xl border p-3 text-left text-sm transition hover:translate-x-0.5"
                :class="action.primary
                  ? 'border-purple-500/40 bg-purple-600/20 text-purple-100 hover:border-purple-400/60 hover:bg-purple-600/30'
                  : 'border-base-200/40 bg-base-100/15 text-slate-100 hover:border-purple-400/40 hover:bg-base-100/25'"
                @click="triggerAction(action)"
              >
                <span class="flex size-10 items-center justify-center rounded-lg bg-base-300/40">
                  <Icon :name="action.icon" class="text-lg text-purple-200" />
                </span>
                <span class="flex-1">
                  <span class="block font-medium leading-tight">
                    {{ action.title }}
                  </span>
                  <span class="mt-0.5 block text-xs opacity-60">
                    {{ action.description }}
                  </span>
                </span>
                <Icon name="tabler-arrow-up-right" class="text-base opacity-60" />
              </button>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* Your component styles go here */
/* A few styles to make the kpi-grid and dashboard-grid responsive */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.25rem; /* 20px */
}

.dashboard-card {
  border-color: rgba(255, 255, 255, 0.07);
}

/* Custom scrollbar for lists */
.custom-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.3) transparent;
}
.custom-scroll::-webkit-scrollbar {
  width: 6px;
}
.custom-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scroll::-webkit-scrollbar-thumb {
  background-color: rgba(148, 163, 184, 0.3);
  border-radius: 20px;
  border: 3px solid transparent;
}
</style>
