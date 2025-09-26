<script setup lang="ts">
import type { ComponentPublicInstance } from "vue";

import { computed, nextTick, onMounted, reactive, ref } from "vue";

definePageMeta({ layout: "auth" });

type Step = "form" | "verify";

// Step management
const step = ref<Step>("form");

// Form state
const form = reactive({
  name: "",
  email: "",
  password: "",
});

// Simple UI validation flags/messages
const errors = reactive<{ name?: string; email?: string; password?: string; code?: string }>({});
const isSubmitting = ref(false);

// OTP state (8 digits)
const CODE_LENGTH = 8;
function makeStringArray(len: number, val = ""): string[] {
  const a = Array.from({ length: len }) as string[];
  for (let i = 0; i < len; i++) a[i] = val;
  return a;
}
const code = ref<string[]>(makeStringArray(CODE_LENGTH));
const codeInputs = Array.from({ length: CODE_LENGTH }, () => ref<HTMLInputElement | null>(null));
const canResendIn = ref(60); // seconds
let resendTimer: number | undefined;

const combinedCode = computed(() => code.value.join(""));
const canSubmitCode = computed(() => combinedCode.value.length === CODE_LENGTH);

function isValidEmail(email: string): boolean {
  // Lightweight checks to avoid regex pitfalls:
  // - Exactly one '@'
  // - Non-empty local and domain parts
  // - Domain contains at least one '.' with non-empty labels
  // - No whitespace
  if (!email || /\s/.test(email))
    return false;
  const at = email.indexOf("@");
  if (at <= 0 || at !== email.lastIndexOf("@"))
    return false;
  const local = email.slice(0, at);
  const domain = email.slice(at + 1);
  if (!local || !domain || domain.startsWith(".") || domain.endsWith("."))
    return false;
  const parts = domain.split(".");
  if (parts.length < 2)
    return false;
  return parts.every(p => p.length > 0);
}

function validateForm() {
  errors.name = !form.name.trim() ? "Please enter your full name" : "";
  errors.email = isValidEmail(form.email) ? "" : "Enter a valid email address";
  errors.password = form.password.length >= 8 ? "" : "Password must be at least 8 characters";
  return !errors.name && !errors.email && !errors.password;
}

async function onSubmitForm(e: Event) {
  e.preventDefault();
  if (!validateForm())
    return;
  isSubmitting.value = true;
  // Simulate sending code to email (UI only)
  await new Promise(r => setTimeout(r, 700));
  isSubmitting.value = false;
  step.value = "verify";
  startResendCountdown();
  await nextTick();
  focusCodeIndex(0);
}

function startResendCountdown() {
  canResendIn.value = 60;
  if (resendTimer)
    window.clearInterval(resendTimer);
  resendTimer = window.setInterval(() => {
    if (canResendIn.value > 0) {
      canResendIn.value -= 1;
    }
    else {
      window.clearInterval(resendTimer);
    }
  }, 1000);
}

function backToForm() {
  step.value = "form";
  errors.code = "";
  code.value = makeStringArray(CODE_LENGTH);
}

function onCodeInput(index: number, evt: Event) {
  const input = evt.target as HTMLInputElement;
  const v = input.value.replace(/\D/g, ""); // keep digits only
  if (!v) {
    code.value[index] = "";
    return;
  }
  // support user typing multiple digits quickly or via mobile autofill
  const chars = v.split("").slice(0, CODE_LENGTH - index);
  for (let i = 0; i < chars.length; i++) {
    code.value[index + i] = chars[i]!;
  }
  const nextIndex = Math.min(index + chars.length, CODE_LENGTH - 1);
  focusCodeIndex(nextIndex);
}

function onCodeKeydown(index: number, evt: KeyboardEvent) {
  const key = evt.key;
  const isDigit = /\d/.test(key);
  if (isDigit && code.value[index]) {
    // Overwrite and move forward
    code.value[index] = key;
    if (index < CODE_LENGTH - 1) {
      evt.preventDefault();
      focusCodeIndex(index + 1);
    }
  }
  else if (key === "Backspace") {
    if (code.value[index]) {
      code.value[index] = "";
    }
    else if (index > 0) {
      focusCodeIndex(index - 1);
      code.value[index - 1] = "";
    }
  }
  else if (key === "ArrowLeft" && index > 0) {
    evt.preventDefault();
    focusCodeIndex(index - 1);
  }
  else if (key === "ArrowRight" && index < CODE_LENGTH - 1) {
    evt.preventDefault();
    focusCodeIndex(index + 1);
  }
}

