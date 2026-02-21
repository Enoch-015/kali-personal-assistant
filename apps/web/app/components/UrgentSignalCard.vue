<script setup lang="ts">
import type { Component } from "vue";

defineProps<{
  icon: Component;
  title: string;
  description: string;
  badge?: string;
  urgency: "critical" | "high" | "medium";
  actions: Array<{
    label: string;
    variant?: "default" | "outline";
  }>;
}>();

const urgencyColors = {
  critical: "border-destructive/60 ",
  high: "border-warning/60 ",
  medium: "border-border ",
};

const iconBgColors = {
  critical: "bg-destructive/15",
  high: "bg-warning/15",
  medium: "bg-secondary/80",
};

const iconColors = {
  critical: "text-destructive/90",
  high: "text-warning/90",
  medium: "text-muted-foreground",
};
</script>

<template>
  <div
    class="border rounded-md p-4"
    :class="urgencyColors[urgency]"
  >
    <!-- Header -->
    <div class="flex items-start gap-3 mb-3">
      <!-- Icon -->
      <div
        class="w-9 h-9 rounded flex items-center justify-center shrink-0"
        :class="iconBgColors[urgency]"
      >
        <component
          :is="icon"
          class="w-4 h-4"
          :class="iconColors[urgency]"
        />
      </div>

      <!-- Content -->
      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-2 mb-1">
          <h4 class="font-medium text-foreground text-sm">
            {{ title }}
          </h4>

          <Badge
            v-if="badge"
            variant="outline"
            class="bg-muted/50 text-muted-foreground border-border text-xs shrink-0 font-mono"
          >
            {{ badge }}
          </Badge>
        </div>

        <p class="text-xs text-muted-foreground/80">
          {{ description }}
        </p>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex gap-2">
      <Button
        v-for="(action, index) in actions"
        :key="index"
        :variant="action.variant || 'outline'"
        size="sm"
        class="text-xs h-7 font-normal"
      >
        {{ action.label }}
      </Button>
    </div>
  </div>
</template>
