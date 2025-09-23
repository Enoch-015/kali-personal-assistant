<script setup lang="ts"></script>

<template>
  <div class="flex flex-col">
    <main class="flex min-h-screen text-white">
      <!-- Left half -->
      <div class="relative flex flex-col justify-center items-center w-full lg:w-1/2 px-2">
        <!-- Logo pinned to top-left -->
        <NuxtImg
          src="/img/Gemini_Generated_Image_ehw9dgehw9dgehw9-removebg-preview11.png"
          alt="Kali-E Logo"
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
          <form class="space-y-2">
            <div>
              <label for="email" class="block text-left mb-1">Email</label>
              <input
                id="email"
                type="email"
                placeholder="Your email address"
                class="w-full  px-4 py-3 rounded-lg bg-black-500 shadow-lg border border-gray-700 focus:outline-none focus:ring-1 focus:ring-purple-900"
              >
            </div>

            <div>
              <div class="flex justify-between items-center">
                <label for="password" class="block mb-1">Password</label>
                <a href="#" class="text-sm text-purple-400 hover:underline">Forgot password?</a>
              </div>
              <input
                id="password"
                type="password"
                placeholder="Your password"
                class="w-full  px-4 py-3 rounded-lg bg-black-500 shadow-lg border border-gray-700 focus:outline-none focus:ring-1 focus:ring-purple-900"
              >
            </div>

            <button type="submit" class="w-full bg-black-500 hover:bg-purple-900 opacity-30 py-3 mt-2.5 rounded-lg font-medium border border-gray-900">
              Log in
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
