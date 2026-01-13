<script setup lang="ts">
import { cva } from "class-variance-authority";
import clsx from "clsx";
import { computed } from "vue";

const props = defineProps<{
  variant?: "default" | "ghost";
  size?: "default" | "sm";
  class?: string;
}>();

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-purple-500/30  text-white hover:bg-purple-500/90",
        ghost:
          "bg-white/30 hover:bg-accent hover:text-accent-foreground",
      },
      size: {
        default: "h-10 px-4",
        sm: "h-6 px-3 text-xs",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

const classes = computed(() =>
  clsx(
    buttonVariants({
      variant: props.variant,
      size: props.size,
    }),
    props.class,
  ),
);
</script>

<template>
  <button :class="classes">
    <slot />
  </button>
</template>
