<script setup lang="ts">
import { useToast } from "#imports";
import { reactive, ref } from "vue";

definePageMeta({ layout: "auth" });

const form = reactive({ email: "", password: "", remember: true });
const errorMsg = ref("");
const loading = ref(false);

const route = useRoute();
// Sanitize redirect: allow only same-origin relative paths, strip any embedded token query to avoid leaking.
function sanitizeRedirect(raw: any): string {
  if (typeof raw !== "string" || !raw.startsWith("/"))
    return "/";
  try {
    const u = new URL(raw, "http://dummy.local");
    u.searchParams.delete("token");
    return u.pathname + (u.search ? u.search : "") + (u.hash || "");
  }
  catch {
    return "/";
  }
}
const redirect = sanitizeRedirect(route.query.redirect);

async function onSubmit(e: Event) {
  e.preventDefault();
  errorMsg.value = "";
  // Basic client-side validation
  const toast = useToast();
  if (!form.email) {
    errorMsg.value = "Email is required";
    toast.error("Email is required");
    return;
  }
  const at = form.email.indexOf("@");
  const dot = form.email.lastIndexOf(".");
  if (!(at > 0 && dot > at + 1 && dot < form.email.length - 1)) {
    errorMsg.value = "Enter a valid email address";
    toast.error("Enter a valid email address");
    return;
  }
  if (!form.password) {
    errorMsg.value = "Password is required";
    toast.error("Password is required");
    return;
  }
  loading.value = true;
  try {
    const nuxtApp = useNuxtApp();
    const client: any = nuxtApp.$authClient;
    const { error: signInError } = await client.signIn.email({
      email: form.email,
      password: form.password,
      rememberMe: form.remember,
      callbackURL: redirect,
    });
    if (signInError) {
      let friendly = signInError.message || "Login failed";
      if (signInError.status === 403) {
        friendly = "Email not verified. Check your inbox or resend from the sign‑up page.";
      }
      else if (signInError.status === 401 || /invalid email or password/i.test(friendly)) {
        friendly = "Incorrect email or password. You can reset it if you've forgotten.";
      }
      else if (/already exists/i.test(friendly)) {
        friendly = "That email belongs to an existing account. Try logging in instead.";
      }
      else if (/too many|rate/i.test(friendly)) {
        friendly = "Too many attempts. Please wait a minute before trying again.";
      }
      errorMsg.value = friendly;
      toast.error(friendly);
      return;
    }
    toast.success("Signed in successfully");
    await navigateTo(redirect);
  }
  catch (err: any) {
    const friendly = err?.message || "Unexpected error during sign in";
    errorMsg.value = friendly;
    toast.error(friendly);
  }
  finally {
    loading.value = false;
  }
}
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
        <!-- Login Form -->
        <div class="w-full max-w-sm space-y-2">
          <h2 class="text-2xl font-bold mb-1">
            Welcome!
          </h2>
          <h5 class="text-sm text-white-500 opacity-60  mb-3">
            Login to kali-E to use your personal AI assistant.
          </h5>

          <!-- Google button -->
          <button class="w-full flex items-center justify-center gap-2 bg-black-500 shadow-lg hover:bg-gray-800 py-2 rounded-lg font-medium border border-gray-700">
            <img
              src="https://www.svgrepo.com/show/475656/google-color.svg"
              alt="Google"
              class="w-5 h-5"
            >
            Log in with Google
          </button>

          <!-- Apple button -->
          <button class="w-full  flex items-center justify-center gap-2 bg-black-500 shadow-lg hover:bg-gray-800 py-2 rounded-lg font-medium border border-gray-700">
            <Icon name="tabler-brand-github-filled" />
            Log in with Github
          </button>

          <!-- Divider -->
          <div class="flex items-center gap-2 text-gray-400">
            <hr class="flex-grow border-gray-700">
            OR
            <hr class="flex-grow border-gray-700">
          </div>

          <!-- Email + Password -->
          <form class="space-y-2" @submit="onSubmit">
            <div>
              <label for="email" class="block text-left mb-1">Email</label>
              <input
                id="email"
                v-model="form.email"
                type="email"
                placeholder="Your email address"
                class="w-full  px-4 py-3 rounded-lg bg-black-500 shadow-lg border border-gray-700 focus:outline-none focus:ring-1 focus:ring-purple-900"
              >
            </div>

            <div>
              <div class="flex justify-between items-center">
                <label for="password" class="block mb-1">Password</label>
                <NuxtLink to="/forgot-password" class="text-sm text-purple-400 hover:underline">
                  Forgot password?
                </NuxtLink>
              </div>
              <input
                id="password"
                v-model="form.password"
                type="password"
                placeholder="Your password"
                class="w-full  px-4 py-3 rounded-lg bg-black-500 shadow-lg border border-gray-700 focus:outline-none focus:ring-1 focus:ring-purple-900"
              >
            </div>

            <div v-if="errorMsg" class="text-xs text-red-400">
              {{ errorMsg }}
            </div>
            <button
              :disabled="loading"
              type="submit"
              class="w-full bg-black-500 hover:bg-purple-900 disabled:opacity-50 py-3 mt-2.5 rounded-lg font-medium border border-gray-900"
            >
              <span v-if="!loading">Log in</span>
              <span v-else>Signing in...</span>
            </button>
          </form>

          <!-- Sign up link -->
          <p class="text-sm text-gray-400 text-center">
            Don’t have an account?
            <NuxtLink to="/sign" class="text-purple-400 hover:underline">
              Sign up
            </NuxtLink>
          </p>
        </div>
      </div>

      <!-- Right half -->
      <div class="hidden lg:flex lg:w-1/2">
        <NuxtImg
          src="/img/Gemini_Generated_Image_t7306vt7306vt730.jpg"
          alt="Hero Image"
          class="max-w-full h-full opacity-50"
          sizes="sm:100vw md:50vw lg:50vw"
          loading="lazy"
          decoding="async"
        />
      </div>
    </main>
  </div>
</template>
