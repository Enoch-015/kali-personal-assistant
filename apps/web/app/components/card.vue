<script setup>
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

// card background variants
const variantClasses = computed(() => {
  if (props.variant === "gradient") {
    return "bg-gradient-to-br from-purple-600 via-fuchsia-600 to-indigo-600 text-white h-48";
  }
  else if (props.variant === "solid") {
    return "bg-base-200/20 hover:bg-base-200/30 h-48";
  }
  return "bg-base-200/20 hover:bg-base-200/30 h-48";
});

const processedContent = computed(() =>
  props.content.map(item => ({
    ...item,
    sparkPath: props.variant !== "solid" && item.sparklines
      ? `M${item.sparklines.map((y, i) => `${i * 20} ${40 - y}`).join(" L")}`
      : null,
  })),
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
      class="relative flex flex-col overflow-hidden  ring-1 ring-white/5 backdrop-blur transition"
      :class="[
        variantClasses,
        padding,
        borderRadius,
        shadow,
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
        <!-- Title + Delta Pill -->
        <div class="flex items-start md:flex-col lg:flex-row gap-2">
          <h3 class="text-[13px] font-medium tracking-wide uppercase opacity-80 leading-tight line-clamp-2 pr-1">
            {{ item.title }}
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
              {{ item.value }}
            </div>
            <div class="mt-1 text-[15px] opacity-60">
              {{ item.baselineLabel }}
            </div>
          </div>

          <!-- Sparkline only for gradient -->
          <div
            v-if="item.sparkPath && showSparkline"
            class="relative h-14 w-25 sm:h-16 sm:w-24"
          >
            <svg viewBox="0 0 100 40" class="absolute inset-0 h-full w-full overflow-visible">
              <defs>
                <linearGradient
                  :id="`grad-${item.id}`"
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
                :d="item.sparkPath"
                fill="none"
                :stroke="sparklineColor"
                stroke-width="2"
                stroke-linejoin="round"
                stroke-linecap="round"
              />
              <path
                :d="`${item.sparkPath} L100 40 L0 40 Z`"
                :fill="`url(#grad-${item.id})`"
              />
            </svg>
          </div>
        </div>
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
