<script setup>
import BarChart from "./BarChart.vue";
import LineChart from "./LineChart.vue";

const props = defineProps({
  variant: {
    type: String,
    default: "default",
  },
  accentColor: {
    type: String,
    default: "text-gray-800",
  },
  padding: {
    type: String,
    default: "p-4",
  },
  borderRadius: {
    type: String,
    default: "rounded-lg",
  },
  shadow: {
    type: String,
    default: "shadow-lg",
  },
  layout: {
    type: String,
    default: "vertical",
  },
  showSparkline: {
    type: Boolean,
    default: true,
  },
  sparklineColor: {
    type: String,
    default: "#c084fc",
  },
  content: {
    type: Array,
    required: true,
  },
  gridColumns: {
    type: String,
    default: "repeat(4, 1fr)",
  },
  gap: {
    type: String,
    default: "1rem",
  },
});

// Status badge styling for ServiceStatus items
const statusChipMeta = {
  online: {
    badge: "text-emerald-300 border-none",
    chip: "bg-emerald-400",
    label: "Online",
  },
  degraded: {
    badge: "text-amber-300 border-none",
    chip: "bg-amber-400",
    label: "Degraded",
  },
  offline: {
    badge: "text-rose-300 border-none",
    chip: "bg-rose-400",
    label: "Offline",
  },
};

function getStatusBadgeClass(status) {
  return statusChipMeta[status]?.badge ?? "bg-slate-500/15 text-slate-200 border-none";
}

function getStatusLabel(status) {
  return statusChipMeta[status]?.label ?? status;
}

function getLatencyDeltaClass(item) {
  if (item.latencyDelta === undefined)
    return "";
  return item.latencyDelta <= 0 ? "text-emerald-300" : "text-amber-300";
}

function getLatencyDeltaText(item) {
  if (item.latencyDelta === undefined || item.target === undefined)
    return "";
  if (item.latencyDelta === 0)
    return "On target";
  const sign = item.latencyDelta > 0 ? "+" : "-";
  return `${sign}${Math.abs(item.latencyDelta)}ms vs target`;
}

// card background variants
const variantClasses = computed(() => {
  if (props.variant === "gradient") {
    return "bg-gradient-to-br from-purple-600 via-fuchsia-600 to-indigo-600 text-white h-48";
  }

  return "bg-base-200/20 hover:bg-base-200/30 h-48";
});

// Generate line chart data for LineChart component
function generateLineChartData(points, color) {
  if (!points?.length)
    return null;
  return {
    labels: points.map(() => ""),
    datasets: [{
      data: points,
      borderColor: color,
      backgroundColor: `${color}20`,
      fill: true,
      tension: 0.4,
      pointRadius: 0,
    }],
  };
}

// Generate bar chart data for BarChart component
function generateBarChartData(points, color) {
  if (!points?.length)
    return null;
  return {
    labels: points.map(() => ""),
    datasets: [{
      data: points,
      backgroundColor: color,
      borderRadius: 2,
      barPercentage: 0.3,
      categoryPercentage: 0.9,
    }],
  };
}

// Sparkline chart options (no grid, no labels, tooltips enabled)
const sparklineOptions = {
  plugins: {
    legend: { display: false },
    tooltip: {
      enabled: true,
      backgroundColor: "rgba(0, 0, 0, 0.8)",
      titleColor: "#fff",
      bodyColor: "#fff",
      padding: 8,
      cornerRadius: 6,
      displayColors: false,
      callbacks: {
        title: () => "",
        label: context => `${context.parsed.y}`,
      },
    },
  },
  interaction: {
    intersect: false,
    mode: "index",
  },
  scales: {
    x: {
      display: false,
      grid: { display: false },
    },
    y: {
      display: false,
      grid: { display: false },
    },
  },
};

// Bar chart options (no grid, no labels, tooltips enabled)
const barChartOptions = {
  plugins: {
    legend: { display: false },
    tooltip: {
      enabled: true,
      backgroundColor: "rgba(0, 0, 0, 0.8)",
      titleColor: "#fff",
      bodyColor: "#fff",
      padding: 8,
      cornerRadius: 6,
      displayColors: false,
      callbacks: {
        title: () => "",
        label: context => `${context.parsed.y}`,
      },
    },
  },
  interaction: {
    intersect: false,
    mode: "index",
  },
  scales: {
    x: {
      display: false,
      grid: { display: false },
    },
    y: {
      display: false,
      grid: { display: false },
    },
  },
};

