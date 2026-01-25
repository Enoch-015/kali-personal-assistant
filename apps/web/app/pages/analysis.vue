<script setup lang="ts">
import { computed, reactive } from "vue";

type ServiceStatus = {
  id: string;
  name: string;
  status: "online" | "degraded" | "offline";
  latency: number;
  target: number;
  latencyDelta: number;
  icon: string;
  trend: number[];
};

type StatusKey = ServiceStatus["status"];

const serviceStatuses = reactive<ServiceStatus[]>([
  {
    id: "dialogue",
    name: "Voice Orchestrator",
    status: "online",
    latency: 182,
    target: 220,
    latencyDelta: -18,
    icon: "tabler-navigation",
    trend: [242, 235, 248, 228, 241, 219, 232, 215, 226, 208, 221, 195, 214, 188, 205, 192, 198, 178, 190, 182],
  },
  {
    id: "memory",
    name: "Memory Service",
    status: "degraded",
    latency: 410,
    target: 350,
    latencyDelta: 60,
    icon: "tabler-database-cog",
    trend: [325, 338, 320, 355, 342, 368, 351, 375, 362, 388, 371, 395, 378, 402, 385, 398, 392, 415, 405, 410],
  },
  {
    id: "relay",
    name: "Event Relay",
    status: "online",
    latency: 95,
    target: 120,
    latencyDelta: -12,
    icon: "tabler-broadcast",
    trend: [128, 118, 125, 115, 122, 108, 118, 105, 112, 102, 108, 98, 105, 92, 102, 88, 98, 92, 88, 95],
  },
  {
    id: "redis",
    name: "Redis Event Bus",
    status: "online",
    latency: 132,
    target: 160,
    latencyDelta: -14,
    icon: "tabler-graph",
    trend: [178, 165, 172, 158, 168, 152, 162, 148, 158, 142, 152, 138, 148, 135, 145, 128, 142, 125, 138, 132],
  },
]);

const statusChipMeta: Record<StatusKey, { badge: string; chip: string; label: string }> = {
  online: {
    badge: "bg-emerald-500/15 text-emerald-100 border-none",
    chip: "bg-emerald-400",
    label: "Online",
  },
  degraded: {
    badge: "bg-amber-500/15 text-amber-100 border-none",
    chip: "bg-amber-400",
    label: "Degraded",
  },
  offline: {
    badge: "bg-rose-500/20 text-rose-100 border-none",
    chip: "bg-rose-400",
    label: "Offline",
  },
};

const serviceStatusSummary = computed(() => {
  const counts: Record<StatusKey, number> = { online: 0, degraded: 0, offline: 0 };
  for (const svc of serviceStatuses)
    counts[svc.status] += 1;
  return (Object.entries(counts) as Array<[StatusKey, number]>).map(([key, count]) => ({
    key,
    count,
    label: statusChipMeta[key].label,
    color: statusChipMeta[key].chip,
  })).filter(item => item.count > 0);
});

const overallHealth = computed(() => {
  const offline = serviceStatuses.filter(svc => svc.status === "offline").length;
  const degraded = serviceStatuses.filter(svc => svc.status === "degraded").length;
  if (offline > 0)
    return { label: "Disrupted", tone: "text-rose-400" };
  if (degraded > 1)
    return { label: "Attention", tone: "text-amber-400" };
  if (degraded === 1)
    return { label: "Watching", tone: "text-amber-400" };
  return { label: "Optimal", tone: "text-emerald-400" };
});

type HealthSignal = {
  id: string;
  label: string;
  metric: string;
  change: number;
  direction: "up" | "down";
  unit?: string;
  description: string;
};

const healthSignals = reactive<HealthSignal[]>([
  {
    id: "uptime",
    label: "Uptime 30d",
    metric: "99.92%",
    change: 0.04,
    direction: "up",
    unit: "%",
    description: "SLO threshold 99.90%.",
  },
  {
    id: "errors",
    label: "Error rate",
    metric: "0.18%",
    change: -0.05,
    direction: "down",
    unit: "%",
    description: "Across orchestrated workloads.",
  },
  {
    id: "voice-load",
    label: "Voice load",
    metric: "62%",
    change: 7,
    direction: "up",
    unit: "%",
    description: "Capacity used by voice streaming nodes.",
  },
]);

function signalChangeClass(signal: HealthSignal) {
  const favorable = signal.direction === "up" ? signal.change >= 0 : signal.change <= 0;
  return favorable ? "text-emerald-300" : "text-rose-300";
}
function signalChangeText(signal: HealthSignal) {
  if (signal.change === 0)
    return "Flat";
  const sign = signal.change > 0 ? "+" : "-";
  const formatted = Math.abs(signal.change).toFixed(2).replace(/\.00$/, "");
  const unit = signal.unit ?? "%";
  return `${sign}${formatted}${unit}`;
}

type Incident = {
  id: string;
  title: string;
  description: string;
  when: string;
  severity: "low" | "moderate" | "high";
  icon: string;
};

