<script setup lang="ts">
import { useToast } from "#imports";
import { ref } from "vue";

definePageMeta({ layout: "auth" });

const route = useRoute();
const token = ref<string | null>((route.query.token as string) || null);
const newPassword = ref("");
const loading = ref(false);
const done = ref(false);
const errorMsg = ref("");
const toast = useToast();

async function submit(e: Event) {
  e.preventDefault();
  if (!token.value) {
    errorMsg.value = "Missing token";
    return;
  }
  errorMsg.value = "";
  loading.value = true;
  try {
    const res: any = await $fetch("/api/auth/reset-password", {
      method: "POST",
      body: { token: token.value, newPassword: newPassword.value },
    });
    if ((res as any)?.error)
      throw (res as any).error;
    done.value = true;
    toast.success("Password updated. You can now log in.");
  }
  catch (err: any) {
    errorMsg.value = err?.message || "Reset failed";
    toast.error("Password reset failed");
  }
  finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center px-4 text-white">
    <div class="w-full max-w-sm space-y-4">
      <h1 class="text-2xl font-bold">
        Reset Password
      </h1>
      <p class="text-sm opacity-70">
        Enter a new password below.
      </p>
      <form
        v-if="!done"
        class="space-y-3"
        @submit="submit"
      >
        <input
          v-model="newPassword"
          type="password"
          minlength="8"
          required
          placeholder="New password"
          class="w-full px-4 py-3 rounded-lg bg-black-500 border border-gray-700 focus:outline-none focus:ring-1 focus:ring-purple-900"
        >
        <p
          v-if="errorMsg"
          class="text-xs text-red-400"
        >
          {{ errorMsg }}
        </p>
        <button
          :disabled="loading"
          type="submit"
          class="w-full bg-black-500 hover:bg-purple-900 py-3 rounded-lg font-medium border border-gray-900 disabled:opacity-50"
        >
          <span v-if="!loading">Reset password</span>
          <span v-else>Updating…</span>
        </button>
      </form>
      <div v-else class="space-y-3 text-sm">
        <p>Password updated successfully.</p>
        <NuxtLink
          to="/login"
          class="text-purple-400 hover:underline"
        >
          Return to login
        </NuxtLink>
      </div>
    </div>
  </div>
</template>