const processedContent = computed(() =>
  props.content.map((item) => {
    // Support both sparklines (KPI style) and trend (ServiceStatus style)
    const sparkData = item.trend ?? item.sparklines;
    const lineChartData = props.showSparkline && sparkData ? generateLineChartData(sparkData, props.sparklineColor) : null;
    const barChartData = props.showSparkline && sparkData ? generateBarChartData(sparkData, props.sparklineColor) : null;

    return {
      ...item,
      lineChartData,
      barChartData,
      // Normalize name/title for display
      displayTitle: item.title ?? item.name,
      // Normalize value display
      displayValue: item.value ?? (item.latency !== undefined ? `${item.latency}ms` : null),
    };
  }),
);

function parseDelta(kpi) {
  const raw = kpi.delta ?? kpi.deltaText ?? 0;
  const num = Number.parseFloat(String(raw).replace(/[^\d.-]/g, ""));
  return Number.isFinite(num) ? num : 0;
}

function isFavorable(kpi) {
  const val = parseDelta(kpi);
  // respect an explicit flag if provided, otherwise higher delta is considered better
  if (typeof kpi.higherIsBetter === "boolean") {
    return kpi.higherIsBetter ? val > 0 : val < 0;
  }
  return val > 0;
}

function deltaPillClasses(kpi) {
  const base = "border border-white/10";
  const val = parseDelta(kpi);
  if (val === 0)
    return `${base} bg-slate-500/15 text-slate-200`;
  return isFavorable(kpi)
    ? `${base} bg-emerald-500/15 text-emerald-200`
    : `${base} bg-rose-500/15 text-rose-200`;
}

// grid columns
const gridTemplateColumns = computed(() => props.gridColumns);
</script>