function onCodePaste(index: number, evt: ClipboardEvent) {
  const text = evt.clipboardData?.getData("text") || "";
  const digits = text.replace(/\D/g, "");
  if (!digits)
    return;
  evt.preventDefault();
  const chars = digits.split("").slice(0, CODE_LENGTH - index);
  for (let i = 0; i < chars.length; i++) {
    code.value[index + i] = chars[i]!;
  }
  const next = Math.min(index + chars.length, CODE_LENGTH - 1);
  focusCodeIndex(next);
}

function focusCodeIndex(i: number) {
  const el = codeInputs[i]?.value;
  el?.focus();
  el?.select();
}
function setCodeInputRef(i: number) {
  return (el: Element | ComponentPublicInstance | null) => {
    if (codeInputs[i])
      codeInputs[i]!.value = (el as HTMLInputElement | null);
  };
}

async function resendCode() {
  if (canResendIn.value > 0)
    return;
  // UI-only resend
  await new Promise(r => setTimeout(r, 500));
  startResendCountdown();
}

async function onVerifyCode(e: Event) {
  e.preventDefault();
  errors.code = "";
  if (combinedCode.value.length !== CODE_LENGTH) {
    errors.code = `Enter the ${CODE_LENGTH}-digit code`;
    return;
  }
  isSubmitting.value = true;
  // Simulate verify call
  await new Promise(r => setTimeout(r, 700));
  isSubmitting.value = false;
  // UI-only: redirect to home
  return navigateTo("/");
}

onMounted(() => {
  // Prefocus name field on load
  // handled via autofocus attribute below
});
</script>

