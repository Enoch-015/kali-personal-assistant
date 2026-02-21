<script setup lang="ts">
import { cva } from "class-variance-authority";
import clsx from "clsx";
import { computed } from "vue";

const props = defineProps<{
  variant?: "default" | "secondary" | "outline";
  class?: string;
}>();

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground",
        outline: "text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

const classes = computed(() =>
  clsx(badgeVariants({ variant: props.variant }), props.class),
);
</script>

<template>
  <span :class="classes">
    <slot />
  </span>
</template>