<template>
  <div
    class="kpi-grid "
    :style="{ '--grid-columns': gridTemplateColumns, gap }"
  >
    <div
      v-for="item in processedContent"
      :key="item.id"
      class="relative flex flex-col overflow-hidden ring-1 ring-white/5 backdrop-blur transition-all duration-300"
      :class="[
        variantClasses,
        padding,
        borderRadius,
        shadow,
        variant === 'service-bar' ? 'hover:scale-[1.03] hover:z-10' : '',
      ]"
    >
      <!-- gradient background decorations -->
      <div
        v-if="item.variant === 'gradient'"
        class="pointer-events-none absolute inset-0 opacity-40"
      >
        <div class="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-fuchsia-400/20 blur-2xl" />
        <div class="absolute left-1/3 top-1/2 h-32 w-32 -translate-x-1/2 -translate-y-1/2 rounded-full bg-purple-300/10 blur-2xl" />
      </div>

      <!-- Layout Container -->
      <div class="relative z-10 flex h-full flex-col gap-2">
        <!-- SERVICE VARIANT: ServiceStatus layout with line chart -->
        <template v-if="variant === 'service'">
          <div class="flex items-start gap-3">
            <!-- Icon -->
            <div v-if="item.icon" class="rounded-lg bg-base-300/40 p-2">
              <Icon :name="item.icon" class="text-purple-200" />
            </div>
            <!-- Name & Status -->
            <div class="min-w-0">
              <p class="font-medium leading-tight text-sm">
                {{ item.displayTitle }}
              </p>
              <span
                v-if="item.status"
                class="badge badge-ghost badge-xs"
                :class="getStatusBadgeClass(item.status)"
              >
                {{ getStatusLabel(item.status) }}
              </span>
            </div>
            <!-- Latency info -->
            <div v-if="item.latency !== undefined" class="ml-auto text-right">
              <p v-if="item.target" class="text-xs opacity-60">
                Target {{ item.target }}ms
              </p>
              <p class="font-semibold text-sm" :class="getLatencyDeltaClass(item)">
                {{ item.latency }}ms
                <span v-if="item.latencyDelta !== undefined" class="font-normal">
                  · {{ getLatencyDeltaText(item) }}
                </span>
              </p>
            </div>
          </div>

          <!-- Sparkline for service variant (line chart) -->
          <div v-if="item.lineChartData && showSparkline" class="mt-auto h-14 w-full">
            <LineChart :data="item.lineChartData" :options="sparklineOptions" />
          </div>
        </template>

        <!-- SERVICE-BAR VARIANT: ServiceStatus layout with bar chart -->
        <template v-else-if="variant === 'service-bar'">
          <div class="flex flex-col gap-3">
            <div class=" relative flex items-center gap-2 ">
              <!-- Icon -->
              <div v-if="item.icon" class="rounded-lg bg-base-300/40 p-2">
                <Icon :name="item.icon" class="text-purple-200" />
              </div>
              <!-- Name & Status -->
              <div class="min-w-0 flex flex-wrap items-center gap-2">
                <p class="flex-1 min-w-[220px] font-medium leading-tight text-sm">
                  {{ item.displayTitle }}
                </p>

                <span
                  v-if="item.status"
                  class="badge badge-ghost badge-xs whitespace-nowrap"
                  :class="getStatusBadgeClass(item.status)"
                >
                  {{ getStatusLabel(item.status) }}
                </span>
              </div>

            </div>
            <!-- Latency info -->
            <div v-if="item.latency !== undefined" class="ml-auto text-right">
              <p v-if="item.target" class="text-xs opacity-60">
                Target {{ item.target }}ms
              </p>
              <p class="font-semibold text-sm" :class="getLatencyDeltaClass(item)">
                {{ item.latency }}ms
                <span v-if="item.latencyDelta !== undefined" class="font-normal">
                  · {{ getLatencyDeltaText(item) }}
                </span>
              </p>
            </div>
          </div>

          <!-- Bar chart for service-bar variant -->
          <div v-if="item.barChartData && showSparkline" class="mt-auto h-14 w-full">
            <BarChart :data="item.barChartData" :options="barChartOptions" />
          </div>
        </template>

        <!-- DEFAULT/GRADIENT/SOLID VARIANT: KPI layout -->
        <template v-else>
          <!-- Title + Delta Pill -->
          <div class="flex items-start md:flex-col lg:flex-row gap-2">
            <h3 class="text-[13px] font-medium tracking-wide uppercase opacity-80 leading-tight line-clamp-2 pr-1">
              {{ item.displayTitle }}
            </h3>

            <span
              v-if="item.deltaText"
              class="ml-auto inline-flex items-center gap-0.5 rounded-full px-2 py-1 text-[10px] font-medium leading-none backdrop-blur shrink-0 md:justify-center"
              :class="[deltaPillClasses(item)]"
            >
              <Icon
                v-if="item.deltaText !== undefined"
                :name="item.deltaText === 0 ? 'tabler-arrows-diff' : 'tabler-trending-up'"
                class="size-3"
              />

              {{ item.deltaText }}
            </span>
          </div>

          <!-- Value + Baseline + Sparkline -->
          <div
            class="flex flex-1 gap-1.5"
            :class="props.variant === 'solid'
              ? 'justify-center items-center text-center text-2xl'
              : 'justify-between items-end'"
          >
            <div>
              <div
                class="font-semibold tracking-tight"
                :class="item.variant === 'gradient' ? 'text-white' : accentColor"
              >
                {{ item.displayValue }}
              </div>
              <div v-if="item.baselineLabel" class="mt-1 text-[15px] opacity-60">
                {{ item.baselineLabel }}
              </div>
            </div>

            <!-- Sparkline for gradient/default variants -->
            <div
              v-if="item.lineChartData && showSparkline"
              class="h-14 w-25 sm:h-16 sm:w-24"
            >
              <LineChart :data="item.lineChartData" :options="sparklineOptions" />
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kpi-grid {
  display: grid;
  /* use a CSS variable so media queries can override the grid on small screens */
  grid-template-columns: var(--grid-columns);
}

/* default mobile behavior: 1 column at small screen sizes */
@media (max-width: 640px) {
  .kpi-grid {
    grid-template-columns: repeat(1, 1fr);
  }
}
</style>
