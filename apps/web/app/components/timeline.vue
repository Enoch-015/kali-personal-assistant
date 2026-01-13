<script setup lang="ts">
import type { Component } from "vue";

type TimelineBadge = {
  label: string;
  variant: "default" | "secondary" | "outline";
};

defineProps<{
  icon: Component;
  title: string;
  description: string;
  timestamp: string;
  timeGroup?: string;
  badges?: TimelineBadge[];
  actionLabel?: string;
}>();
</script>

<template>
  <div class="relative">
    <!-- Time group header -->
    <div v-if="timeGroup" class="flex items-center gap-3 mb-4">
      <Badge
        variant="outline"
        class="ring-1 ring-white/5 backdrop-blur  text-muted-foreground border-border px-3 py-1 text-xs font-mono"
      >
        {{ timeGroup }}
      </Badge>
      <div class="h-px flex-1  bg-white/5 backdrop-blur" />
    </div>

    <!-- Card -->
    <div
      class="ring-1 ring-white/5 backdrop-blur transition border border-border rounded-md p-3.5 hover:border-border/80 "
    >
      <div class="flex items-start gap-3">
        <!-- Icon -->
        <div
          class="w-8 h-8 rounded bg-secondary/50 flex items-center justify-center shrink-0"
        >
          <component
            :is="icon"
            class="w-4 h-4 text-muted-foreground"
          />
        </div>

        <!-- Content -->
        <div class="flex-1 min-w-0">
          <div class="flex items-start justify-between gap-2 mb-1">
            <h4 class="font-medium text-foreground text-sm">
              {{ title }}
            </h4>

            <!-- Badges -->
            <div v-if="badges?.length" class="flex gap-1 shrink-0">
              <Badge
                v-for="(badge, index) in badges"
                :key="index"
                variant="outline"
                class="text-xs"
                :class="
                  badge.variant === 'default'
                    ? 'bg-info/10 text-info/90 border-info/30'
                    : badge.variant === 'secondary'
                      ? 'bg-warning/10 text-warning/90 border-warning/30'
                      : 'bg-muted/50 text-muted-foreground border-border'
                "
              >
                {{ badge.label }}
              </Badge>
            </div>
          </div>

          <p class="text-xs text-muted-foreground/80 mb-2">
            {{ description }}
          </p>

          <div class="flex items-center justify-between">
            <span class="text-xs text-muted-foreground/70">
              {{ timestamp }}
            </span>

            <Button
              v-if="actionLabel"
              variant="ghost"
              size="sm"
              class="text-xs h-6 font-normal"
            >
              {{ actionLabel }}
            </Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