<template>
  <div class="flex flex-col">
    <main class="flex min-h-screen text-white">
      <!-- Left half -->
      <div class="relative flex flex-col justify-center items-center w-full lg:w-1/2 px-2">
        <!-- Logo pinned to top-left -->
        <NuxtImg
          src="/img/Gemini_Generated_Image_ehw9dgehw9dgehw9-removebg-preview11.png"
          alt="Kali-E Logo"
          width="48"
          height="48"
          class="absolute top-2 left-4 w-12 h-12 object-contain"
          loading="eager"
          decoding="async"
        />

        <!-- Sign Up Form / 2FA Verify -->
        <div class="w-full max-w-sm space-y-2">
          <h2 class="text-2xl font-bold mb-1">
            {{ step === 'form' ? 'Create account' : 'Verify your email' }}
          </h2>
          <h5 class="text-sm text-white-500 opacity-60  mb-3">
            <template v-if="step === 'form'">
              Sign up to start using your personal AI assistant.
            </template>
            <template v-else>
              We sent an 8-digit verification code to
              <span class="font-semibold">{{ form.email || 'your email' }}</span>.
              Enter the code below to finish creating your account.
            </template>
          </h5>

          <template v-if="step === 'form'">
            <!-- Google button -->
            <button class="w-full flex items-center justify-center gap-2 bg-black-500 shadow-lg hover:bg-gray-800 py-2 rounded-lg font-medium border border-gray-700">
              <img
                src="https://www.svgrepo.com/show/475656/google-color.svg"
                alt="Google"
                class="w-5 h-5"
              >
              Continue with Google
            </button>

            <!-- Github button -->
            <button class="w-full  flex items-center justify-center gap-2 bg-black-500 shadow-lg hover:bg-gray-800 py-2 rounded-lg font-medium border border-gray-700">
              <Icon name="tabler-brand-github-filled" />
              Continue with Github
            </button>

            <!-- Divider -->
            <div class="flex items-center gap-2 text-gray-400">
              <hr class="flex-grow border-gray-700">
              OR
              <hr class="flex-grow border-gray-700">
            </div>

            <!-- Name + Email + Password -->
            <form class="space-y-2" @submit="onSubmitForm">
              <div>
                <label for="name" class="block text-left mb-1">Full name</label>
                <input
                  id="name"
                  v-model.trim="form.name"
                  type="text"
                  placeholder="Your full name"
                  class="w-full  px-4 py-3 rounded-lg bg-black-500 shadow-lg border border-gray-700 focus:outline-none focus:ring-1 focus:ring-purple-900"
                  :class="{ 'border-red-500': errors.name }"
                  autofocus
                >
                <p v-if="errors.name" class="text-xs text-red-400 mt-1">
                  {{ errors.name }}
                </p>
              </div>

              <div>
                <label for="email" class="block text-left mb-1">Email</label>
                <input
                  id="email"
                  v-model.trim="form.email"
                  type="email"
                  placeholder="Your email address"
                  class="w-full  px-4 py-3 rounded-lg bg-black-500 shadow-lg border border-gray-700 focus:outline-none focus:ring-1 focus:ring-purple-900"
                  :class="{ 'border-red-500': errors.email }"
                >
                <p v-if="errors.email" class="text-xs text-red-400 mt-1">
                  {{ errors.email }}
                </p>
              </div>

              <div>
                <div class="flex justify-between items-center">
                  <label for="password" class="block mb-1">Password</label>
                  <span class="text-sm text-gray-500">min 8 characters</span>
                </div>
                <input
                  id="password"
                  v-model="form.password"
                  type="password"
                  placeholder="Create a password"
                  class="w-full  px-4 py-3 rounded-lg bg-black-500 shadow-lg border border-gray-700 focus:outline-none focus:ring-1 focus:ring-purple-900"
                  :class="{ 'border-red-500': errors.password }"
                >
                <p v-if="errors.password" class="text-xs text-red-400 mt-1">
                  {{ errors.password }}
                </p>
              </div>

              <button
                type="submit"
                :disabled="isSubmitting"
                class="w-full bg-black-500 hover:bg-purple-900 disabled:opacity-50 py-3 mt-2.5 rounded-lg font-medium border border-gray-900"
              >
                <span v-if="!isSubmitting">Create account</span>
                <span v-else>Sending code…</span>
              </button>
            </form>

            <!-- Login link -->
            <p class="text-sm text-gray-400 text-center">
              Already have an account?
              <NuxtLink to="/login" class="text-purple-400 hover:underline">
                Log in
              </NuxtLink>
            </p>
          </template>

          <template v-else>
            <form class="space-y-3" @submit="onVerifyCode">
              <div class="flex items-center justify-between">
                <button
                  type="button"
                  class="text-sm text-gray-400 hover:text-white"
                  @click="backToForm"
                >
                  <Icon name="tabler-arrow-left" class="inline -mt-0.5" />
                  Edit email
                </button>
                <button
                  type="button"
                  class="text-sm text-purple-400 disabled:text-gray-500"
                  :disabled="canResendIn > 0"
                  @click="resendCode"
                >
                  <template v-if="canResendIn > 0">
                    Resend in {{ canResendIn }}s
                  </template>
                  <template v-else>
                    Resend code
                  </template>
                </button>
              </div>

              <div class="grid grid-cols-8 gap-1.5 sm:gap-2" aria-label="8-digit verification code">
                <input
                  v-for="(_, i) in code"
                  :key="i"
                  :ref="setCodeInputRef(i)"
                  :value="code[i]"
                  inputmode="numeric"
                  pattern="[0-9]*"
                  maxlength="1"
                  autocomplete="one-time-code"
                  class="text-center text-lg sm:text-xl px-0 py-3 rounded-lg bg-black-500 shadow-lg border border-gray-700 focus:outline-none focus:ring-1 focus:ring-purple-900"
                  @input="onCodeInput(i, $event)"
                  @keydown="onCodeKeydown(i, $event)"
                  @paste="onCodePaste(i, $event)"
                >
              </div>
              <p v-if="errors.code" class="text-xs text-red-400 mt-1">
                {{ errors.code }}
              </p>

              <button
                type="submit"
                :disabled="!canSubmitCode || isSubmitting"
                class="w-full bg-black-500 hover:bg-purple-900 disabled:opacity-50 py-3 mt-1.5 rounded-lg font-medium border border-gray-900"
              >
                <span v-if="!isSubmitting">Verify and create account</span>
                <span v-else>Verifying…</span>
              </button>
            </form>

            <p class="text-xs text-gray-400 text-center">
              Tip: You can paste the full 8-digit code.
            </p>
          </template>
        </div>
      </div>

      <!-- Right half -->
      <div class="hidden lg:flex lg:w-1/2">
        <NuxtImg
          src="/img/Gemini_Generated_Image_sfebllsfebllsfeb.png"
          alt="Hero Image"
          width="1280"
          class="max-w-full h-full opacity-50"
          sizes="sm:100vw md:50vw lg:50vw"
          loading="lazy"
          decoding="async"
        />
      </div>
    </main>
  </div>
</template>
