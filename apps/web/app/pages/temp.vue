<script setup>
import { AlertTriangle, Clock } from "lucide-vue-next";

const card = {
  icon: AlertTriangle,
  title: "High error rate detected",
  description: "API responses spiked in the last 5 minutes.",
  badge: "LIVE",
  urgency: "critical",
  actions: [
    { label: "View logs" },
    { label: "Resolve", variant: "default" },
  ],
};
// const exampleKpis = [
//   {
//     id: 1,
//     title: "AI Interactions",
//     value: "328",
//     sparklines: [10, 40, 25, 60, 80, 50],
//     baselineLabel: "vs yesterday 290",
//     deltaText: "5",
//   },
//   {
//     id: 2,
//     title: "Automation Time Saved",
//     value: "2.8",
//     sparklines: [15, 30, 45, 35, 60, 55],
//   },
//   {
//     id: 3,
//     title: "Avg Response Latency",
//     value: "420",
//     sparklines: [5, 10, 8, 12, 15, 11],
//   },
// ];
</script>

<template>
  <!-- <div class="grid grid-cols-2 gap-4">
    <div />
    <div class="p-10">
      <Card
        padding="p-6"
        border-radius="rounded-2xl"
        shadow="shadow-xl"
        layout="vertical"
        accent-color="text-fuchsia-300"
        :show-sparkline="true"
        sparkline-color="#c084fc"
        grid-columns="repeat(3, 1fr)"
        gap="1.2rem"
        :content="exampleKpis"
      />
    </div>
  </div> -->

  <Timeline
    :icon="Clock"
    title="Job completed"
    description="Background worker finished processing."
    timestamp="just now"
    time-group="Today"
    :badges="[
      { label: 'Worker', variant: 'default' },
      { label: 'OK', variant: 'secondary' },
    ]"
    action-label="Details"
  />
  <UrgentSignalCard v-bind="card" />
</template>