const incidentLog = reactive<Incident[]>([
  {
    id: "ml-cache",
    title: "ML cache refresh lag",
    description: "Cold start on embeddings cache caused fallback to slower vector lookup.",
    when: "2 hours ago",
    severity: "moderate",
    icon: "tabler-database-search",
  },
  {
    id: "voice-spike",
    title: "Edge voice spike",
    description: "Unexpected burst from APAC voice nodes throttled for 4 minutes.",
    when: "Yesterday",
    severity: "low",
    icon: "tabler-wave-sine",
  },
  {
    id: "webhook",
    title: "Webhook retries increased",
    description: "Third-party CRM endpoint degraded, automatic retries succeeded after 3 attempts.",
    when: "Mon 09:12",
    severity: "low",
    icon: "tabler-refresh-alert",
  },
]);

function incidentSeverityClass(severity: Incident["severity"]) {
  if (severity === "high")
    return "text-rose-500 border-none";
  if (severity === "moderate")
    return "text-amber-400 border-none";
  return "text-green-300 border-none";
}
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <main class="mx-auto w-full max-w-[1400px] flex-1 px-3 py-6 sm:px-6">
      <header class="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight">
            Systems Analysis
          </h1>
          <p class="mt-1 text-sm opacity-70">
            Infrastructure, latency, and resilience signals for deeper diagnosis.
          </p>
        </div>
        <div class="flex items-center gap-2 text-xs uppercase tracking-wide opacity-60">
          <Icon name="tabler-clock" class="text-emerald-300" />
          Updated 4 minutes ago
        </div>
      </header>

      <div class="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-12">
        <!-- performance and health -->
        <section class="border col-span-12 md:col-span-3 shadow-sm bg-base-200/10 backdrop-blur lg:col-span-12">
          <div class="card-body gap-4">
            <div class="flex items-center justify-between">
              <h2 class="font-semibold flex items-center gap-2">
                <Icon name="tabler-shield-check" class="text-emerald-300" /> Platform System Health
              </h2>
              <span class="badge badge-sm border-none" :class="overallHealth.tone">
                {{ overallHealth.label }}
              </span>
            </div>
            <div class="flex flex-wrap items-center gap-3 text-xs text-purple-100/80">
              <span
                v-for="chip in serviceStatusSummary"
                :key="chip.key"
                class="inline-flex items-center gap-1 rounded-full bg-base-100/30 px-2.5 py-1"
              >
                <span class="inline-block h-2.5 w-2.5 rounded-full" :class="chip.color" />
                <span class="font-semibold">{{ chip.count }}</span>
                <span class="uppercase tracking-wide opacity-70">{{ chip.label }}</span>
              </span>
            </div>
            <Card
              class="responsive-grid-card"
              variant="service-bar"
              :content="serviceStatuses"
              grid-columns="repeat(4, 1fr)"
              padding="p-10"
              border-radius="rounded-xl"
              shadow="shadow-xl"
            />
            <div class="grid grid-cols-1 md:grid-cols-3 gap-5 ">
              <div
                v-for="signal in healthSignals"
                :key="signal.id"
                class="rounded-xl ring-1 ring-white/5 backdrop-blur transition shadow-xl hover:bg-base-200/30 p-3 w-full text-sm"
              >
                <div class="flex items-center justify-between">
                  <p class="font-medium">
                    {{ signal.label }}
                  </p>
                  <span class="text-xs font-medium" :class="signalChangeClass(signal)">
                    {{ signalChangeText(signal) }}
                  </span>
                </div>
                <p class="text-lg font-semibold">
                  {{ signal.metric }}
                </p>
                <p class="text-xs opacity-60">
                  {{ signal.description }}
                </p>
              </div>
            </div>
          </div>
        </section>

        <!-- recent activities -->
        <section class="card col-span-12 border shadow-sm bg-base-200/10 backdrop-blur transition duration-300 hover:scale-[1.02] ">
          <div class="card-body gap-4">
            <div class="flex items-center justify-between">
              <h2 class="font-semibold flex items-center gap-2">
                <Icon name="tabler-clipboard-text" class="text-purple-400" /> Recent Incidents
              </h2>
              <span class="badge badge-sm border-none text-amber-100">
                Past 7 days
              </span>
            </div>
            <ul class="space-y-3">
              <li
                v-for="incident in incidentLog"
                :key="incident.id"
                class="flex items-start gap-3 rounded-xl border border-base-200/40 bg-base-100/15 p-3 text-sm"
              >
                <div class="rounded-lg bg-base-300/40 p-2">
                  <Icon :name="incident.icon" class="text-purple-500" />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-start justify-between gap-2">
                    <p class="font-medium leading-tight">
                      {{ incident.title }}
                    </p>
                    <span class="badge badge-ghost badge-xs" :class="incidentSeverityClass(incident.severity)">
                      {{ incident.severity }}
                    </span>
                  </div>
                  <p class="text-xs opacity-60">
                    {{ incident.description }}
                  </p>
                  <p class="mt-1 text-[11px] uppercase tracking-wide opacity-50">
                    {{ incident.when }}
                  </p>
                </div>
              </li>
            </ul>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
  @media (max-width: 768px) {
  .responsive-grid-card {
    grid-template-columns: repeat(2, 1fr);
  }
  @media (max-width: 480px) {
    .responsive-grid-card {
      grid-template-columns: 1fr;
    }
  }
}
</style>
