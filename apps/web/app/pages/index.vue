<script setup lang="ts">
// Kali-E Dashboard redesigned
import { computed, onMounted, reactive, ref } from "vue";

// Greeting logic
const greeting = ref("Hello");
onMounted(() => {
  const hour = new Date().getHours();
  greeting.value = hour < 12 ? "Good Morning" : hour < 18 ? "Good Afternoon" : "Good Evening";
});

// Core KPI snapshot (Kali-E contextual metrics)
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
  {
    id: "interactions",
    title: "AI Interactions",
    value: 328,
    prev: 290,
    delta: 13.1,
    type: "number",
    variant: "plain",
    sparkline: [180, 210, 250, 230, 260, 305, 328],
    accent: "text-purple-100",
    goodDirection: "up",
    baseline: "vs yesterday 290",
    deltaUnit: "%",
  },
  {
    id: "automation",
    title: "Automation Time Saved",
    value: 2.8, // hours today
    prev: 2.3,
    delta: 22.0,
    type: "hours",
    variant: "plain",
    sparkline: [1.4, 1.6, 1.9, 2.1, 2.3, 2.5, 2.8],
    accent: "text-purple-300",
    goodDirection: "up",
    baseline: "vs last week avg 2.3h",
    deltaUnit: "%",
  },
  {
    id: "latency",
    title: "Avg Response Latency",
    value: 420, // ms
    prev: 445,
    delta: -5.6, // percent improvement (lower better)
    type: "ms",
    variant: "plain",
    sparkline: [510, 505, 480, 470, 451, 438, 420],
    accent: "text-pink-300",
    goodDirection: "down",
    baseline: "vs last week 445ms",
    deltaUnit: "%",
  },
  {
    id: "continuity",
    title: "Continuity Score",
    value: 92, // percent
    prev: 89,
    delta: 3.0,
    type: "percent",
    variant: "plain",
    sparkline: [84, 85, 86, 87, 90, 91, 92],
    accent: "text-purple-300",
    goodDirection: "up",
    baseline: "vs last week 89%",
    deltaUnit: "%",
  },
]);

function formatValue(k: Kpi) {
  const baseFmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: k.type === "number" ? 0 : 1 });
  switch (k.type) {
    case "hours":
      return `${baseFmt.format(k.value)}h`;
    case "ms":
      return `${Math.round(k.value)}ms`;
    case "percent":
      return `${Math.round(k.value)}%`;
    default:
      return baseFmt.format(k.value);
  }
}
function baselineLabel(k: Kpi) {
  if (k.baseline)
    return k.baseline;
  return `vs previous ${k.prev}`;
}
function deltaPillClasses(k: Kpi) {
  const good = (k.goodDirection === "up" && k.delta >= 0) || (k.goodDirection === "down" && k.delta < 0);
  return good ? "bg-emerald-500/15 text-emerald-300" : "bg-rose-500/15 text-rose-300";
}
function deltaIcon(k: Kpi) {
  const good = (k.goodDirection === "up" && k.delta >= 0) || (k.goodDirection === "down" && k.delta < 0);
  return good ? "tabler-arrow-up-right" : "tabler-arrow-down-right";
}
function deltaText(k: Kpi) {
  return `${k.delta > 0 ? "+" : ""}${k.delta}${k.deltaUnit || ""}`;
}

