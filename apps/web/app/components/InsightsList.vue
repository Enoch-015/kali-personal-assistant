<script setup lang="ts">
import { computed } from "vue";

type InsightItem = {
  label: string;
  value: number;
  color?: string;
};

const props = defineProps<{
  title: string;
  items: InsightItem[];
}>();

const maxValue = computed(() =>
  Math.max(...props.items.map(item => item.value)),
);
</script>

<template>
  <div class="space-y-3">
    <!-- Title -->
    <h3
      class="text-xs text-muted-foreground uppercase tracking-wide font-mono"
    >
      {{ title }}
    </h3>

    <!-- List -->
    <div class="space-y-2.5">
      <div
        v-for="(item, index) in items"
        :key="index"
        class="flex items-center justify-between gap-3"
      >
        <div class="flex items-center gap-3 flex-1 min-w-0">
          <span
            class="text-xs text-muted-foreground min-w-24"
          >
            {{ item.label }}
          </span>

          <!-- Progress bar -->
          <div
            class="flex-1 h-1 bg-secondary/50 rounded-sm overflow-hidden"
          >
            <div
              class="h-full rounded-sm transition-all"
              :style="{
                width: `${(item.value / maxValue) * 100}%`,
                backgroundColor:
                  item.color
                  ?? 'hsl(var(--muted-foreground) / 0.5)',
              }"
            />
          </div>
        </div>

        <!-- Value -->
        <span
          class="text-xs font-medium text-foreground shrink-0 font-mono"
        >
          {{ item.value }}
        </span>
      </div>
    </div>
  </div>
</template>
