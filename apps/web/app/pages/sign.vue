<script setup lang="ts">
import { useToast } from "#imports";
import { reactive, ref } from "vue";

definePageMeta({ layout: "auth" });

type Step = "form" | "check";
const step = ref<Step>("form");
const form = reactive({ name: "", email: "", password: "" }); // Removed image from form
const errors = reactive<{ name?: string; email?: string; password?: string }>({});
const loading = ref(false);
const resendCooldown = ref(0);
let timer: number | undefined;
const message = ref("");
const resendLoading = ref(false);

function validate() {
  errors.name = form.name.trim() ? "" : "Full name required";
  const at = form.email.indexOf("@");
  const dot = form.email.lastIndexOf(".");
  errors.email = at > 0 && dot > at + 1 && dot < form.email.length - 1 ? "" : "Valid email required";
  errors.password = form.password.length >= 8 ? "" : "Min 8 characters";
  return !errors.name && !errors.email && !errors.password;
}

function startCooldown() {
  resendCooldown.value = 60;
  if (timer)
    window.clearInterval(timer);
  timer = window.setInterval(() => {
    if (resendCooldown.value <= 0) {
      window.clearInterval(timer);
    }
    else {
      resendCooldown.value -= 1;
    }
  }, 1000);
}

async function onSubmitForm(e: Event) {
  e.preventDefault();
  message.value = "";
  if (!validate())
    return;
  loading.value = true;
  try {
    const toast = useToast();
    const client: any = (useNuxtApp() as any).$authClient;

    // Only send fields that have values - image is optional
    const signUpData: any = {
      name: form.name,
      email: form.email,
      password: form.password,
    };

    const { error } = await client.signUp.email(signUpData);

    if (error) {
      // Log the full error object to console
      console.error("Full error object:", error);
      console.error("Error status:", error?.status);
      console.error("Error message:", error?.message);
      console.error("Error details:", JSON.stringify(error, null, 2));

      const msg = error.message || "Sign up failed";
      message.value = msg;
      if (/already exists/i.test(msg)) {
        errors.email = "Email already registered";
        toast.error("That email is already in use. Try logging in instead.");
      }
      else {
        toast.error(msg);
      }
      return;
    }
    step.value = "check";
    startCooldown();
    toast.success("Account created. Verify your email to continue.");
  }
  catch (err: any) {
    message.value = err?.message || "Unexpected error";
    const toast = useToast();
    toast.error(message.value);
  }
  finally {
    loading.value = false;
  }
}

async function resendVerification() {
  if (resendCooldown.value > 0)
    return;
  resendLoading.value = true;
  try {
    const toast = useToast();
    const client: any = (useNuxtApp() as any).$authClient;
    const { error } = await client.sendVerificationEmail({
      email: form.email,
      callbackURL: "/",
    });
    if (error) {
      message.value = error.message || "Could not resend email";
      toast.error(message.value);
      return;
    }
    message.value = "Verification email resent.";
    startCooldown();
    toast.success("Verification email resent");
  }
  catch (err: any) {
    message.value = err?.message || "Unexpected error";
    const toast = useToast();
    toast.error(message.value);
  }
  finally {
    resendLoading.value = false;
  }
}

function backToForm() {
  step.value = "form";
  message.value = "";
}
</script>

<template>
  <main class="flex min-h-screen text-white">
    <!-- Left half -->
    <div class="relative flex flex-col justify-center items-center w-full lg:w-1/2 px-2">
      <!-- Logo pinned to top-left -->
      <NuxtImg
        src="v1762635825/Gemini_Generated_Image_ehw9dgehw9dgehw9-removebg-preview11_igmqeu.png"
        alt="Kali-E Logo"
        width="48"
        height="48"
        class="absolute top-2 left-4 w-12 h-12 object-contain"
        loading="eager"
        decoding="async"
      />

      <!-- Sign Up Form / Email Verification -->
      <div class="w-full max-w-sm space-y-2">
        <h2 class="text-2xl font-bold mb-1">
          {{ step === 'form' ? 'Create account' : 'Check your email' }}
        </h2>
        <h5 class="text-sm text-white-500 opacity-60 mb-3">
          <span v-if="step === 'form'">
            Sign up to start using your personal AI assistant.
          </span>
          <span v-else>
            We've sent a verification link to <span class="font-semibold">{{ form.email }}</span>. Click the link in the email to verify your account, then return here or continue in the opened tab.
          </span>
        </h5>

        <!-- Form View -->
        <div v-if="step === 'form'" class="space-y-2">
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
          <button class="w-full flex items-center justify-center gap-2 bg-black-500 shadow-lg hover:bg-gray-800 py-2 rounded-lg font-medium border border-gray-700">
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
                class="w-full px-4 py-3 rounded-lg bg-black-500 shadow-lg border border-gray-700 focus:outline-none focus:ring-1 focus:ring-purple-900"
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
                class="w-full px-4 py-3 rounded-lg bg-black-500 shadow-lg border border-gray-700 focus:outline-none focus:ring-1 focus:ring-purple-900"
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
                class="w-full px-4 py-3 rounded-lg bg-black-500 shadow-lg border border-gray-700 focus:outline-none focus:ring-1 focus:ring-purple-900"
                :class="{ 'border-red-500': errors.password }"
              >
              <p v-if="errors.password" class="text-xs text-red-400 mt-1">
                {{ errors.password }}
              </p>
            </div>

            <button
              type="submit"
              :disabled="loading"
              class="w-full bg-black-500 hover:bg-purple-900 disabled:opacity-50 py-3 mt-2.5 rounded-lg font-medium border border-gray-900"
            >
              <span v-if="!loading">Create account</span>
              <span v-else>Creating…</span>
            </button>
          </form>

          <p
            v-if="message"
            class="text-xs mt-1"
            :class="/verif/i.test(message) ? 'text-green-400' : 'text-red-400'"
          >
            {{ message }}
          </p>

          <!-- Login link -->
          <p class="text-sm text-gray-400 text-center">
            Already have an account?
            <NuxtLink to="/login" class="text-purple-400 hover:underline">
              Log in
            </NuxtLink>
          </p>
        </div>

        <!-- Email Verification View -->
        <div v-else class="space-y-4">
          <div class="flex items-center justify-between">
            <button
              type="button"
              class="text-sm text-gray-400 hover:text-white"
              @click="backToForm"
            >
              <Icon name="tabler-arrow-left" class="inline -mt-0.5" /> Edit email
            </button>
            <button
              type="button"
              class="text-sm text-purple-400 disabled:text-gray-500"
              :disabled="resendCooldown > 0 || resendLoading"
              @click="resendVerification"
            >
              <span v-if="resendCooldown > 0">
                Resend in {{ resendCooldown }}s
              </span>
              <span v-else>
                {{ resendLoading ? 'Sending…' : 'Resend email' }}
              </span>
            </button>
          </div>
          <p class="text-xs opacity-70">
            Didn't get the email? Check spam or promotions folder.
          </p>
          <p
            v-if="message"
            class="text-xs"
            :class="/resend|verification|sent/i.test(message) ? 'text-green-400' : 'text-red-400'"
          >
            {{ message }}
          </p>
        </div>
      </div>
    </div>

    <!-- Right half -->
    <div class="hidden lg:flex lg:w-1/2">
      <NuxtImg
        src="v1762636794/Gemini_Generated_Image_sfebllsfebllsfeb_ry4scl.png"
        alt="Hero Image"
        width="1280"
        class="max-w-full h-full opacity-50"
        sizes="sm:100vw md:50vw lg:50vw"
        loading="lazy"
        decoding="async"
      />
    </div>
  </main>
</template>