// Generate a simple sparkline path (0..100 width, 0..40 height coordinate system)
function sparkPath(points: number[]) {
  if (!points.length)
    return "";
  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = max - min || 1;
  return points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * 100;
      const y = 40 - ((p - min) / range) * 30 - 5;
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

// Notes Preview
const notes = reactive([
  { id: 1, title: "Q4 Launch Plan", snippet: "Finalize feature freeze & marketing assets..." },
  { id: 2, title: "Investor Call", snippet: "Talking points: growth curve, retention..." },
  { id: 3, title: "Voice UX Ideas", snippet: "Ambient wake word, contextual follow-ups..." },
]);

// Task Board
const tasks = reactive([
  { id: 1, title: "Reply to client feedback", priority: "High", done: false },
  { id: 2, title: "Sync calendar w/ Notion", priority: "Med", done: true },
  { id: 3, title: "Draft weekly summary", priority: "Low", done: false },
  { id: 4, title: "Review plugin PRs", priority: "Med", done: true },
]);
const taskProgress = computed(() => {
  const done = tasks.filter(t => t.done).length;
  return Math.round((done / tasks.length) * 100);
});

// Plugin marketplace preview
type PluginCard = {
  id: string;
  name: string;
  category: string;
  desc: string;
  icon: string;
  enabled: boolean;
  color: string;
  tags?: string[];
};
const pluginCategories = ["All", "Productivity", "Communication", "Social"];
const selectedPluginCategory = ref("All");
const plugins = reactive<PluginCard[]>([
  { id: "email", name: "Email Assistant", category: "Communication", desc: "Smart triage + auto-draft replies", icon: "tabler-mail-cog", enabled: true, color: "bg-gradient-to-br from-purple-800/40 to-purple-600/20", tags: ["AI", "Priority"] },
  { id: "whatsapp", name: "WhatsApp Sync", category: "Communication", desc: "Two-way message & event pipeline", icon: "tabler-brand-whatsapp", enabled: false, color: "bg-gradient-to-br from-emerald-700/30 to-emerald-500/10", tags: ["Messages"] },
  { id: "calendar", name: "Calendar Fusion", category: "Productivity", desc: "Predictive scheduling & conflict guard", icon: "tabler-calendar-stats", enabled: true, color: "bg-gradient-to-br from-indigo-700/30 to-indigo-500/10", tags: ["Time"] },
  { id: "notes", name: "Notes Intelligence", category: "Productivity", desc: "Semantic clustering + summarization", icon: "tabler-notes", enabled: true, color: "bg-gradient-to-br from-fuchsia-700/30 to-fuchsia-500/10", tags: ["NLP"] },
]);
const filteredPlugins = computed(() => selectedPluginCategory.value === "All" ? plugins : plugins.filter(p => p.category === selectedPluginCategory.value));
function togglePlugin(p: PluginCard) {
  p.enabled = !p.enabled;
}

// Events feed (real-time like)
type EventItem = { id: number; plugin: string; type: string; title: string; time: string; severity?: string; icon: string };
const eventFilterPlugin = ref("All");
const events = reactive<EventItem[]>([
  { id: 1, plugin: "WhatsApp Sync", type: "message", title: "New message from Alex: “Ship status?”", time: "2m", severity: "normal", icon: "tabler-brand-whatsapp" },
  { id: 2, plugin: "Calendar Fusion", type: "reminder", title: "Design Review starts in 30m", time: "8m", severity: "high", icon: "tabler-calendar" },
  { id: 3, plugin: "Email Assistant", type: "email", title: "Draft prepared: Weekly performance summary", time: "21m", severity: "info", icon: "tabler-mail" },
  { id: 4, plugin: "Notes Intelligence", type: "note", title: "Auto summary generated: Investor Call", time: "31m", severity: "info", icon: "tabler-notes" },
]);
const pluginNames = computed(() => ["All", ...new Set(events.map(e => e.plugin))]);
const filteredEvents = computed(() => eventFilterPlugin.value === "All" ? events : events.filter(e => e.plugin === eventFilterPlugin.value));

// Notification center preview
const notifications = reactive([
  { id: 1, title: "Voice session transcript saved", icon: "tabler-microphone", time: "Just now" },
  { id: 2, title: "2 tasks auto-rescheduled", icon: "tabler-robot", time: "5m" },
  { id: 3, title: "Plugin \"Calendar Fusion\" updated", icon: "tabler-refresh", time: "18m" },
]);

// Urgent information aggregation (calls, meetings, priority tasks)
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
  {
    id: 1,
    type: "call",
    title: "Incoming Call: Sarah",
    desc: "Personal call • ringing (15s)",
    time: "Now",
    icon: "tabler-phone-call",
    level: "critical",
    action: "Answer",
  },
  {
    id: 2,
    type: "meeting",
    title: "Product Strategy Meeting",
    desc: "Starts in 5 min • Boardroom / Zoom",
    time: "5m",
    icon: "tabler-calendar-event",
    level: "high",
    action: "Join",
  },
  {
    id: 3,
    type: "task",
    title: "Finalize Investor Deck",
    desc: "Marked PRIORITY • due today 6 PM",
    time: "Due 6h",
    icon: "tabler-presentation",
    level: "high",
  },
]);
const acknowledged = ref<string[]>([]);
function isAck(id: string | number) {
  return acknowledged.value.includes(String(id));
}
// Derive high-priority undone tasks into urgent feed (declare first for reference below)
const urgentItems = computed<UrgentItem[]>(() => {
  const hiTasks = tasks
    .filter(t => t.priority === "High" && !t.done)
    .map<UrgentItem>(t => ({
      id: `task-${t.id}`,
      type: "task",
      title: t.title,
      desc: "High priority task",
      time: "Today",
      icon: "tabler-alert-circle",
      level: "high",
    }));
  return [...urgentBase, ...hiTasks];
});
function acknowledge(id: string | number) {
  const key = String(id);
  if (!acknowledged.value.includes(key))
    acknowledged.value.push(key);
}
function acknowledgeAll() {
  urgentItems.value.forEach(i => acknowledge(i.id));
}

