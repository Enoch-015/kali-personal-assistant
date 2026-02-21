<script setup lang="ts">
import { useToast } from "#imports";
import { ref } from "vue";

definePageMeta({ layout: "auth" });

const email = ref("");
const loading = ref(false);
const sent = ref(false);
const errorMsg = ref("");
const toast = useToast();

async function submit(e: Event) {
  e.preventDefault();
  errorMsg.value = "";
  loading.value = true;
  try {
    const res: any = await $fetch("/api/auth/request-password-reset", {
      method: "POST",
      body: { email: email.value, redirectTo: "/reset-password" },
    });
    if ((res as any)?.error)
      throw (res as any).error;
    sent.value = true;
    toast.success("Password reset email sent");
  }
  catch (err: any) {
    errorMsg.value = err?.message || "Failed to send reset email";
    toast.error("Failed to send reset email");
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
        Forgot Password
      </h1>
      <p class="text-sm opacity-70">
        Enter your email to receive a reset link.
      </p>
      <form
        v-if="!sent"
        class="space-y-3"
        @submit="submit"
      >
        <input
          v-model="email"
          type="email"
          required
          placeholder="you@example.com"
          class="w-full px-4 py-3 rounded-lg bg-black-500 border border-gray-700 focus:outline-none focus:ring-1 focus:ring-purple-900"
        >
        <p v-if="errorMsg" class="text-xs text-red-400">
          {{ errorMsg }}
        </p>
        <button
          :disabled="loading"
          type="submit"
          class="w-full bg-black-500 hover:bg-purple-900 py-3 rounded-lg font-medium border border-gray-900 disabled:opacity-50"
        >
          <span v-if="!loading">Send reset link</span>
          <span v-else>Sending…</span>
        </button>
      </form>
      <div v-else class="space-y-3 text-sm">
        <p>Check your email for a link to reset your password.</p>
        <NuxtLink to="/login" class="text-purple-400 hover:underline">
          Return to login
        </NuxtLink>
      </div>
    </div>
  </div>
</template>
