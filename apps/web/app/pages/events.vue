<script setup lang="ts">
import type { Component } from "vue";

import { reactive } from "vue";

import { AlertTriangle, Bell } from "lucide-vue-next";

/*************************************************
 * Events + Urgent Activity Overview Page
 * Mirrors dashboard visual language (cards, gradients, pill metrics)
 * Provides: filters (plugin, severity, type), search, acknowledge flow
 *************************************************/

const exampleKpis = [
  {
    id: 1,
    title: "Total Events Processed",
    value: "8",
    baselineLabel: "Across 5 Plugins",
    deltaText: "5",
  },
  {
    id: 2,
    title: "HIGH / CRITICAL Events",
    value: "2",
    baselineLabel: "Needs Attention",
    deltaText: "1",
  },
  {
    id: 3,
    title: "Open Urgent Items",
    value: "3",
    baselineLabel: "Active Severity Alerts",
    deltaText: "1",
  },
  {
    id: 4,
    title: "Integrated Plugins",
    value: "5",
    baselineLabel: "Connected Sources",
    deltaText: "0",
  },
];

type TimelineEntry = {
  id: number;
  icon: Component;
  title: string;
  description: string;
  timestamp: string;
  timeGroup?: string;
};
const timeline = reactive<TimelineEntry[]>([
  {
    id: 1,
    icon: Bell,
    title: "User signed up",
    description: "New signup from mobile",
    timestamp: "10:02",
    timeGroup: "Today",
  },
  {
    id: 2,
    icon: AlertTriangle,
    title: "Payment failed",
    description: "Card declined",
    timestamp: "10:10",
    timeGroup: "Today",
  },
  {
    id: 3,
    icon: Bell,
    title: "Deploy complete",
    description: "v1.2 released",
    timestamp: "Yesterday",
    timeGroup: "Yesterday",
  },
]);
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <main class="mx-auto w-full max-w-[1400px] flex-1 px-3 py-6 sm:px-6">
      <header class="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight">
            Activity & Events
          </h1>
          <p class="mt-3 text-sm opacity-70 md:mt-1">
            Unified feed of system activity, plugin events & urgent signals.
          </p>
        </div>
        <div class="flex items-center gap-2 text-xs uppercase tracking-wide opacity-60 mt-3 md:mt-0">
          <Icon name="tabler-clock" class="text-emerald-300" />
          Updated 4 minutes ago
        </div>
      </header>
      <div class="p-2 h-max relative">
        <Card
          variant="solid"
          padding="p-6"
          border-radius="rounded-2xl"
          shadow="shadow-xl"
          layout="vertical"
          accent-color="text-fuchsia-300"
          grid-columns="repeat(4, 1fr)"
          gap="1.2rem"
          :content="exampleKpis"
        />
      </div>
      <!-- Search & Filters -->
      <div class="flex flex-col flex-wrap items-center gap-4 p-2 mt-2 mb-8 md:flex-row">
        <div class="relative flex-1 w-full">
          <Icon name="tabler-search" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-base opacity-60" />
          <input
            v-model="search"
            type="text"
            placeholder="Search events..."
            class="input input-sm w-full rounded-xl bg-base-200/30 pl-10"
          >
        </div>
        <div className="flex gap-11 md:gap-3 flex-wrap filters">
          <Button
            variant="ghost"
            size="sm"
            class-name="h-9 text-xs font-normal "
          >
            Reset
          </Button>
          <Button size="sm" class-name="h-9 text-xs font-normal">
            Ack All Urgent
          </Button>
        </div>
      </div>
      <div
        grid
        grid-cols-1
        lg:grid-cols-3
      />
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
</style>