// Voice input state (placeholder)
const listening = ref(false);
function toggleListening() {
  listening.value = !listening.value;
}

// Theme accent utility (legacy reference removed)
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <main class="dashboard-root mx-auto w-full max-w-[1650px] flex-1 px-3 py-4 sm:px-6">
      <!-- Top Greeting & quick stats row -->
      <div class="dashboard-top-row mb-6 grid gap-4 lg:grid-cols-12">
        <!-- Greeting / Voice panel -->
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
                <Icon v-else :name="listening ? 'tabler-wave-sine' : 'tabler-microphone'" />
                <span>{{ listening ? 'Listening…' : 'Speak' }}</span>
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
              Tip: Say "Summarize my morning inputs" to get a cross‑channel brief.
            </div>
          </div>
        </div>

        <!-- KPI tiles redesigned -->
        <div class="lg:col-span-8 kpi-grid">
          <div
            v-for="k in kpis"
            :key="k.id"
            class="relative overflow-hidden rounded-[26px] p-4 md:p-5 lg:p-6 2xl:p-7 shadow-sm ring-1 ring-white/5 transition backdrop-blur kpi-card flex flex-col"
            :class="[
              k.variant === 'gradient' ? 'bg-gradient-to-br from-purple-600 via-fuchsia-600 to-indigo-600 text-white kpi-gradient' : 'bg-base-200/20 hover:bg-base-200/30',
            ]"
          >
            <!-- top-right action bubble -->
            <button class="absolute right-2 top-2 rounded-full bg-base-100/70 p-1.5 text-xs shadow hover:scale-105 hover:bg-base-100/90 active:scale-95 transition">
              <Icon name="tabler-arrow-up-right" class="text-base opacity-70" />
            </button>
            <!-- Decorative rings for gradient variant -->
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
                  <Icon :name="deltaIcon(k)" class="inline size-3" /> {{ deltaText(k) }}
                </span>
              </div>
              <div class="flex items-end justify-between gap-2 flex-1">
                <div>
                  <div class="kpi-value font-semibold tracking-tight" :class="k.variant === 'gradient' ? 'text-white' : k.accent">
                    {{ formatValue(k) }}
                  </div>
                  <div class="mt-1 text-[11px] opacity-60">
                    {{ baselineLabel(k) }}
                  </div>
                </div>
                <!-- Sparkline if provided -->
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

      <!-- Main adaptive grid (inspired by multi panel trading layout) -->
      <div class="dashboard-grid grid auto-rows-[minmax(120px,auto)] gap-5 lg:grid-cols-12">
        <!-- Events Feed (Left / Large) -->
        <section class="card dashboard-card col-span-12 lg:col-span-5 xl:col-span-4 border shadow-sm bg-base-200/10 backdrop-blur">
          <div class="card-body gap-4">
            <div class="flex items-center justify-between">
              <h2 class="font-semibold">
                Live Events
              </h2>
              <div class="flex gap-2">
                <select v-model="eventFilterPlugin" class="select select-xs w-32 bg-base-300/40">
                  <option v-for="p in pluginNames" :key="p">
                    {{ p }}
                  </option>
                </select>
              </div>
            </div>
            <ul class="space-y-3 max-h-[340px] overflow-auto pr-1 custom-scroll">
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
                    {{ e.plugin }} • {{ e.time }}
                  </p>
                </div>
                <span class="badge badge-ghost badge-xs" :class="{ 'badge-error': e.severity === 'high', 'badge-info': e.severity === 'info' }">{{ e.type }}</span>
              </li>
            </ul>
          </div>
        </section>

        <!-- Urgent Info Panel -->
        <section class="card dashboard-card col-span-12 lg:col-span-7 xl:col-span-4 border shadow-sm bg-base-200/10 backdrop-blur">
          <div class="card-body gap-4">
            <div class="flex items-center justify-between">
              <h2 class="font-semibold flex items-center gap-2">
                <Icon name="tabler-alert-triangle" class="text-amber-400" /> Urgent Info
              </h2>
              <div class="flex items-center gap-2">
                <button
                  class="btn btn-xs btn-outline"
                  :disabled="acknowledged.length === urgentItems.length"
                  @click="acknowledgeAll"
                >
                  Acknowledge All
                </button>
              </div>
            </div>
            <ul class="space-y-3 max-h-[300px] overflow-auto pr-1 custom-scroll">
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
                  class="rounded-lg p-2 flex items-center justify-center"
                  :class="u.level === 'critical' ? 'bg-rose-500/20 text-rose-300' : u.level === 'high' ? 'bg-amber-500/15 text-amber-300' : 'bg-base-300/40 text-purple-300'"
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
          </div>
        </section>

        <!-- Task Board -->
        <section class="card dashboard-card col-span-12 xl:col-span-4 border shadow-sm bg-base-200/10">
          <div class="card-body gap-4">
            <div class="flex items-start justify-between">
              <h2 class="font-semibold">
                Tasks Today
              </h2>
              <div class="text-xs opacity-70">
                {{ taskProgress }}% done
              </div>
            </div>
            <ul class="space-y-2 max-h-[180px] overflow-auto pr-1 custom-scroll">
              <li
                v-for="t in tasks"
                :key="t.id"
                class="flex items-center gap-3 rounded-lg border border-base-200/40 bg-base-100/20 p-2"
              >
                <input
                  v-model="t.done"
                  type="checkbox"
                  class="checkbox checkbox-xs checkbox-primary"
                >
                <div class="flex-1 min-w-0">
                  <p class="truncate text-sm" :class="t.done ? 'line-through opacity-50' : ''">
                    {{ t.title }}
                  </p>
                  <span class="badge badge-ghost badge-xs mt-1" :class="{ 'badge-error': t.priority === 'High', 'badge-warning': t.priority === 'Med', 'badge-success': t.priority === 'Low' }">{{ t.priority }}</span>
                </div>
              </li>
            </ul>
            <progress
              class="progress progress-primary"
              :value="taskProgress"
              max="100"
            />
            <button class="btn btn-xs btn-outline w-fit">
              Add Task
            </button>
          </div>
        </section>

        <!-- Notes -->
        <section class="card dashboard-card col-span-12 md:col-span-6 lg:col-span-4 2xl:col-span-3 border shadow-sm bg-base-200/10">
          <div class="card-body gap-4">
            <div class="flex items-center justify-between">
              <h2 class="font-semibold">
                Recent Notes
              </h2>
              <button class="btn btn-xs btn-outline">
                Open
              </button>
            </div>
            <ul class="space-y-3 text-sm">
              <li
                v-for="n in notes"
                :key="n.id"
                class="group cursor-pointer rounded-xl border border-base-200/40 bg-base-100/20 p-3 hover:border-purple-500/40 hover:bg-base-100/40"
              >
                <p class="font-medium truncate">
                  {{ n.title }}
                </p>
                <p class="mt-0.5 text-xs opacity-60 line-clamp-2">
                  {{ n.snippet }}
                </p>
              </li>
            </ul>
          </div>
        </section>

        <!-- Plugin Marketplace Preview -->
        <section class="card dashboard-card col-span-12 md:col-span-6 lg:col-span-8 2xl:col-span-6 border shadow-sm bg-base-200/10">
          <div class="card-body gap-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <h2 class="font-semibold">
                Plugins
              </h2>
              <div class="flex items-center gap-2">
                <div class="tabs tabs-sm tabs-boxed bg-base-300/30">
                  <a
                    v-for="c in pluginCategories"
                    :key="c"
                    class="tab"
                    :class="{ 'tab-active': selectedPluginCategory === c }"
                    @click="selectedPluginCategory = c"
                  >{{ c }}</a>
                </div>
                <button class="btn btn-xs btn-outline">
                  Marketplace
                </button>
              </div>
            </div>
            <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <div
                v-for="p in filteredPlugins"
                :key="p.id"
                class="group relative overflow-hidden rounded-xl border border-base-200/40 p-4 text-sm shadow-sm transition hover:border-purple-500/40"
                :class="p.color"
              >
                <div class="mb-3 flex items-start justify-between">
                  <div class="flex items-center gap-2">
                    <div class="rounded-lg bg-base-100/40 p-2">
                      <Icon :name="p.icon" class="text-purple-300" />
                    </div>
                    <div>
                      <p class="font-medium leading-tight">
                        {{ p.name }}
                      </p>
                      <p class="text-[10px] uppercase tracking-wide opacity-60">
                        {{ p.category }}
                      </p>
                    </div>
                  </div>
                  <label class="swap swap-rotate">
                    <input
                      type="checkbox"
                      :checked="p.enabled"
                      @change="togglePlugin(p)"
                    >
                    <Icon name="tabler-toggle-right" class="swap-on text-green-400" />
                    <Icon name="tabler-toggle-left" class="swap-off opacity-50" />
                  </label>
                </div>
                <p class="line-clamp-2 opacity-70">
                  {{ p.desc }}
                </p>
                <div class="mt-3 flex flex-wrap gap-1">
                  <span
                    v-for="t in p.tags"
                    :key="t"
                    class="badge badge-ghost badge-xs"
                  >{{ t }}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Notifications Center Preview -->
        <section class="card dashboard-card col-span-12 md:col-span-6 lg:col-span-4 2xl:col-span-3 border shadow-sm bg-base-200/10">
          <div class="card-body gap-4">
            <div class="flex items-center justify-between">
              <h2 class="font-semibold">
                Notifications
              </h2>
              <button class="btn btn-xs btn-outline">
                All
              </button>
            </div>
            <ul class="space-y-3 max-h-[210px] overflow-auto pr-1 custom-scroll">
              <li
                v-for="n in notifications"
                :key="n.id"
                class="flex items-start gap-3 rounded-xl border border-base-200/40 bg-base-100/20 p-3"
              >
                <div class="rounded-md bg-base-300/40 p-2">
                  <Icon :name="n.icon" class="text-purple-300" />
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium truncate">
                    {{ n.title }}
                  </p>
                  <p class="text-[10px] uppercase tracking-wide opacity-50">
                    {{ n.time }}
                  </p>
                </div>
                <button class="btn btn-ghost btn-xs">
                  ×
                </button>
              </li>
            </ul>
            <button class="btn btn-xs btn-primary">
              Clear All
            </button>
          </div>
        </section>

        <!-- Voice CTA / Publish style bar (sticky bottom center) -->
        <div class="pointer-events-none fixed inset-x-0 bottom-4 z-40 flex justify-center">
          <button class="voice-cta btn btn-primary pointer-events-auto gap-2 rounded-full bg-gradient-to-r from-purple-600 via-fuchsia-600 to-purple-500 shadow-xl shadow-purple-900/40" @click="toggleListening">
            <Icon :name="listening ? 'tabler-wave-sine' : 'tabler-microphone'" class="text-lg" />
            <span class="font-medium">{{ listening ? 'Listening... Speak now' : 'Ask Kali‑E Anything' }}</span>
            <span v-if="listening" class="loading loading-dots loading-xs" />
          </button>
        </div>
      </div>
    </main>
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

