<script setup lang="ts">
definePageMeta({ layout: "auth" });
const route = useRoute();
const code = computed(() => route.query.error as string || "unknown_error");
const msg = computed(() => decodeURIComponent((route.query.message as string) || "An unexpected error occurred."));
</script>

<template>
  <div class="min-h-screen flex items-center justify-center text-white px-4">
    <div class="w-full max-w-md space-y-4 text-center">
      <h1 class="text-2xl font-bold">
        Authentication Error
      </h1>
      <p class="text-sm opacity-70">
        Code: <code class="px-1.5 py-0.5 rounded bg-base-300/40">{{ code }}</code>
      </p>
      <p class="text-sm">
        {{ msg }}
      </p>
      <NuxtLink to="/login" class="btn btn-primary btn-sm mt-2">
        Back to Login
      </NuxtLink>
    </div>
  </div>
</template>
