<script setup lang="ts">
const toasts = useState<{ id: number; message: string; type: "info" | "error" | "success" }[]>(
  "toasts",
  () => [],
);
function remove(id: number) {
  toasts.value = toasts.value.filter(t => t.id !== id);
}
onMounted(() => {
  // auto cleanup older toasts beyond 5
  watch(toasts, () => {
    if (toasts.value.length > 5)
      toasts.value.shift();
  }, { deep: true });
});
</script>

<template>
  <div class="fixed z-50 top-4 right-4 flex flex-col gap-2 w-72">
    <div
      v-for="t in toasts"
      :key="t.id"
      class="rounded-lg px-4 py-3 shadow border text-sm backdrop-blur"
      :class="t.type === 'error' ? 'bg-rose-500/15 border-rose-400/40 text-rose-200' : t.type === 'success' ? 'bg-emerald-500/15 border-emerald-400/40 text-emerald-200' : 'bg-base-200/40 border-base-300/50 text-white'"
    >
      <div class="flex items-start gap-2">
        <Icon :name="t.type === 'error' ? 'tabler-alert-triangle' : t.type === 'success' ? 'tabler-check' : 'tabler-info-circle'" class="mt-0.5" />
        <span class="flex-1">{{ t.message }}</span>
        <button class="opacity-60 hover:opacity-100" @click="remove(t.id)">
          ×
        </button>
      </div>
    </div>
  </div>
</template>