/* KPI Grid Responsive Layout */
.kpi-grid {
  display: grid;
  gap: 1.1rem;
  grid-template-columns: 1fr; /* phones */
  align-items: stretch;
}
/* Avoid orphan last row: force even counts */
@media (min-width: 520px) {
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (min-width: 980px) {
  /* jump directly to 4 to prevent 3+1 layout */
  .kpi-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
@media (min-width: 1400px) {
  .kpi-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
@media (min-width: 1750px) {
  .kpi-grid {
    grid-template-columns: repeat(5, 1fr);
  }
}
/* Ultra wide super large monitors */
@media (min-width: 2100px) {
  .kpi-grid {
    grid-template-columns: repeat(6, 1fr);
  }
}

/* KPI Card tweaks */
.kpi-card {
  min-height: 150px;
}

/* Ensure consistent internal spacing and prevent overlap */
.kpi-card .kpi-delta {
  position: relative;
  top: 1px;
}
.kpi-card h3 {
  max-width: 70%;
}
@media (max-width: 420px) {
  .kpi-card h3 {
    max-width: 100%;
  }
}

/* Clamp the main metric size to scale smoothly across breakpoints */
.kpi-value {
  font-size: clamp(1.4rem, 1.4rem + 0.6vw, 2rem);
  line-height: 1.1;
}

/* Reduce internal spacing when very narrow to avoid overlap */
@media (max-width: 430px) {
  .kpi-card {
    padding: 0.9rem;
  }
  .kpi-card span[role="delta"],
  .kpi-card .delta-pill {
    /* future-proof naming */
    font-size: 9px;
  }
  .kpi-card .sparkline {
    display: none;
  }
}

/* Optimize sparkline visibility */
.sparkline svg path:first-of-type {
  filter: drop-shadow(0 0 4px rgba(192, 132, 252, 0.4));
}

/* Ultra-small devices (e.g., iPhone SE 320px) adjustments */
@media (max-width: 360px) {
  .dashboard-root {
    padding-left: 0.5rem;
    padding-right: 0.5rem;
  }
  .dashboard-top-row {
    gap: 0.75rem;
  }
  .kpi-grid {
    gap: 0.75rem;
  }
  .kpi-card {
    border-radius: 18px;
  }
  .kpi-card h3 {
    font-size: 11px;
  }
  .kpi-value {
    font-size: clamp(1.25rem, 5.5vw, 1.6rem);
  }
  .voice-cta {
    font-size: 0.75rem;
    padding-left: 0.9rem;
    padding-right: 0.9rem;
    height: 40px;
  }
  .voice-cta span.font-medium {
    max-width: 150px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  /* Reduce vertical space in big panels */
  .dashboard-grid {
    gap: 1rem;
  }
  .card-body {
    padding: 0.9rem !important;
  }
  .card-body h2 {
    font-size: 0.9rem;
  }
}

/* General dashboard card responsiveness */
@media (max-width: 540px) {
  .dashboard-card ul {
    max-height: none !important;
  }
  .dashboard-card .custom-scroll {
    overflow-y: visible !important;
  }
  .dashboard-card .badge {
    font-size: 9px;
  }
  .dashboard-card .btn.btn-xs {
    height: 1.6rem;
    min-height: 1.6rem;
  }
  .dashboard-card .swap {
    transform: scale(0.9);
  }
  /* tighter spacing */
  .dashboard-card .card-body {
    gap: 0.9rem;
  }
}

/* When width is extremely constrained, stack plugin tabs and actions */
@media (max-width: 430px) {
  .dashboard-card:has(.tabs) .flex.flex-wrap.items-center {
    flex-direction: column;
    align-items: flex-start;
  }
  .dashboard-card:has(.tabs) .tabs {
    width: 100%;
    justify-content: space-between;
  }
}

/* Better wrapping for long text inside lists */
.dashboard-card p.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
}
@media (max-width: 400px) {
  .dashboard-card p.truncate {
    white-space: normal;
    display: -webkit-box;
    line-clamp: 2;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }
}

/* Voice button hide text on tiny devices to save space */
@media (max-width: 330px) {
  .voice-cta span.font-medium {
    display: none;
  }
  .voice-cta {
    padding: 0 0.9rem;
  }
}

/* Hide non-critical baseline text if not enough width inside KPI card */
@media (max-width: 350px) {
  .kpi-card .kpi-value + div {
    display: none;
  }
}

/* Medium small (<=640px) slight density increase */
@media (max-width: 640px) {
  .dashboard-grid {
    gap: 1.1rem;
  }
}
</style>
